# hn-glut 设计

## 目标与边界

`hn-glut` 回答一个问题：**HN 每月“Who wants to be hired?”的一级评论数，是“Who is hiring?”的几倍？** 从两帖同时存在的 2014-07 起给出连续序列，并按技能拆分，可选叠加美国 JOLTS 的“空缺数 / 失业人数”。

- 产物：可离线重跑的 CLI → `data/` 下的 CSV/JSON 数据集 → 一张读这些 JSON 的静态网页（GitHub Pages）→ 每月自动重跑的 GitHub Action（写好，默认不推送）。
- 只发布聚合计数。**求职帖正文、用户名、联系方式不进仓库**；原始 API 响应只缓存在本机 `.cache/`（gitignore）。
- 不做：按人搜索、LLM 抽取、实时服务、数据库。

## 1. 数据来源

| 来源 | 用途 | 请求量（全量回填） | 限流 / 口径 |
|---|---|---|---|
| Firebase `hacker-news.firebaseio.com/v0/user/{whoishiring,_whoishiring}.json` | `submitted`：两个账号发过的全部 item id（2026-10-25 实测 551 + 9 个） | 2 | 官方 README 不写限流（“no rate limit” 未写成承诺，按礼貌访问处理）。返回的 id 包括 dead/删除的帖子 |
| Firebase `/v0/item/{id}.json` | 帖子标题、发帖时间、`kids`（一级评论 id，**含已删除和 dead**） | ≈551 | 同上；单个请求小、快 |
| Algolia `hn.algolia.com/api/v1/items/{id}` | 整棵评论树，取一级 `children`（**只含可见评论**）及正文，用于“可见口径”和技能统计 | 两类月帖各一个/月，≈300 | 文档写每 IP 每小时 10,000 次；大帖单次 5～10 秒 |
| FRED `fred.stlouisfed.org/graph/fredgraph.csv?id=JTSJOL,UNEMPLOY` | BLS 原始序列的镜像：`JTSJOL`（JOLTS 空缺，非农总计，季调，千）与 `UNEMPLOY`（CPS 失业人数，季调，千） | 1 | 不需要 key。原计划直连 BLS Public API v1，但 2026-10-25 实测 `api.bls.gov` 对 GET/POST 都返回 503 “The BLS website is busy”，所以改走 FRED；最新月是初值，会被修订 |

所有 HTTP 请求：
- `User-Agent: hn-glut/<版本> (+https://github.com/majiayu000/hn-glut)`，不带邮箱。
- 串行，两次请求间至少间隔 `--delay`（默认 Firebase 0.2 秒、Algolia 1 秒）；失败重试 3 次，指数退避；最终失败直接报错退出，不写半截数据。
- 每个响应原样写入 `.cache/<source>/<id>.json`。缓存命中就不再请求（见第 5 节的刷新规则）。

### 实测口径差异（2026-10 招聘帖，id 49922569，2026-10-25 测）

| 口径 | 数 | 说明 |
|---|---|---|
| Firebase `kids` | 319 | 一级评论 id 全集 |
| 逐个取 `kids` 的 item | live 266 / deleted 34 / dead 19 | 合计 319 |
| Algolia `children` | 266 | 与 live 完全相等（每条都有 text 和 author） |
| Firebase `descendants` | 395 | 含回复，bilbof 用的就是这个 |
| 同口径，2026-10 求职帖（id 49922568） | kids 799 = live 694 + deleted 86 + dead 19；Algolia 695；descendants 703 | Algolia 比逐条统计多 1：逐条取 799 个 item 花了几分钟，期间多了一条可见评论，属于取数时刻差异 |

结论：**Algolia children = kids − deleted − dead**。所以不需要逐条取 15 万个 kid，两个来源各一次请求就能同时得到两种口径。

## 2. 帖子识别

只认 `whoishiring` 账号，以及 2015 年 4、5 月临时代发的 `_whoishiring` 账号（共 9 个 submitted；第一次全量回填时发现这两个月缺帖，查 Algolia 才知道是它发的）`submitted` 里的 story，按标题归类（大小写不敏感，允许首尾空格和月份后的逗号）：

| 类型 | 标题正则 |
|---|---|
| `hiring` | `^Ask HN: Who is hiring\? \((Month) (YYYY)\)$` |
| `seeking`（想被雇） | `^Ask HN: Who wants to be hired\? \((Month) (YYYY)\)$` |
| `freelancer` | `^Ask HN: Freelancer\? Seeking freelancers?\? \((Month) (YYYY)\)$` |

- 月份取**标题里的月份**，不用发帖时间（1 月帖常在 1 月 2 日发，周末顺延到周一）。
- 不符合三种格式的（如 2020-03 的 “Who is hiring right now?”、2012 的 “Who is meeting up?”）不计入，原样列进 `data/skipped.csv`（id、标题、日期），便于核查。
- 同一类型同一月份出现两帖时报错退出（2026-10-25 实测没有），不静默取其一。
- `dead` 或 `deleted` 的帖子本身跳过并列入 skipped。
- 比值只在两帖都存在的月份给出；缺一帖的月份在 CSV 里留空，不插值。

## 3. 计数口径（先定，后出数）

每帖两个数：

- **`all`**（主口径）= Firebase `len(kids)`：有人在这一帖发过的一级评论数，含作者后来删除的、被 flag 成 dead 的。
- **`visible`** = Algolia 一级 `children` 中 `text` 和 `author` 都非空的条数：现在还能看到的。

主口径选 `all`，理由（与结果无关）：
1. 帖子发出两周后关闭，`kids` 基本不再变化；`visible` 会随年份流失——求职者找到工作后删帖、旧账号删号——越老的月份删得越多，跨年比较会系统性偏移。
2. 对一个“有多少人来发帖”的问题，删帖的人当时也来发过。
3. 两个 Firebase 请求就能算，对 HN 压力最小。

`all` 的已知缺陷：含 spam（dead）。所以页面和 CSV 同时给 `visible` 口径的比值，README 写明两者差异。比值 = 求职 ÷ 招聘，四舍五入两位小数，CSV 里保留原始计数，任何人可以自己重算。

进行中的月份：发帖不足 14 天时 `complete=false`，页面上画成虚线点并标注“未结束”；不在“历史最高”排名中参与比较。

## 4. 技能拆分

- 输入：Algolia 可见评论的正文（HTML 去标签、反转义后转小写）。删除的评论没有正文，所以技能只能用 `visible` 口径。
- 方法：确定性的关键词正则，**每个技能一条正则，带词边界**，每条评论命中一次记 1。正则表放在 `src/hn_glut/skills.py`，改动必须加 fixture 测试。首批 29 个：python、javascript、typescript、react、node、go、rust、java、kotlin、swift、c++、c#/.net、ruby、php、elixir、scala、sql、aws、kubernetes、ml（`machine learning|\bml\b|pytorch|tensorflow`）、llm（`llms?|genai|gpt|rag`）、ai agents（`agents?|agentic`）、data engineering、devops/sre、frontend、ios、android、security、embedded。
  - 歧义词特别处理：`go` 只认 `\bgolang\b` 或 `\bgo\b` 后接 `,`/`/`/`)`/行尾 或前面是 `,`/`/`/`(`（技术栈列表语境），不认 “go to”；`rust` 与 `swift` 不处理同形英文词（误伤可接受，在 README 写明）。
- 输出：每月每技能的 `hiring_hits`、`seeking_hits`，以及**3 个月滚动**的 `seekers_per_job = Σseeking_hits / Σhiring_hits`。
- 已知偏差（README 必须写）：求职帖大多按 “Technologies:” 模板列一长串技术，所以单个技能的比值普遍高于总比值；**只能比较技能之间的相对高低**，不能读成绝对数。

## 5. 缓存与增量

- `.cache/firebase/item/<id>.json`、`.cache/algolia/items/<id>.json`、`.cache/fred/jolts.csv`、`.cache/firebase/user-whoishiring.json`。
- 刷新规则：
  - `user/whoishiring` 每次运行都重新取（新帖要靠它发现）。
  - 帖子 item 和 Algolia 树：发帖超过 `--freeze-days`（默认 30 天）的缓存永久有效；更新的每次重新取。
  - FRED 每次运行都重新取（会修订）。`--offline` 时只用缓存，缓存缺失则报错。
- 一次全量回填约 550 个 Firebase 请求 + 约 300 个 Algolia 请求 + 1 个 FRED 请求；之后每月一次增量约 3 + 4 个。

## 6. 输出

```
data/
  monthly.csv      month, hiring_id, seeking_id, freelancer_id,
                   hiring_all, seeking_all, ratio_all,
                   hiring_visible, seeking_visible, ratio_visible,
                   freelancer_all, complete
  skills.csv       month, skill, hiring_hits, seeking_hits, hiring_hits_3m, seeking_hits_3m, seekers_per_job_3m
  jolts.csv        month, openings_k, unemployed_k, openings_per_unemployed   （--jolts 时）
  skipped.csv      id, title, date, reason
  hn-glut.json     以上合并 + generated_at + 口径说明，供网页读取
```

CLI：

```
hn-glut build  [--out data] [--cache .cache] [--jolts] [--offline] [--since 2014-07]
hn-glut show   [--out data]          # 打印最新月份与历史最高 5 个月
```

网页 `index.html`（仓库根目录，GitHub Pages 直接按分支根目录发布，不需要构建步骤）：单文件，原生 JS 画 SVG，不依赖 CDN，读同目录的 `data/hn-glut.json`。首屏一个大数字（最新完整月的 `ratio_all`）和几条事实；下面依次是：2014 年起的比值折线（两种口径各一条，y=1 虚线）；JOLTS“空缺/失业”单独一张小图，与上图共用月份横轴（**不做双纵轴**，两个量纲不同的比值放同一张图会误导）；技能条形图（最新 3 个月滚动值，招聘侧命中少于 20 次的技能不显示，并画出同期总比值的参考线）；一张可展开的逐月数据表。

## 7. 自动更新

`.github/workflows/update.yml`：每月 3 日、16 日 UTC 跑 `hn-glut build --jolts`，把 `data/` 作为 artifact 上传。提交回仓库的那一步写好但被 `if: false` 关掉，由维护者决定何时打开。CI（`ci.yml`）只跑离线测试。

## 8. 测试

`tests/fixtures/` 放手工裁剪的小样本（2 个月的 Firebase item、Algolia 树，正文替换成合成文本，不含真实求职者信息），用注入的假 HTTP 层运行完整的 build，断言 CSV 内容。测试不联网。
