# 发布计划

所有数字来自 2026-10-25 本地实跑的 `hn-glut build --jolts`。

## 先要知道的：这个数 HN 上有人说过

调研（[research.md](research.md)）发现，“求职/招聘比”在 HN 上至少被发过 5 次，都是一次性的：

| 日期 | 帖子 | 分 / 评论 |
|---|---|---|
| 2023-04-04 | Tell HN: The ratio of wants-to-be-hired to is-hiring is at a record high 0.94 | 363 / 185 |
| 2024-01-05 | Tell HN: This month, job seekers outnumber job openings on HN | 32 / 5 |
| 2024-05-01 | HN who is hiring ratio（bilbof 截图） | 4 / 4 |
| 2026-07-01 | Show HN: I visualized "Who's Hiring?" vs. "Who wants to be hired?" over time | 1 / 0 |
| 2026-08-13 | Tell HN: In 2021, there were 4.5 jobs per job seeker vs. 2.5 job seekers/job now | 11 / 4 |

所以标题和正文**不能说“第一次发现”或“没人注意到”**。可以说的、别人没做过的：
1. 一条持续更新、口径写清楚的序列（两种口径并列，能和 hnhiringtrends.com 的数对上）；
2. 按技能的“每个岗位几个求职者”；
3. 与美国 JOLTS 对照；
4. 可下载的 CSV。

2023 年那帖 363 分说明这个话题在 HN 上有读者。

## 时间

| 时间（北京时间） | 动作 |
|---|---|
| 10-26 ~ 11-01 | 你：建仓库、推送、开 Pages、上传 social preview（见下文“需要你做的”）。我这边可以按反馈修口径说明 |
| 11-03 00:00 前后 | 11 月招聘帖预计 11-02（周一）16:00 UTC 发出（按往年 1 日逢周末顺延到周一的惯例推算，未核实） |
| **11-03 晚 21:00～23:00（= 11-03 13:00～15:00 UTC，美东早 8～10 点）** | **发 Show HN**。此时 11 月帖已发出约 21 小时，人们正在看招聘帖，话题最热；但 11 月比值还没稳定，首发只用 10 月数 |
| 11-04 ~ 11-05 | 手动跑一次 `hn-glut build --jolts`，把 11 月“进行中”数更新进页面；在帖子下回复更新值 |
| 11-17 | 11 月帖关闭后（14 天）再跑一次，确认 11 月终值 |

备选：如果 11-03 来不及，11-04（周三）同一时段也可以。避开周五晚到周日。

## Show HN 标题草稿

HN 标题上限 80 字符，不用感叹号和形容词。

1. `Show HN: HN job seekers per job post, monthly since 2014 – 2.50 in October`（74）
2. `Show HN: Hn-glut – "Who wants to be hired" ÷ "Who is hiring", 2014–2026`（71）
3. `Show HN: 2.5 job seekers per HN job post; by skill and next to US JOLTS`（71）

推荐 1：数字在前、说清是什么；“since 2014”暗示长序列，和以往一次性截图区分开。

## 正文草稿（英文，发帖时贴）

> Every month HN has two threads: "Who is hiring?" and "Who wants to be hired?". I counted the top-level comments in both for every month since July 2014, when they started running side by side.
>
> October 2026: 799 seeker comments, 319 job posts, 2.50 seekers per post. August (2.52), October and September (2.31) are the three highest months in the series. October 2021 was 0.30. For comparison, the US had about 1.01 job openings per unemployed person in August (JOLTS / CPS).
>
> This has come up here before as one-off screenshots (0.94 in April 2023 was a "record" then). What's new here:
>
> - Two counting rules side by side: every top-level comment ever posted (Firebase `kids`, includes deleted and dead) and only what's visible today (Algolia). 21% of seeker comments since 2014 have since been deleted vs 7% of job posts, so visible-only numbers drift over time. The headline uses all comments.
> - Ratio per skill, pooled over 3 months, with plain regexes (no LLM). Go and Java have the most seekers per post (11.2, 10.0), ML and security the fewest (2.2, 1.4). Seekers list long tech stacks, so compare skills with each other, not with the overall ratio.
> - CSV/JSON you can download, a small Python CLI that rebuilds everything from the public HN APIs with caching, and a GitHub Action for monthly updates.
>
> Only counts are published, no comment text or usernames. HN is a narrow slice of the job market; this measures how crowded these threads are.
>
> Chart: https://majiayu000.github.io/hn-glut/ · Code: https://github.com/majiayu000/hn-glut

发帖前把正文里的数字和当天 `uv run hn-glut show` 的输出再对一遍。

## 预期问题和回答要点

- **“比值上升是因为求职者愿意发帖，不代表市场”**：同意，README Caveats 写了。给出 JOLTS 那张图作为外部参照。
- **“有人用 LLM 批量发求职帖”**：不检测，README 写了。可以提 10 月同帖内没有重复作者（原调研结论，本项目未复核，**发帖时不要当成本项目的结论**）。
- **“hnhiringtrends.com 早就有了”**：承认，它画两条线；我们的 visible 口径与它一致（10 月 266/695），区别是比值、两种口径、技能拆分、JOLTS、CSV。
- **“技能比值都比总比值高，有偏差”**：是，求职帖列技术栈，只看相对排序。

## 需要你做的

1. 建仓库 `majiayu000/hn-glut`（public），推 `main`。
2. Settings → Pages：Deploy from branch，`main` / root（仓库根目录已有 `index.html` 和 `.nojekyll`）。
3. Settings → General → Social preview：上传 `docs/social-preview.png`（1280×640）。
4. 确认 CI 绿。
5. 决定是否打开 `update.yml` 里的自动提交（删掉 `if: false`）；不打开的话每月手动跑一次 `uv run hn-glut build --jolts` 再提交 `data/`。
6. 发 Show HN（上面的时间和标题）。

## 不做

- 不发其他渠道的帖子（Reddit、Twitter、V2EX），除非你另行决定。
- 不发布到 PyPI。
