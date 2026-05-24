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
| `GGG_POESESSID` | 空 | POE 账号登录 Cookie | 要用监控和交易搜索的话必须填 |
| `LEAGUES` | `Fate of the Vaal,Standard,...` | 刷数据的联赛，逗号分隔 | 否 |
| `CRAWL_INTERVAL_MINUTES` | `30` | 价格数据多久刷新一次 | 否 |
| `STASH_INTERVAL_MINUTES` | `5` | 公共仓库拉取间隔 | 否 |

### 怎么拿 POESESSID

浏览器登录 [pathofexile.com](https://www.pathofexile.com)，F12 → Application → Cookies，找 `POESESSID`，复制值贴到 `.env`。

这串字符等于你的账号密码，别发给任何人。`.env` 已经加在 `.gitignore` 里了，不会被提交。

## 每个页面干什么

导航栏有 7 个入口。

### Dashboard（首页）

四个数字卡片：货币、装备、宝石数量、最后更新时间。下面两张涨跌榜——24 小时涨幅 Top 5 和跌幅 Top 5。涨跌榜需要积累几次历史快照才有数据，刚部署时可能是空的。

最底部是三个快捷入口卡片。

### Currency（货币页）

顶部分三列：Chaos（基准 1）、Exalted、Divine 兑换率。下面通货列表有图标、名称、混沌石价格、神圣石换算。Mirror of Kalandra 这种高价的会用黄色标出来。

碎片和 Greater/Perfect 变体会自动过滤掉。页面每 5 分钟自动刷新。

### Items（装备页）

按分类浏览：防具、武器、饰品、珠宝、药剂、地图、通货、碎片。顶部分类标签切换。每件有图标、名称、价格。搜索框输入即过滤。

URL 加 `?lang=en` 切英文，`?lang=zh` 切回中文。

### Monitor（监控页）

核心功能。设置规则："如果 Headhunter 低于 50 divine，通知我"。系统通过 WebSocket 连着 GGG 的 Trade2 实时搜索，有符合条件的物品上架，立刻弹到页面上。

没填 POESESSID 的话，规则能创建但不能实际监控。页面顶部会有红色提示条。

**左边** 是规则列表，名称、物品、价格上限、开关。**右边** 是实时交易流，新发现从顶部插入，带折扣百分比、价格对比、卖家名。

点 `+ 新建` 创建规则。规则创建后立刻生效。

收到提醒时点 **复制密语**，切到游戏粘贴发给卖家。点 **打开页面** 可以看 Trade 网站详情。买完后点 **已购买** 记录到数据库。

本系统只做"发现 + 通知"，密语自己发，交易自己做。自动交易违反 GGG 协议。

### Gems（宝石页）

按技能/辅助分类，显示每一级、每一品质的价格。

### Trades（交易搜索页）

输入物品名、类型、最高价格，调 GGG Trade2 API 搜在线物品。结果有图标、名字、价格、卖家。点 `Track` 一键创建监控规则——物品名和价格自动填好。

### Purchases（购买记录页）

在 Monitor 标记"已购买"的记录会出现在这里。四个卡片：总购买次数、总花费、总节省、ROI。下面每笔明细表。

## 项目健康

```bash
# 跑测试
python -m pytest tests/ -v
# 12 passed ✅
```

**后台任务（3 个）：**

| 任务 | 频率 | 做什么 |
|------|------|--------|
| data_sync | 每 30 分钟 | 从 poe2scout 拉取货币、装备价格 |
| stash_poll | 每 5 分钟 | 轮询 GGG 公共仓库新上架物品 |
| price_compaction | 每天凌晨 3 点 | 聚合昨日快照到 price_history，清理 30 天前数据 |

**数据库**：SQLite，7 个性能索引，Alembic 迁移管理。

## API 文档

`http://127.0.0.1:8006/docs` 有 Swagger，可以直接在网页上测试。

常用接口：

| 方法 | 路径 | 做什么 |
|------|------|--------|
| GET | `/api/v1/dashboard/summary` | 仪表盘摘要（含涨跌榜） |
| GET | `/api/v1/currency` | 货币价格列表 |
| GET | `/api/v1/items` | 装备价格列表（支持分类过滤） |
| GET | `/api/v1/watchlist` | 列出所有监控规则 |
| POST | `/api/v1/watchlist` | 新建规则 |
| PUT | `/api/v1/watchlist/{id}` | 修改规则 |
| DELETE | `/api/v1/watchlist/{id}` | 删除规则 |
| GET | `/api/v1/deals` | 最近发现的交易机会 |
| GET | `/api/v1/deals/{id}/detail` | 单笔交易详情 + 价格曲线 |
| PUT | `/api/v1/deals/{id}/mark-purchased` | 标记已购买 |
| GET | `/api/v1/monitor/stream` | SSE 实时推送流 |

## 技术栈

Python 3.12 + FastAPI + SQLAlchemy 2.0 (async) + aiosqlite · Jinja2 + HTMX + Chart.js + Bootstrap 5 · APScheduler · SSE + Trade2 WebSocket · Alembic

数据来源：poe2scout.com API、GGG Public Stash API、GGG Trade2 API

## 目录结构

```
E:/project-poe2/
├── app/
│   ├── main.py              # 入口 & 生命周期
│   ├── config.py             # 从 .env 读配置
│   ├── database.py           # 异步 SQLAlchemy 引擎
│   ├── scheduler.py          # 3 个定时任务
│   ├── translations.py       # 中英文词典
│   ├── models/               # 9 张 ORM 表
│   ├── crawlers/             # 4 个数据采集器
│   ├── services/             # 7 个业务模块
│   ├── routers/              # 5 个路由模块
│   ├── templates/            # 页面模板 + 碎片
│   └── static/               # CSS + JS
├── alembic/                  # 数据库迁移
├── tests/                    # pytest (12 tests)
├── data/                     # SQLite 数据库
├── .env                      # 你的配置
├── requirements.txt
├── start.bat                 # Windows 一键启动
└── start.sh                  # Linux/macOS 一键启动
```
