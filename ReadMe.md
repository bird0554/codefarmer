# CODEFARMER API Gateway

参考 CODEFARMER / New API 公开页面构建的 AI API 网关演示站，包含 React 前端、FastAPI、SQLite 持久化数据库、定时价格采集器和 Docker Compose 部署。页面使用独立实现，不复制目标站源码或受保护资产。

## GitHub 发布边界

本仓库仅发布 CodeFarmer 网关的 `api/`、`web/`、`crawler/`、`nginx/`、Docker 配置和项目说明。根目录中的其他独立项目、运行数据库、日志、依赖目录、前端构建产物和本地配置均不属于本仓库；根级 `.gitignore` 会阻止这些内容被误加入版本控制。部署时请从 `.env.example` 创建本地 `.env`，不要提交真实凭据。

## 目录

- `web/`：Vite + React 前端，提供首页、模型广场、模型详情、价格、排行榜、登录/注册，以及登录后的控制台、API 密钥、渠道、钱包、用量日志、Playground 和个人资料数据页面；`web/src/TicketFlowPage.tsx` 与 `web/src/ticket-flow.css` 提供独立的工单流转演示界面。
- `api/`：FastAPI 服务，提供价格、状态、公告、排行榜、认证，以及登录用户的 API 密钥、钱包流水、用量日志、渠道和模型路由接口；`api/app/database.py` 使用 SQLite 持久化全部业务数据。
- `crawler/`：抓取公开价格与状态接口，保存快照和历史。
- `nginx/`：SPA 回退和 `/api/` 反向代理配置。
- `Dockerfile`、`docker-compose.yml`：生产部署配置。
- `.gitattributes`：固定 Shell 脚本使用 LF 换行，确保从 Windows 克隆后仍可在 Linux 容器中启动。

## 启动

```bash
docker compose up -d --build
```

打开 <http://localhost:18002>；Web 容器监听并发布到 `0.0.0.0:18002`，同一局域网内可通过部署主机 IP 的 `18002` 端口访问。价格快照、历史和 SQLite 数据库写入 Docker 卷 `pricing_data`，数据库默认为 `/data/app.db`，可用 `DATABASE_URL` 覆盖。

## 接口

- `GET /api/health`：健康状态和模型数量。
- `GET /api/status`：系统信息、数据源、更新时间和版本。
- `GET /api/pricing`：模型价格，可用 `vendor`、`endpoint`、`group`、`q` 查询。
- `GET /api/notice`：公告列表。
- `GET /api/rankings`：排行榜；无真实调用时为空并标记为预览。
- `POST /api/auth/register`、`POST /api/auth/login`：账户注册和登录；登录成功会写入 HttpOnly 会话 Cookie。
- `GET /api/auth/me`、`POST /api/auth/logout`：恢复当前会话和退出登录。
- `GET/POST /api/keys`、`POST /api/keys/{id}/revoke`、`DELETE /api/keys/{id}`：当前用户的访问密钥管理；原始密钥仅在创建响应返回一次。
- `GET /api/wallet`、`GET /api/wallet/transactions`、`POST /api/wallet/credit`、`GET /api/billing`：余额和账单流水。
- `GET/POST /api/usage-logs`：查询或记录当前用户的模型调用用量。
- `GET/POST/PATCH/DELETE /api/channels`：渠道配置管理；`GET/POST/DELETE /api/routes`：模型路由管理。
- `POST /api/playground`：登录后按模型路由调用已配置的 OpenAI 兼容渠道，并将成功或失败记录写入用量日志；未配置路由时返回明确错误，不伪造模型响应。
- `GET/POST /api/keys`、`POST /api/keys/{id}/revoke`、`DELETE /api/keys/{id}`：登录用户的 API 密钥创建、列表、撤销和删除。
- `GET /api/wallet`、`GET /api/wallet/transactions`：登录用户钱包余额和资金流水。
- `GET /api/usage-logs`：登录用户的调用用量、Token、延迟和成本明细。
- `GET/POST /api/channels`、`DELETE /api/channels/{id}`：登录用户的上游渠道配置。

注册和登录接口支持跨端口浏览器请求（CORS `GET`、`POST`、`OPTIONS`），注册要求密码至少 8 位；重复邮箱返回 409，错误密码返回 401。登录会话默认有效 7 天，前端刷新页面会自动恢复状态，顶部导航提供退出登录。前端会显示接口错误和网络连接失败提示。

## 页面

已覆盖首页、`/models` 模型广场、`/models/:modelId` 模型详情、`/pricing`、`/rankings`、`/sign-in`、`/sign-up`、`/console`、`/dashboard`、`/api-keys`、`/channels`、`/billing`、`/playground`、`/profile`、`/wallet`、`/usage-logs`、`/users`、`/system-settings`、`/forgot-password`、`/reset`、`/oauth`、`/privacy-policy`、`/user-agreement` 等路由。模型广场无需登录即可使用，支持搜索、分组倍率、供应商、协议标签、计费类型筛选、标准/充值价格模式、/1M 与 /1K 单位、名称/价格排序、网格/列表视图、重置和价格详情；卡片说明根据价格接口返回的协议数据生成。登录后的控制台模块使用真实接口：API 密钥可创建/撤销/删除，钱包显示余额和流水，用量日志支持模型筛选和 CSV 导出，渠道可新增/删除，Playground 可提交模型请求并展示响应，个人资料显示当前会话账户。充值支付、OAuth 和后台管理仍需部署方提供对应生产配置，不伪造第三方结果。

### 工单流转演示

访问 `/tickets` 打开独立的工单运营界面。页面包含工单状态与优先级筛选、搜索、处理队列、流转进度、人员指派和新建工单表单，侧栏和概览数字会随当前内存中的工单状态更新，队列表格支持键盘选择并提供移动端布局。侧栏或顶部工具栏的“界面设置”可以即时切换三档字号和森林绿、海岸蓝、暖棕色三种主题配色，选择会保存到浏览器本地存储并在下次打开 `/tickets` 时恢复。当前工单数据与状态变更保存在页面内存中，仅用于界面演示，不连接后端工单服务。主要实现文件为 `web/src/TicketFlowPage.tsx` 和 `web/src/ticket-flow.css`，路由入口位于 `web/src/main.tsx`。

## 本地运行与验证

```bash
cd web && npm install && npm run dev
cd api && pip install -r requirements.txt && uvicorn app.main:app --reload
cd crawler && pip install -r requirements.txt && python main.py
```

里程碑检查：

```bash
cd web && npm run build
python -m compileall -q api crawler
docker compose config
```

所有服务基础镜像使用 DaoCloud 国内镜像代理；外部价格同步仍取决于公开数据源网络可用性。
