# POE2 Analytics

一个 Python FastAPI 应用，用来爬 POE2 的市场数据，发现低价物品，实时通知你去买。

## 5 分钟跑起来

```bash
pip install -r requirements.txt

# 编辑 .env，填上 POESESSID（怎么获取看下一节）
# 然后：

python -m uvicorn app.main:app --host 127.0.0.1 --port 8006 --reload
```

浏览器打开 `http://127.0.0.1:8006`。Windows 下也可以双击 `start.bat`。

## 启动前要做的事

打开 `.env`，改这几项：

| 配置 | 默认值 | 说明 | 必须？ |
|------|--------|------|--------|
| `GGG_POESESSID` | 空 | POE 账号登录 Cookie | 要用监控功能的话必须填 |
| `LEAGUES` | `Fate of the Vaal,Standard,...` | 刷数据的联赛，逗号分隔 | 否 |
| `CRAWL_INTERVAL_MINUTES` | `30` | 价格数据多久刷新一次 | 否 |
| `STASH_INTERVAL_MINUTES` | `5` | 公共仓库拉取间隔 | 否 |

### 怎么拿 POESESSID

1. 浏览器登录 [pathofexile.com](https://www.pathofexile.com)
2. 按 F12 → Application → Cookies
3. 找 `POESESSID`，把它的值复制出来
4. 贴到 `.env` 的 `GGG_POESESSID=` 后面

这串字符等于你的账号密码，别发给任何人。`.env` 已经加在 `.gitignore` 里了，不会被提交。

## 每个页面干什么

导航栏有 5 个入口：

### Dashboard

打开就是。四个数字卡片显示库里有多少货币、装备、宝石，以及最近一次数据更新时间。下面是三个快捷入口。

数据是空的？别急，启动后后台会自动去 poe2scout 拉数据，等几分钟刷新就好。

### Currency（货币页）

顶部三个数字：Chaos 是基准（1），Divine 显示当前混沌石兑换率，Exalted 暂无数据。

下面是通货列表。每行有物品图标、名称、混沌石价格、神圣石换算。像 Mirror of Kalandra 这种高价值物品会用黄色标出来。

碎片和 Greater/Perfect 变体会自动过滤掉，不会在列表里出现。页面每 5 分钟自动刷新。

### Items（装备页）

按分类浏览：防具、武器、饰品、珠宝、药剂、地图、通货、碎片。点顶部分类标签切换。

每件物品显示小图标、名称、价格。顶部有搜索框，输入即过滤。点物品名进详情页。

URL 加 `?lang=en` 切英文，`?lang=zh` 切回中文。导航栏右边也有快捷切换按钮。

### Monitor（监控页 — 重点功能）

这里才是最有用的部分。你可以设置规则："如果 Headhunter 低于 50 divine，通知我"。系统通过 WebSocket 连着 GGG 的 Trade2 实时搜索，有符合条件的物品上架，立刻弹到页面上。

没填 POESESSID 的话，规则能创建但不能实际监控（Trade2 需要登录态）。

#### 界面说明
- **左边：** 你的规则列表。每条规则显示名称、监控的物品、价格上限、开关
- **右边：** 实时交易流。新发现的物品会从顶部插入，带折扣百分比、价格对比、卖家名

#### 怎么创建规则
1. 点左边 `+ 新建`
2. 填表单：
   - **规则名称：** 自己看的标签，比如"便宜 Headhunter"
   - **物品名称：** 要蹲的物品，比如 `Headhunter`
   - **最高价格（混沌石）：** 比这个贵的直接跳过
   - **最低折扣 %：** 填 15 表示"低于市价 15% 才提醒"
3. 点创建

规则创建后立刻生效。

#### 收到提醒后怎么办
每条提醒卡片有三个操作：
- **复制密语：** 密语进剪贴板，切到游戏里粘贴发给卖家
- **打开页面：** 新标签页打开 Trade 网站，可以看物品详情
- **已购买：** 标记交易完成，记录到数据库里

本系统只负责"发现 + 通知"。密语得你自己发，交易得你自己做。自动交易违反 GGG 用户协议，有封号风险。

### Gems（宝石页）

按技能宝石 / 辅助宝石分类。显示每一级、每一品质的价格。数据和其他页面一样，后台自动刷新。

## API 文档

`http://127.0.0.1:8006/docs` 有完整的 Swagger 文档，可以直接在网页上测试。

几个常用接口：

| 方法 | 路径 | 做什么 |
|------|------|--------|
| GET | `/api/v1/watchlist` | 列出所有监控规则 |
| POST | `/api/v1/watchlist` | 新建规则 |
| PUT | `/api/v1/watchlist/{id}` | 修改规则 |
| DELETE | `/api/v1/watchlist/{id}` | 删除规则 |
| GET | `/api/v1/deals` | 最近发现的交易机会 |
| GET | `/api/v1/monitor/stream` | SSE 实时推送流 |

## 用了什么

Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + aiosqlite 做后端，Jinja2 + HTMX + Alpine.js + Chart.js + Bootstrap 5 做前端，APScheduler 跑定时任务，SSE 做实时推送。

数据从 poe2scout.com API、GGG Public Stash API、GGG Trade2 API 三个地方来。

## 目录结构

```
E:/project-poe2/
├── app/
│   ├── main.py              # 入口 & 生命周期管理
│   ├── config.py             # 从 .env 读配置
│   ├── database.py           # 异步 SQLAlchemy 引擎
│   ├── scheduler.py          # 两个定时任务
│   ├── translations.py       # 中英文字典
│   ├── models/               # 10 张 ORM 表
│   ├── crawlers/             # 3 个数据采集器
│   ├── services/             # 6 个业务模块
│   ├── routers/              # 5 个路由模块
│   ├── templates/            # 页面模板
│   └── static/               # CSS + JS
├── data/                     # SQLite 数据库
├── .env                      # 你的配置
├── requirements.txt
├── start.bat
└── start.sh
```
