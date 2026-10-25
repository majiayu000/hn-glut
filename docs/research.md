# hn-glut 竞品调研

数据取自 2026-10-25（北京时间）。star 数与最近 push 来自 `gh api`，站点内容用 curl 或内置浏览器实查。没查到的写“未核实”。

## 1. 查询方法

- **GitHub 仓库搜索**（`gh api search/repositories`，按 star 排序，每次间隔 2.5 秒）。拆词 14 组，其中 2 词短查询 6 组：
  `whoishiring`、`who wants to be hired`、`wants hired`、`hn hiring`、`hiring ratio`、`whoishiring ratio`、`hn job seekers`、`hacker news hiring`、`hn jobs`、`who is hiring`、`hiring trends`、`skills radar`、`hn hiring data`、`seekers per job`。
- **HN 帖子**（Algolia `search?tags=story`）：`who wants to be hired ratio`、`job seekers outnumber`、`wants to be hired`、`whoishiring ratio`、`hiring threads seekers`、`hn hiring trends`、`who is hiring trends`、`hiring-market-pulse`、`skills radar`。
- **数据集**：Hugging Face `api/datasets?search=`（`hacker news hiring`、`who is hiring`、`whoishiring`、`hn jobs`、`hackernews jobs`、`wants to be hired`）；Kaggle 没有本机凭据，用 WebSearch 查（只找到 Baselight 上的一个 Kaggle 镜像）。
- **站点**：hnhiringtrends.com、hnhiring.com/trends、hntrends.com、hnhiring.josusanmartin.com、austinmunday.github.io/hn-hiring-charts、hacker-job.com、hnwork.app，直接抓取并搜 `wants to be hired|seeker|ratio`。

## 2. 结论先说

1. **“求职/招聘比”这个数在 HN 上已经被人说过好几次，原报告“HN 上还没人发这个数”不成立。** 但每次都是一次性的 Tell HN / 截图，没有一个持续更新、口径公开、可下载的序列：
   - 2023-04-04 `Tell HN: The ratio of wants-to-be-hired to is-hiring is at a record high 0.94`（jstx1，**363 分 / 185 评论**），一张 pasteboard 截图。
   - 2024-01-05 `Tell HN: This month, job seekers outnumber job openings on HN`（32 分）。
   - 2024-05-01 bilbof 的 `HN who is hiring ratio`（4 分）。
   - 2026-07-01 `Show HN: I visualized "Who's Hiring?" vs. "Who wants to be hired?" over time`（1 分，链接到 Bluesky 帖子）。
   - **2026-08-13 `Tell HN: In 2021, there were 4.5 jobs per job seeker vs. 2.5 job seekers/job now`**（ed_balls，11 分 / 4 评论），正文只有一句“based on hnhiringtrends.com”。
   这说明话题本身有人关心（2023 年那帖 363 分），但首发不能再用“第一个发现”的说法，要用“持续更新 + 公开口径 + 按技能拆分 + 和 JOLTS 对照”。
2. **最接近的现役对手是 hnhiringtrends.com（SimonBerens/hn-jobs，25★）**。仓库最后 push 2023-11，但后台 cron 仍在跑：数据文件 `prd-data.hnhiringtrends.com/small-data.json` 的 `Last-Modified` 是 2026-10-24 00:25 GMT，10 月招聘帖记录为 266 条一级评论。页面画的是 Hiring / Looking 两条线（2011 年起），还能对两侧分别做关键词过滤。**它缺的是**：没有直接画比值，没有按技能算比值，不能下载 CSV，不说明删帖/dead 的口径（从 266 这个数看是 Algolia 的未删除口径），没有 JOLTS。
3. **按技能看“求职者/岗位”的比值、以及和 JOLTS 对照，仍然没人做。** 只统计招聘侧技能的项目很多（hacker-job、hiring-market-pulse、skills-radar、hntrends 等）。
4. **没有数据集提供求职侧计数。** HF 上 brusic 的数据集明确写了“For privacy reasons, job seeker posts will not be included”；其余只覆盖招聘帖或某一个月。

## 3. 同类：直接做“求职 vs 招聘”的

| 项目 | ★ / 最近更新 | 做了什么 | 缺什么 |
|---|---|---|---|
| [bilbof/whoishiring-ratio](https://github.com/bilbof/whoishiring-ratio) | 10 / 2024-12-05 | Ruby 脚本，读 Firebase `user/whoishiring` 的 `submitted`，按标题含 `hiring` / `wants` 分组，输出终端条形图；仓库里只有 4 张 2024 年截图 | 用的是 `descendants`（**所有层级评论，含回复**），不是一级评论；2014-05 起；不更新；无数据文件、无网页 |
| [SimonBerens/hn-jobs](https://github.com/SimonBerens/hn-jobs)（hnhiringtrends.com） | 25 / 仓库 2023-11-06，数据 2026-10-24 | Next.js 静态站 + cron 抓 Algolia，画 Hiring / Looking / Freelancer 一级评论数，支持关键词过滤 | 见第 2 节第 2 条 |
| [ej29-r3d/hacker-news-hiring-trends](https://github.com/ej29-r3d/hacker-news-hiring-trends) | 0 / 2026-07-26 | 一篇文章“'Who wants to be hired' now outnumbers 'Who is hiring'”，3 张 D3 图，`data/fetch.py` 生成 CSV | 用 Algolia `num_comments`（**含回复**）；只从 2019-01 开始；一次性，07-26 后没更新；无技能拆分 |
| HN 帖子（见上） | 2023-04 ~ 2026-08 | 一次性截图 / 一句话 | 无代码、无口径 |
| [Manifold “hn whoishiring posts”](https://manifold.markets/news/hn-whoishiring-posts) | 2023～24 | 预测盘，按月问 hiring 占 hiring+looking 的比例（约 36～42%） | 只到 2024 年初（WebSearch 摘要，未逐页核实） |

## 4. 相邻：只看招聘侧

| 项目 | ★ / 最近 push | 做了什么 | 和 hn-glut 的关系 |
|---|---|---|---|
| [hacker-job/hacker-job](https://github.com/hacker-job/hacker-job) | 755 / 2026-10-21 | hacker-job.com，LLM 抽取 88k 条岗位，29 个关键词趋势 | 只有招聘侧。它加一个求职侧只要一个周末，是最大的潜在对手 |
| [ryanwi/hiringtrends](https://github.com/ryanwi/hiringtrends)（hntrends.com） | 72 / 2024-08-26 | 每月一篇语言/工具排行 | 只有招聘侧，2024 年后停更 |
| [nemanjam/hn-new-jobs](https://github.com/nemanjam/hn-new-jobs) | 82 / 2026-04-07 | 区分首次/新/老公司 | 只有招聘侧 |
| hnhiring.com/trends（[jordinl/hnhiring](https://github.com/jordinl/hnhiring) 18★） | 2026-04-29 | 招聘帖技术关键词趋势（HN 2025-01 帖 111 分） | 抓取页面未见 seeker / wants 字样，只有招聘侧 |
| hnhiring.josusanmartin.com | HN 2026-06-23 Show HN | 按月按类别的招聘趋势 | 只有招聘侧 |
| [AustinMunday/hn-hiring-charts](https://github.com/AustinMunday/hn-hiring-charts) | 0 / 2026-08-16 | 2011 起 185 个招聘帖、94,807 条岗位的图表（薪资披露、混合办公、AI 提及） | 只有招聘侧；一次性 |
| [wacsvn/hiring-market-pulse](https://github.com/wacsvn/hiring-market-pulse) | 1 / 2026-10-24（10-22 建） | 招聘帖 + **BLS JOLTS** → dbt/Databricks → Streamlit 看板，52 个数据测试 | **唯一也叠加 JOLTS 的**，但只对比招聘帖活跃度和 JOLTS 空缺数，不看求职侧；只覆盖近 3 年 |
| [ambarachristian/skills-radar](https://github.com/ambarachristian/skills-radar) | 0 / 2026-10-24（10-24 建） | 用 Claude 把 9、10 月招聘帖抽成结构化字段（技能 F1 93%），MCP 工具 + agent 问答 | 只有招聘侧、只有两个月、依赖 LLM；它报告 9+10 月 619 条一级回复里 72 条作者删除、32 条被版主移除，可作为口径差异的旁证 |
| [cncf/hnscraping](https://github.com/cncf/hnscraping)、[Amber-Williams/hackernews-whos-hiring](https://github.com/Amber-Williams/hackernews-whos-hiring) 等 | — | 抓取 / SQL 化 | 只有招聘侧 |
| 求职侧抓取：[dsposito/hackernews-recruiter](https://github.com/dsposito/hackernews-recruiter)（9★，2016）、InterfazeAI/hackernews-jd-matcher（2★）、valehelle/peridot、narskidan/hn-candidate-search | — | 抓求职帖给招聘方筛人 | 方向相反（按人搜索），hn-glut 刻意不做 |

## 5. 数据集

| 数据集 | 内容 | 求职侧？ |
|---|---|---|
| HF [brusic/hacker-news-who-is-hiring-posts](https://huggingface.co/datasets/brusic/hacker-news-who-is-hiring-posts)（MIT，2026-09-19 更新，242 下载） | 2011-04 起招聘帖与 freelancer 帖的全部一级评论正文 | **否**，README 原文 “For privacy reasons, job seeker posts will not be included” |
| HF [dansbecker/hackernews_hiring_posts](https://huggingface.co/datasets/dansbecker/hackernews_hiring_posts)（2021-12） | BigQuery 导出的 hiring / wants_to_be_hired / freelancer 三表 | 有，但 2021 年后不更新，作者自述不可复现 |
| HF soup1984/hn-whoishiring-2026-10（10-25 建） | 10 月招聘帖 233 行表头字段 | 否，只有一个月 |
| HF kalyan33、logiover 样例、gemmozero/ai-hnjobs-2026（需登录） | 招聘帖 | 否 / 未核实 |
| Kaggle “kidrulit hackernews who is hiring listings from 2018”（经 Baselight 镜像看到） | 2018～2023 年中的招聘帖字段 | 否；Kaggle 原页和许可未核实 |
| Apify 若干付费 actor | 按需抓取 | 是抓取服务，不是数据集 |

## 6. 对设计的影响

- 卖点从“第一个发现比值创新高”改成：**一个可复现、每月自动更新、口径写清楚的比值序列**，加上两项没人做的：**按技能的求职者/岗位比** 和 **JOLTS 对照**。
- 口径必须同时给出两个：Firebase `kids` 全量（含删帖，和原报告 2.50 一致）与 Algolia 可见口径（和 hnhiringtrends.com 的 266 一致）。别人一对数就能对上，避免“你的数和 X 站不一样”的争论。
- 不保存、不发布任何求职帖正文、用户名或联系方式（brusic 数据集也是这个立场），只发聚合计数。
- hacker-job 是最可能跟进的对手，首发节奏要快。
