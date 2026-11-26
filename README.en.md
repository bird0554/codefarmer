# CODEFARMER API Gateway

[简体中文](ReadMe.md) | [English](README.en.md)

An AI API gateway demo inspired by the public CODEFARMER / New API pages. It includes a React frontend, FastAPI, a persistent SQLite database, a scheduled pricing crawler, and Docker Compose deployment. The pages are independently implemented without copying the reference site's source code or protected assets.

## Repository scope

This repository publishes only the CodeFarmer gateway: `api/`, `web/`, `crawler/`, `nginx/`, Docker configuration, and project documentation. Other independent projects in the workspace, runtime databases, logs, dependencies, frontend build output, and local configuration are excluded through the root `.gitignore`. `.env.example` provides reference crawler settings; never commit real credentials. Keep the Chinese and English READMEs aligned when features or usage change.

## Directory structure

- `web/`: Vite + React frontend with the home page, model catalog and details, pricing, rankings, registration/login, console, API keys, channels, wallet, usage logs, Playground, and account data pages. `web/src/TicketFlowPage.tsx` and `web/src/ticket-flow.css` implement a separate ticket workflow demo.
- `api/`: FastAPI service for pricing, status, notices, rankings, authentication, user API keys, wallet transactions, usage logs, channels, and model routes. `api/app/database.py` persists backend business data in SQLite.
- `crawler/`: Fetches public pricing and status endpoints and stores snapshots and history.
- `nginx/`: SPA fallback and the `/api/` reverse proxy.
- `Dockerfile`, `docker-compose.yml`: Container image builds and deployment configuration.
- `.gitattributes`: Enforces LF line endings for shell scripts so Windows checkouts can run in Linux containers.
- `ReadMe.md`, `README.en.md`: Chinese and English usage guides; `IMPLEMENTATION_PLAN.md`: implementation plan.

## Start with Docker

Install Docker Engine / Docker Desktop and Docker Compose, then run from the repository root:

```bash
docker compose up -d --build
```

Open <http://localhost:18002>. The web container listens on port `8080` internally and publishes to `0.0.0.0:18002` on the host. Other devices on the same LAN can use the host's IP address and port `18002` if the host firewall permits it. Nginx forwards `/api/` to the API service and provides SPA fallback for frontend routes.

Pricing snapshots, history, and the SQLite database are stored in the `pricing_data` Docker volume; its actual name may include a Compose project prefix. The database path is `/data/app.db`. Normal container recreation preserves the named volume; `docker compose down -v` deletes that volume and its data.

### Configuration

| Variable | Service | Current default or purpose |
| --- | --- | --- |
| `SOURCE_URL` | crawler / api | Public pricing source, `https://newapi.zxdj.club/api/pricing`; the API uses it as source metadata |
| `STATUS_URL` | crawler | Public status source, `https://newapi.zxdj.club/api/status` |
| `CRAWL_INTERVAL_SECONDS` | crawler | `1800`, interval between collection cycles in seconds |
| `REQUEST_DELAY_SECONDS` | crawler | `5`, delay between pricing and status requests in seconds |
| `DATA_DIR` | crawler | `/data`, directory for collected files |
| `DATA_FILE` | api | `/data/pricing.json`, pricing snapshot path |
| `DATABASE_URL` | api | `sqlite:////data/app.db`, SQLite database file; the current implementation uses SQLite only |
| `VITE_API_URL` | web | `/api`, API base URL at frontend build or development time |

Container settings are passed explicitly through each service's `environment` section in `docker-compose.yml`. Copying `.env.example` to `.env` alone does not override those values; add matching `${VARIABLE_NAME}` references to Compose if you want to use `.env`. Vite reads `VITE_API_URL` at build time, so changing a running web container's environment does not change the generated frontend.

All service base images use the DaoCloud Docker mirror. Pricing synchronization also depends on access to the public data sources. The model list may be empty before the first successful collection.

## API

- `GET /api/health`: Health status and model count.
- `GET /api/status`: System information, data source, update time, and version.
- `GET /api/pricing`: Model pricing; supports `vendor`, `endpoint`, `group`, and `q` query parameters.
- `GET /api/history`: Pricing snapshot change history.
- `GET /api/notice`: Notices.
- `GET /api/rankings`: Rankings; empty and marked as a preview when there is no actual usage.
- `POST /api/auth/register`, `POST /api/auth/login`: Account registration and login; successful login sets an HttpOnly session cookie.
- `GET /api/auth/me`, `POST /api/auth/logout`: Restore the current session and sign out.
- `GET/POST /api/keys`, `POST /api/keys/{key_id}/revoke`, `DELETE /api/keys/{key_id}`: Manage the current user's API keys; the raw key is returned only once, on creation.
- `GET /api/wallet`, `GET /api/wallet/transactions`, `POST /api/wallet/credit`, `GET /api/billing`: Balance, credits, and billing transactions.
- `GET/POST /api/usage-logs`: Query or record the current user's model usage.
- `GET/POST /api/channels`, `PATCH/DELETE /api/channels/{channel_id}`: Manage upstream channels.
- `GET/POST /api/routes`, `DELETE /api/routes/{route_id}`: Manage model routes.
- `POST /api/playground`: Calls a configured OpenAI-compatible channel through a model route after login, recording successful and failed requests in usage logs. Missing routes produce an explicit error rather than a fabricated model response.

Passwords must be at least eight characters long. A duplicate email returns HTTP 409, and an incorrect password returns HTTP 401. Sessions last seven days by default. The frontend restores the session after a refresh, provides sign-out in the navigation, and displays API and connection errors. Use the same-origin Compose deployment above for the complete login flow. During local development across separate ports, the current generic CORS configuration does not support cross-origin cookie authentication; configure a same-origin proxy or credential-aware CORS separately.

Public API examples for Bash or another terminal with native curl:

```bash
curl http://localhost:18002/api/health
curl "http://localhost:18002/api/pricing?q=gpt"
```

Authenticated business endpoints use the session cookie. Playground requires a channel and a model route; creating an API key does not automatically configure an upstream channel.

## Pages and functionality

Public pages include the home page, `/models`, `/models/:modelId`, `/pricing`, `/rankings`, `/sign-in`, and `/sign-up`. The model catalog works without login and includes search, group ratios, provider/protocol/billing filters, standard and recharge pricing modes, /1M and /1K units, name/price sorting, grid/list views, reset, and price details. Card descriptions are derived from protocol data returned by the pricing API.

The authenticated `/console`, `/dashboard`, `/api-keys`, `/channels`, `/billing`, `/playground`, `/profile`, `/wallet`, and `/usage-logs` pages use business APIs. Users can create/revoke/delete API keys, view wallet balances and transactions, filter usage by model and export CSV, add/delete channels, submit Playground model requests and view responses, and view the current account profile.

The project does not claim complete feature parity with the reference site. `/users`, `/system-settings`, `/forgot-password`, `/reset`, and `/oauth` are informational entry pages, without complete administration, password reset, or third-party login workflows. `/privacy-policy` and `/user-agreement` contain demo terms. The wallet credit endpoint is not a real payment integration; production payments, OAuth, administration, and formal terms still require further implementation and configuration.

### Ticket workflow demo

Visit `/tickets` for a separate ticket operations interface. It includes status and priority filters, search, a work queue, workflow progress, assignments, and a new-ticket form. Sidebar and overview counts reflect the tickets currently held in memory. The queue supports keyboard selection and a mobile layout. Interface settings in the sidebar or top toolbar offer three font sizes and forest green, coastal blue, and warm brown themes; preferences are saved in browser local storage and restored on the next visit. Ticket data and state changes remain in page memory and are not connected to a backend ticket service. Main files: `web/src/TicketFlowPage.tsx`, `web/src/ticket-flow.css`; route entry: `web/src/main.tsx`.

## Local development and verification

The container images use Node.js 22 and Python 3.12. For direct local development, use corresponding versions and a separate Python virtual environment. The following PowerShell examples each start from the repository root in a separate terminal. Local runtime data is written to the Git-ignored `data/` directory.

Frontend (<http://localhost:5173>; use the same-origin deployment above for complete login verification):

```powershell
Set-Location web
npm install
$env:VITE_API_URL = 'http://localhost:8000/api'
npm run dev
```

API (interactive API documentation at <http://localhost:8000/docs>):

```powershell
Set-Location api
python -m pip install -r requirements.txt
$env:DATA_FILE = '../data/pricing.json'
$env:DATABASE_URL = 'sqlite:///../data/app.db'
python -m uvicorn app.main:app --reload
```

Crawler:

```powershell
Set-Location crawler
python -m pip install -r requirements.txt
$env:DATA_DIR = '../data'
python main.py
```

When verification is needed at a development milestone, run from the repository root:

```bash
npm --prefix web run build
python -m compileall -q api crawler
docker compose config
```

These checks cover the frontend build, Python syntax, and Compose configuration. They do not establish successful upstream calls, payment integration, or complete business acceptance.
