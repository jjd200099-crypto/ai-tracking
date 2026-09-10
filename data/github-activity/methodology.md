# Public GitHub Repository Activity

Collected September 10, 2026. Coverage: January 2025–August 2026.

| August 2026 | OpenAI | Anthropic |
|---|---:|---:|
| Commits | 3,543 | 2,785 |
| Text lines changed | 3,958,685 | 1,316,469 |

## Methodology

GitHub organization API inventories include 237 OpenAI and 84 Anthropic public repositories with fork=false. Of these 321 repositories, 190 had their history inspected, 130 had no pushes since before the reporting period, and one was empty. No unresolved collection failures remain. The commit audit contains 50,451 records.

History is taken from each current default branch. Commits are grouped by committer timestamp converted to UTC. Counts include merge commits. Lines changed sum text additions and deletions from non-merge commits, using Git rename detection at its default 50% similarity threshold. Binary files are excluded from text-line totals. Documentation, generated files, lockfiles, notebooks and datasets are included. Commits are counted separately per repository without cross-repository deduplication.

This measures organization repository activity, separately from Claude Code co-authored commits, which track tool usage.

## Interpretation

- Anthropic’s OpenROAD-flow-scripts repository is a read-only upstream mirror created in August 2026, but GitHub marks it fork=false. Its inherited history contributes 353,465 lines to June, or 40.8% of Anthropic’s June total. Current ownership does not establish historical authorship.
- One OpenAI ten-proofs commit contributes 550,770 lines in August, mainly Lean proof files. tunnel-client includes substantial SPDX software component inventory additions and deletions.
- Anthropic’s commerce-agents was created September 1 but contains an August 31 commit contributing 88,497 lines to August. Commit date does not establish when code became public.
- Public changes do not directly measure engineering productivity, model progress or product adoption, and exclude private repository activity.

## Validation and limits

All 40 company/month totals reconcile to the commit audit. An API spot check of openai/openai-node commit eea2292a4a523da9405161dde0a79ac5dc2ecb2a matches local Git: 63 additions and 13 deletions.

OpenROAD was fetched with history beginning in 2024 following full-clone network failures. All seven shallow boundaries reachable from its default branch predate the 2025 reporting window. Current repository ownership and default-branch history may differ from what was publicly visible in earlier months.

## Sources and downloads

- [GitHub repository API](https://docs.github.com/en/rest/repos/repos#list-organization-repositories)
- [GitHub commit API](https://docs.github.com/en/rest/commits/commits)
- [Monthly totals](monthly_totals.csv)
- [Repository detail](repository_monthly.csv)
- [Data and scripts](github_activity_reproduction.zip)

The archive includes audit CSVs, repository snapshots and Python scripts. To recollect, use Python 3, Git and an authenticated GitHub CLI. Run collect_github.py and then summarize_github.py in a separate working directory. The collector uses bundled inventory snapshots, caches repositories in work/ and writes results to outputs/. Inspect collection errors before relying on totals. Cached successful repositories are not automatically refreshed; use a new working directory and updated inventory for a new snapshot. This is a research reproduction, not a scheduled monitor.
