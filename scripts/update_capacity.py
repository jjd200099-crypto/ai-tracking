#!/usr/bin/env python3
"""Daily capacity-tension updater for the ai-tracking dashboard's Capacity tab.

WHY THIS EXISTS: OpenAI's status page (incident.io) only exposes the most recent
~90-95 incidents (~3 months); older ones are permanently lost from the API. By
snapshotting daily and merging by incident-id into an append-only archive, this
script accumulates OAI history the status page itself can never give back.
Anthropic (Atlassian Statuspage) exposes ~12 months but is archived the same way
so the series stays continuous and self-owned, independent of either vendor's
retention window.

Idempotent: re-running the same day adds nothing new. Pure stdlib, no pip installs.
Meant to run from the repo root via GitHub Actions cron (see
.github/workflows/capacity-daily.yml), but also runs fine locally:

  python3 scripts/update_capacity.py

Reads/writes (relative to repo root):
  data/capacity_archive_oai.json / capacity_archive_anth.json   append-only archives, keyed by incident id
  data/capacity_summary.json                                     rendered summary the index.html Capacity tab fetches()
"""
import json, re, html, os, sys, urllib.request
from datetime import datetime, timezone, timedelta
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data')
os.makedirs(DATA_DIR, exist_ok=True)
UTC = timezone.utc
NOW = datetime.now(UTC)
TODAY = NOW.strftime('%Y-%m-%d')

ARCHIVE_OAI = os.path.join(DATA_DIR, 'capacity_archive_oai.json')
ARCHIVE_ANTH = os.path.join(DATA_DIR, 'capacity_archive_anth.json')
SUMMARY = os.path.join(DATA_DIR, 'capacity_summary.json')


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 ai-tracking-capacity-scan'})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode('utf-8', 'replace')


# ----------------- classifier (same methodology as the Obsidian capacity scan) -----------------
STRICT = ['elevated error', 'elevated rate', 'high error rate', 'high failure rate', 'rate limit', 'throttl',
          'capacity', 'high demand', 'overload', 'degraded performance', 'performance degradation',
          'elevated latency', 'increased latency', '503']
CAP = STRICT + ['latency', 'slow', 'response time', '5xx', '429', 'elevated 5', 'increased response',
                'increased error', 'elevated time', 'queue', 'timeout', 'timing out', 'unavailable']
NET = ['network', 'dns', 'connectivity', 'gateway', 'cdn', 'tls']
MAINT = ['scheduled', 'maintenance', 'planned']
BUG = ['cannot', 'unable to', 'broken', 'incorrect', 'wrong', 'duplicat', 'login', 'sign in', 'sign-in',
       'auth fail', 'oauth', 'billing', 'invoice', 'subscription', 'webhook deliver', 'memory',
       'file upload', 'image generation fail', 'voice mode', '401', '403']


def classify(title, message=''):
    t = (title + ' ' + (message or '')).lower()
    if any(k in t for k in MAINT): return 'maintenance'
    if any(k in t for k in STRICT): return 'capacity'
    if any(k in t for k in CAP): return 'capacity'
    if any(k in t for k in NET): return 'network'
    if any(k in t for k in BUG): return 'bug'
    return 'unknown'


def product_of(title, src):
    t = title.lower()
    if src == 'anthropic':
        for k, v in [('opus', 'Claude-Opus'), ('sonnet', 'Claude-Sonnet'), ('haiku', 'Claude-Haiku'),
                     ('claude code', 'Claude-Code'), ('claude.ai', 'Claude.ai'), ('console', 'Console'),
                     ('api', 'API (generic)')]:
            if k in t: return v
        return 'Other'
    for k, v in [('5.5', 'GPT-5.5'), ('codex', 'Codex'), ('sora', 'Sora'), ('gpt-5', 'GPT-5'), ('gpt-4', 'GPT-4'),
                 ('dall', 'DALL-E'), ('realtime', 'Voice/Realtime'), ('voice', 'Voice/Realtime'),
                 ('image', 'Images'), ('chatgpt', 'ChatGPT'), ('api', 'API (generic)'),
                 ('responses', 'API (generic)')]:
        if k in t: return v
    return 'Other'


def iso(dt): return dt.isoformat() if dt else None
def parse_dt(s): return datetime.fromisoformat(s) if s else None


# ----------------- parse Anthropic (react props, 4 pages) -----------------
def parse_anth(pages):
    seen = set(); out = []
    for t in pages:
        m = re.search(r'data-react-props="([^"]+)"', t)
        if not m: continue
        data = json.loads(html.unescape(m.group(1)))
        for mo in data.get('months', []):
            year = mo['year']; mname = mo['name']
            for inc in mo.get('incidents', []):
                if inc['code'] in seen: continue
                seen.add(inc['code'])
                ts = re.sub(r"<[^>]+>", "", inc['timestamp']).replace('UTC', '').strip()
                parts = ts.split(' - '); sstr = parts[0].strip(); estr = parts[1].strip() if len(parts) > 1 else None
                s = e = None
                for fmt in ("%b %d, %H:%M", "%B %d, %H:%M"):
                    try:
                        s = datetime.strptime(f"{sstr} {year}", f"{fmt} %Y").replace(tzinfo=UTC); break
                    except Exception:
                        pass
                if estr and s:
                    if ':' in estr and ',' not in estr:
                        try:
                            e = datetime.strptime(f"{mname} {s.day}, {estr} {year}", "%B %d, %H:%M %Y").replace(tzinfo=UTC)
                        except Exception:
                            pass
                    else:
                        for fmt in ("%b %d, %H:%M", "%B %d, %H:%M"):
                            try:
                                e = datetime.strptime(f"{estr} {year}", f"{fmt} %Y").replace(tzinfo=UTC); break
                            except Exception:
                                pass
                    if e and e < s: e += timedelta(days=1)
                ev = s or e
                out.append({'src': 'anthropic', 'id': inc['code'], 'title': inc['name'],
                            'message': inc.get('message', ''), 'impact': inc.get('impact'),
                            'started_at': iso(s), 'ended_at': iso(e), 'event_at': iso(ev),
                            'category': classify(inc['name'], inc.get('message', '')),
                            'product': product_of(inc['name'], 'anthropic')})
    return out


# ----------------- parse OpenAI (atom base + json enrich) -----------------
def parse_oai(atom, incidents_json):
    base = {}
    for en in re.findall(r'<entry>(.*?)</entry>', atom, re.S):
        cm = re.search(r'/incidents/([A-Z0-9]+)', en)
        tm = re.search(r'<title[^>]*><!\[CDATA\[(.*?)\]\]>', en, re.S)
        um = re.search(r'<updated>(.*?)</updated>', en)
        ctm = re.search(r'<content[^>]*><!\[CDATA\[(.*?)\]\]>', en, re.S)
        if not cm or not tm: continue
        code = cm.group(1); title = tm.group(1).strip()
        upd = datetime.fromisoformat(um.group(1).replace('Z', '+00:00')) if um else None
        comps = [c.strip() for c in re.findall(r'<li>(.*?)\(', ctm.group(1))] if ctm else []
        base[code] = {'src': 'openai', 'id': code, 'title': title, 'message': ' '.join(comps), 'impact': None,
                      'started_at': None, 'ended_at': iso(upd), 'event_at': iso(upd)}
    try:
        j = json.loads(incidents_json)
        for inc in j.get('incidents', []):
            code = inc['id']
            ca = datetime.fromisoformat(inc['created_at'].replace('Z', '+00:00')) if inc.get('created_at') else None
            ra = datetime.fromisoformat(inc['resolved_at'].replace('Z', '+00:00')) if inc.get('resolved_at') else None
            if code in base:
                if ca: base[code]['started_at'] = iso(ca); base[code]['event_at'] = iso(ca)
                if ra: base[code]['ended_at'] = iso(ra)
                base[code]['impact'] = inc.get('impact')
            else:
                base[code] = {'src': 'openai', 'id': code, 'title': inc['name'], 'message': '',
                              'impact': inc.get('impact'), 'started_at': iso(ca), 'ended_at': iso(ra),
                              'event_at': iso(ca or ra)}
    except Exception as ex:
        print('  [warn] OAI json parse failed:', ex)
    out = []
    for r in base.values():
        r['category'] = classify(r['title'], r['message']); r['product'] = product_of(r['title'], 'openai')
        out.append(r)
    return out


# ----------------- merge into append-only archive -----------------
def load_archive(fn):
    if os.path.exists(fn):
        return {r['id']: r for r in json.load(open(fn))}
    return {}


def merge(arch, new_list):
    n_new = 0
    for r in new_list:
        k = r['id']
        if k not in arch:
            r['first_seen'] = TODAY; r['last_seen'] = TODAY; arch[k] = r; n_new += 1
        else:
            ex = arch[k]; ex['last_seen'] = TODAY
            if not ex.get('started_at') and r.get('started_at'):
                ex['started_at'] = r['started_at']; ex['event_at'] = r['started_at']
            if not ex.get('ended_at') and r.get('ended_at'):
                ex['ended_at'] = r['ended_at']
            if (ex.get('impact') in (None, 'none')) and (r.get('impact') not in (None, 'none')):
                ex['impact'] = r['impact']
    return n_new


# ----------------- build the summary JSON the front-end fetches -----------------
def durmin(r):
    s, e = parse_dt(r.get('started_at')), parse_dt(r.get('ended_at'))
    return (e - s).total_seconds() / 60 if s and e and e > s else None


def build_summary(arch_oai, arch_anth):
    oai = list(arch_oai.values()); anth = list(arch_anth.values())
    for r in oai + anth:
        r['_ev'] = parse_dt(r.get('event_at'))

    W90 = NOW - timedelta(days=90)
    def cap90(d): return [r for r in d if r['category'] == 'capacity' and r['_ev'] and r['_ev'] >= W90]
    oc90 = cap90(oai); ac90 = cap90(anth)
    mc90 = lambda cap: sum(1 for r in cap if r.get('impact') in ('major', 'critical'))

    # full monthly history for both
    def monthly(d):
        m = defaultdict(int)
        for r in d:
            if r['category'] == 'capacity' and r['_ev']:
                m[r['_ev'].strftime('%Y-%m')] += 1
        return m
    mo_oai = monthly(oai); mo_anth = monthly(anth)
    all_months = sorted(set(mo_oai) | set(mo_anth))
    monthly_table = [{'month': m, 'oai': mo_oai.get(m, 0), 'anth': mo_anth.get(m, 0),
                      'oai_has_data': m in mo_oai or (all_months and m >= min(mo_oai, default=m))}
                     for m in all_months]

    # weekly, trailing 18 weeks
    def weekly(d):
        w = defaultdict(int)
        for r in d:
            if r['category'] == 'capacity' and r['_ev']:
                ws = (r['_ev'] - timedelta(days=r['_ev'].weekday())).date()
                w[ws] += 1
        return w
    wk_oai = weekly(oai); wk_anth = weekly(anth)
    cur_wk = (NOW - timedelta(days=NOW.weekday())).date()
    wk_axis = [cur_wk - timedelta(weeks=k) for k in range(17, -1, -1)]
    weekly_table = [{'week': w.isoformat(), 'oai': wk_oai.get(w, 0), 'anth': wk_anth.get(w, 0)} for w in wk_axis]

    # recent severe (major/critical) events, last 30 days, newest first
    D30 = NOW - timedelta(days=30)
    severe = [r for r in oai + anth if r.get('impact') in ('major', 'critical') and r['_ev'] and r['_ev'] >= D30]
    severe.sort(key=lambda r: r['_ev'], reverse=True)
    severe_table = [{'date': r['_ev'].strftime('%Y-%m-%d %H:%M'), 'src': r['src'], 'impact': r['impact'],
                     'title': r['title'], 'duration_min': durmin(r)} for r in severe[:20]]

    # MTTR (90d)
    def mttr(cap):
        durs = sorted(d for d in (durmin(r) for r in cap) if d is not None)
        if not durs: return None
        n = len(durs)
        return {'median': durs[n // 2], 'p90': durs[min(int(n * 0.9), n - 1)], 'n': n}

    return {
        'generated_at': NOW.isoformat(),
        'archive_total': {'oai': len(oai), 'anth': len(anth)},
        'capacity_90d': {'oai': len(oc90), 'anth': len(ac90)},
        'major_critical_90d': {'oai': mc90(oc90), 'anth': mc90(ac90)},
        'mttr_90d': {'oai': mttr(oc90), 'anth': mttr(ac90)},
        'monthly': monthly_table,
        'weekly': weekly_table,
        'recent_severe': severe_table,
        'methodology_note': 'OpenAI 状态页(incident.io)只暴露最近约 3 个月 incident,过期永久消失;本数据集每日快照按 incident id 去重累加,逐步攒出状态页给不了的 OAI 长历史。Anthropic(Atlassian Statuspage)可追 ~12 个月。跨厂商绝对值不可比(Anthropic 按模型拆分上报,OpenAI 倾向合并上报),只比较各自趋势。',
    }


def main():
    print(f"[{TODAY}] fetching status pages…")
    try:
        oai_atom = fetch('https://status.openai.com/history.atom')
        oai_json = fetch('https://status.openai.com/api/v2/incidents.json')
        anth_pages = [fetch(f'https://status.claude.com/history?page={p}') for p in (1, 2, 3, 4)]
    except Exception as ex:
        print('  [FATAL] fetch failed:', ex); sys.exit(1)

    oai_new = parse_oai(oai_atom, oai_json)
    anth_new = parse_anth(anth_pages)
    print(f"  parsed: OAI {len(oai_new)}, Anth {len(anth_new)}")

    arch_oai = load_archive(ARCHIVE_OAI); arch_anth = load_archive(ARCHIVE_ANTH)
    before = (len(arch_oai), len(arch_anth))
    n_oai = merge(arch_oai, oai_new); n_anth = merge(arch_anth, anth_new)

    json.dump(list(arch_oai.values()), open(ARCHIVE_OAI, 'w'), indent=1, ensure_ascii=False)
    json.dump(list(arch_anth.values()), open(ARCHIVE_ANTH, 'w'), indent=1, ensure_ascii=False)

    summary = build_summary(arch_oai, arch_anth)
    json.dump(summary, open(SUMMARY, 'w'), indent=1, ensure_ascii=False)

    print(f"[done] archive: OAI {len(arch_oai)} (+{n_oai}), Anth {len(arch_anth)} (+{n_anth})")
    print(f"       90d capacity: OAI {summary['capacity_90d']['oai']}, Anth {summary['capacity_90d']['anth']}")


if __name__ == '__main__':
    main()
