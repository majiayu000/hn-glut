# 与相邻工具的对比

数据取自 2026-10-25（star 与最近 push 来自 `gh api`；功能以各项目 README、源码和线上页面为准）。完整调研见 [research.md](research.md)。

## 一览

| 工具 | ★ | 最近更新 | 做什么 |
|---|---|---|---|
| hnhiringtrends.com（SimonBerens/hn-jobs） | 25 | 代码 2023-11，数据 2026-10-24 | 招聘 / 求职 / freelancer 三帖的一级评论数折线，两侧都能按关键词过滤 |
| bilbof/whoishiring-ratio | 10 | 2024-12-05 | Ruby 脚本，终端里画求职/招聘条形图 |
| ej29-r3d/hacker-news-hiring-trends | 0 | 2026-07-26 | 一次性文章：求职帖首次超过招聘帖 |
| hacker-job/hacker-job | 755 | 2026-10-21 | 招聘帖 LLM 抽取 + 29 个关键词趋势 |
| wacsvn/hiring-market-pulse | 1 | 2026-10-24 | 招聘帖 + JOLTS 的 dbt 管道和 Streamlit 看板 |
| ambarachristian/skills-radar | 0 | 2026-10-24 | 用 Claude 抽取 9、10 月招聘帖技能，MCP + agent |

## 逐项

✅ 支持　⚠️ 部分　— 不支持

| 能力 | hn-glut | hnhiringtrends | bilbof | ej29-r3d | hacker-job | hiring-market-pulse | skills-radar |
|---|---|---|---|---|---|---|---|
| 求职侧计数 | ✅ | ✅ | ✅ | ✅ | — | — | — |
| 直接给出“求职/招聘”比值序列 | ✅ | ⚠️ 只画两条线，比值要自己除 | ✅（终端条形图） | ⚠️ 只画占比 | — | — | — |
| 只数一级评论（不含回复） | ✅ | ✅ | — 用 `descendants`，含回复 | — 用 `num_comments`，含回复 | — | — | — |
| 起始月份 | 2014-07 | 2011-04（求职帖 2014-07） | 2014-05 | 2019-01 | 2012-12 | 近 3 年 | 2026-09 |
| 同时给“含删帖”和“仅可见”两种口径并写明差异 | ✅ | — 只有 Algolia 可见口径，未写明 | — | — | — | — | ⚠️ 写了删帖数 |
| 按技能算“每个岗位几个求职者” | ✅ 29 个技能，3 个月滚动 | ⚠️ 两侧可分别过滤关键词，不算比值 | — | — | — 只有招聘侧 | — | — |
| 叠加美国 JOLTS | ✅ 空缺/失业 | — | — | — | — | ✅ 只对比招聘帖与空缺数 | — |
| 可下载数据（CSV/JSON） | ✅ | ⚠️ 前端用的 JSON 可直接取，未声明 | — | ✅ CSV | ✅ | ⚠️ Databricks 内 | — |
| 不依赖 LLM，结果可复现 | ✅ | ✅ | ✅ | ✅ | — | ⚠️ 部分字段用 LLM | — |
| 每月自动更新 | ✅（Action 已写好，推送默认关闭） | ✅ | — | — | ✅ | ✅ | — |
| 不保存求职者正文 / 联系方式 | ✅ 只发布计数 | ⚠️ 前端拉取的 `full-data.json`（141 MB）带评论正文（实查到招聘侧正文；求职侧是否也带未核实） | ✅ | ✅ | 不涉及 | 不涉及 | 不涉及 |

## 结论

- 求职侧的原始计数 hnhiringtrends.com 已经有，hn-glut 不靠“独家数据”取胜。差别在于：把**比值本身**做成主角，口径公开、两种口径并列；**按技能的求职/岗位比**和 **JOLTS 对照**目前没有别人做。
- hn-glut 不做：按公司、城市、薪资的招聘分析（用 hacker-job、hnhiring.com），按人搜索求职者（刻意不做）。
- 数字对得上：hn-glut 的 `visible` 口径与 hnhiringtrends.com 的数一致（2026-10 招聘帖都是 266，它的求职帖是 695），`all` 口径与 Firebase `kids` 一致（319）。
