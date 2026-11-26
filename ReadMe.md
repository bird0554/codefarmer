# CODEFARMER API Gateway

[简体中文](ReadMe.md) | [English](README.en.md)

参考 CODEFARMER / New API 公开页面构建的 AI API 网关演示站，包含 React 前端、FastAPI、SQLite 持久化数据库、定时价格采集器和 Docker Compose 部署。页面使用独立实现，不复制目标站源码或受保护资产。

## GitHub 发布边界

本仓库仅发布 CodeFarmer 网关的 `api/`、`web/`、`crawler/`、`nginx/`、Docker 配置和项目说明。根目录中的其他独立项目、运行数据库、日志、依赖目录、前端构建产物和本地配置均不属于本仓库；根级 `.gitignore` 会阻止这些内容被误加入版本控制。`.env.example` 提供采集配置参考；不要提交真实凭据。中文和英文 README 应随相关功能及使用方式变化同步维护。

## 目录

- `web/`：Vite + React 前端，提供首页、模型广场、模型详情、价格、排行榜、登录/注册，以及登录后的控制台、API 密钥、渠道、钱包、用量日志、Playground 和个人资料数据页面；`web/src/TicketFlowPage.tsx` 与 `web/src/ticket-flow.css` 提供独立的工单流转演示界面。
- `api/`：FastAPI 服务，提供价格、状态、公告、排行榜、认证，以及登录用户的 API 密钥、钱包流水、用量日志、渠道和模型路由接口；`api/app/database.py` 使用 SQLite 持久化后端业务数据。
- `crawler/`：抓取公开价格与状态接口，保存快照和历史。
- `nginx/`：SPA 回退和 `/api/` 反向代理配置。
- `Dockerfile`、`docker-compose.yml`：容器镜像构建和部署配置。
- `.gitattributes`：固定 Shell 脚本使用 LF 换行，确保从 Windows 克隆后仍可在 Linux 容器中启动。
- `ReadMe.md`、`README.en.md`：中文和英文使用说明；`IMPLEMENTATION_PLAN.md`：实现计划。

## 启动

安装 Docker Engine / Docker Desktop 及 Docker Compose，在仓库根目录执行：

```bash
docker compose up -d --build
```

打开 <http://localhost:18002>。Web 容器在内部监听 `8080`，发布到主机的 `0.0.0.0:18002`；同一局域网内可通过部署主机 IP 的 `18002` 端口访问（需主机防火墙允许）。Nginx 将 `/api/` 转发到 API 服务，并对前端路由提供 SPA 回退。

价格快照、历史和 SQLite 数据库写入 Docker 卷 `pricing_data`（实际卷名可能带 Compose 项目前缀），数据库为 `/data/app.db`。普通容器重建会保留命名卷；`docker compose down -v` 会删除该卷及其中数据。

### 配置

| 配置项 | 服务 | 当前默认值或用途 |
| --- | --- | --- |
| `SOURCE_URL` | crawler / api | 公开价格数据源 `https://newapi.zxdj.club/api/pricing`；API 用于数据源信息 |
| `STATUS_URL` | crawler | 公开状态数据源 `https://newapi.zxdj.club/api/status` |
| `CRAWL_INTERVAL_SECONDS` | crawler | `1800`，采集轮次间隔（秒） |
| `REQUEST_DELAY_SECONDS` | crawler | `5`，价格和状态请求之间的等待时间（秒） |
| `DATA_DIR` | crawler | `/data`，采集文件目录 |
| `DATA_FILE` | api | `/data/pricing.json`，价格快照路径 |
| `DATABASE_URL` | api | `sqlite:////data/app.db`，SQLite 数据库文件；当前实现仅使用 SQLite |
| `VITE_API_URL` | web | `/api`，前端构建或开发时的 API 基地址 |

容器配置通过 `docker-compose.yml` 的对应服务 `environment` 显式传入。仅将 `.env.example` 复制为 `.env` 不会自动覆盖这些值；如使用 `.env`，需要在 Compose 中添加对应的 `${变量名}` 引用。`VITE_API_URL` 在 Vite 构建时读取，修改运行中 Web 容器的环境变量不会改变已生成的页面。

所有服务基础镜像使用 DaoCloud 国内镜像代理；外部价格同步仍取决于公开数据源网络可用性。首次采集成功前，模型列表可能为空。

## 接口

- `GET /api/health`：健康状态和模型数量。
- `GET /api/status`：系统信息、数据源、更新时间和版本。
- `GET /api/pricing`：模型价格，可用 `vendor`、`endpoint`、`group`、`q` 查询。
- `GET /api/history`：价格快照的变更历史。
- `GET /api/notice`：公告列表。
- `GET /api/rankings`：排行榜；无真实调用时为空并标记为预览。
- `POST /api/auth/register`、`POST /api/auth/login`：账户注册和登录；登录成功会写入 HttpOnly 会话 Cookie。
- `GET /api/auth/me`、`POST /api/auth/logout`：恢复当前会话和退出登录。
- `GET/POST /api/keys`、`POST /api/keys/{key_id}/revoke`、`DELETE /api/keys/{key_id}`：当前用户的访问密钥管理；原始密钥仅在创建响应返回一次。
- `GET /api/wallet`、`GET /api/wallet/transactions`、`POST /api/wallet/credit`、`GET /api/billing`：余额和账单流水。
- `GET/POST /api/usage-logs`：查询或记录当前用户的模型调用用量。
- `GET/POST /api/channels`、`PATCH/DELETE /api/channels/{channel_id}`：渠道配置管理。
- `GET/POST /api/routes`、`DELETE /api/routes/{route_id}`：模型路由管理。
- `POST /api/playground`：登录后按模型路由调用已配置的 OpenAI 兼容渠道，并将成功或失败记录写入用量日志；未配置路由时返回明确错误，不伪造模型响应。

注册要求密码至少 8 位；重复邮箱返回 409，错误密码返回 401。登录会话默认有效 7 天，前端刷新页面会自动恢复状态，顶部导航提供退出登录。前端会显示接口错误和网络连接失败提示。通过上述 Compose 同源部署使用完整登录流程；跨端口本地开发时，当前通用 CORS 配置不足以支持带 Cookie 的跨域认证，需要另行配置同源代理或凭据型 CORS。

公开接口调用示例（Bash 或其他提供原生 curl 的终端）：

```bash
curl http://localhost:18002/api/health
curl "http://localhost:18002/api/pricing?q=gpt"
```

登录后的业务接口使用会话 Cookie。Playground 需要先创建渠道并配置模型路由；创建访问密钥本身不会自动配置上游渠道。

## 页面

公开页面包含首页、`/models` 模型广场、`/models/:modelId` 模型详情、`/pricing`、`/rankings`、`/sign-in` 和 `/sign-up`。模型广场无需登录即可使用，支持搜索、分组倍率、供应商、协议标签、计费类型筛选、标准/充值价格模式、/1M 与 /1K 单位、名称/价格排序、网格/列表视图、重置和价格详情；卡片说明根据价格接口返回的协议数据生成。

登录后的 `/console`、`/dashboard`、`/api-keys`、`/channels`、`/billing`、`/playground`、`/profile`、`/wallet` 和 `/usage-logs` 使用业务接口：API 密钥可创建/撤销/删除，钱包显示余额和流水，用量日志支持模型筛选和 CSV 导出，渠道可新增/删除，Playground 可提交模型请求并展示响应，个人资料显示当前会话账户。

当前不宣称与参考站全功能一致。`/users`、`/system-settings`、`/forgot-password`、`/reset` 和 `/oauth` 为说明入口，尚未实现完整管理、密码重置或第三方登录流程；`/privacy-policy` 和 `/user-agreement` 为演示条款。钱包入账接口不等于真实支付集成；生产支付、OAuth、后台管理和正式条款仍需进一步实现及配置。

### 工单流转演示

访问 `/tickets` 打开独立的工单运营界面。页面包含工单状态与优先级筛选、搜索、处理队列、流转进度、人员指派和新建工单表单，侧栏和概览数字会随当前内存中的工单状态更新，队列表格支持键盘选择并提供移动端布局。侧栏或顶部工具栏的“界面设置”可以即时切换三档字号和森林绿、海岸蓝、暖棕色三种主题配色，选择会保存到浏览器本地存储并在下次打开 `/tickets` 时恢复。当前工单数据与状态变更保存在页面内存中，仅用于界面演示，不连接后端工单服务。主要实现文件为 `web/src/TicketFlowPage.tsx` 和 `web/src/ticket-flow.css`，路由入口位于 `web/src/main.tsx`。

## 本地运行与验证

容器镜像使用 Node.js 22 和 Python 3.12。直接本地开发时可使用相应版本，并为 Python 安装独立虚拟环境。下面是 PowerShell 示例，每个服务分别在新的终端从仓库根目录执行；本地数据写入被 Git 忽略的 `data/`。

前端（<http://localhost:5173>；完整登录验证请使用上面的同源部署）：

```powershell
Set-Location web
npm install
$env:VITE_API_URL = 'http://localhost:8000/api'
npm run dev
```

API（交互式接口文档：<http://localhost:8000/docs>）：

```powershell
Set-Location api
python -m pip install -r requirements.txt
$env:DATA_FILE = '../data/pricing.json'
$env:DATABASE_URL = 'sqlite:///../data/app.db'
python -m uvicorn app.main:app --reload
```

采集器：

```powershell
Set-Location crawler
python -m pip install -r requirements.txt
$env:DATA_DIR = '../data'
python main.py
```

在开发里程碑需要验证时，从仓库根目录执行：

```bash
npm --prefix web run build
python -m compileall -q api crawler
docker compose config
```

这些检查分别验证前端构建、Python 语法和 Compose 配置，不代表已完成上游调用、支付或完整业务验收。
