# AI Intelligence Dashboard

ChatGPT / Gemini / Claude 全平台数据追踪仪表盘，覆盖 Mobile、Web、Coding Agent 三个维度。

## Live Dashboard

👉 **[https://jjd200099-crypto.github.io/ai-tracking/](https://jjd200099-crypto.github.io/ai-tracking/)**

## 三个视图

### Mobile (Sensor Tower)
- **KPI**：MAU / WAU / DAU / Downloads，含 MoM 变化
- **Monthly Trend**：DAU → WAU → MAU → Downloads 可切换
- **DAU / MAU Ratio**：用户粘性趋势
- **iOS vs Android**：平台拆分柱状图
- **Market Share Evolution**：DAU / WAU / MAU / Downloads 份额趋势
- **Avg Time Spent**：日均使用分钟、单次会话时长、日均会话次数
- **Top 20 Countries**：国家维度 DAU / MAU / Downloads 柱状图
- **Country Growth Table**：MAU / DAU 净增量 + MoM%，按 app 拆分
- **Monthly Net Increase**：DAU / MAU 月度净增量
- **New User Share**：新增用户占比分布
- **MoM Growth Rate**：DAU / MAU 环比增速
- **Ratio vs ChatGPT**：Gemini & Claude 相对 ChatGPT 的 DAU / MAU / DL 比值

### Web (Semrush)
- 与 Mobile 对应的全套图表（无 Downloads、无 iOS/Android）
- **Avg Visit Duration**：15 个月平均访问时长趋势
- 国家数据按 ChatGPT / Gemini / Claude 分别展示

### Coding Agent (npm + GitHub)
- **Claude Code vs Codex**：npm 周下载量趋势
- **Market Share**：CC 份额从 99%（Jul '25）收窄至 75%（Mar '26）
- **CC / Codex Ratio**：倍数变化趋势
- **Cumulative Downloads**：累计下载面积图
- **GitHub Commits**：Claude Code 月度 co-authored commits（10.3M in Mar '26）

## 数据源

| 视图 | 数据源 | 更新频率 |
|------|--------|----------|
| Mobile | Sensor Tower Enterprise | 月度 |
| Web | Semrush | 月度 |
| Coding | npm Registry API + GitHub | 实时 |

## 数据截止

- Mobile / Web：**2026 年 3 月**
- Coding Agent：**2026 年 4 月 13 日**

## 技术栈

- 纯前端单文件：HTML + CSS + JavaScript
- 图表引擎：Chart.js 4.4
- 字体：Fraunces + Plus Jakarta Sans + IBM Plex Mono
- 部署：GitHub Pages（自动）

## 更新方式

1. 从 Sensor Tower / Semrush 导出新月份 CSV
2. 运行数据处理脚本更新 `index.html` 中的 DATA 对象
3. Push 到 main 分支，GitHub Pages 自动部署
