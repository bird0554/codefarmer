import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import httpx
from .database import (
    add_usage_log, authenticate_user, create_api_key, create_channel, create_route, create_session, create_user,
    credit_wallet, delete_api_key, delete_channel, delete_route, delete_session, ensure_wallet, get_session_user,
    init_db, list_api_keys, list_channels, list_notices, list_rankings, list_routes, list_transactions, list_usage_logs,
    resolve_route_channel,
    revoke_api_key, update_channel,
)

DATA_FILE = Path(os.getenv("DATA_FILE", "/data/pricing.json"))
SOURCE_URL = os.getenv("SOURCE_URL", "https://newapi.zxdj.club/api/pricing")

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CODEFARMER API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


def fallback() -> dict[str, Any]:
    return {"success": True, "source_url": SOURCE_URL, "fetched_at": None, "data": [], "vendors": [], "group_ratio": {}, "usable_group": {}}


def load_data() -> dict[str, Any]:
    if not DATA_FILE.exists():
        return fallback()
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback()


@app.get("/api/health")
def health() -> dict[str, Any]:
    payload = load_data()
    return {"status": "ok", "models": len(payload.get("data", [])), "fetched_at": payload.get("fetched_at")}


@app.get("/api/pricing")
def pricing(
    vendor: str | None = Query(default=None),
    endpoint: str | None = Query(default=None),
    group: str | None = Query(default=None),
    q: str | None = Query(default=None),
) -> dict[str, Any]:
    payload = load_data()
    rows = payload.get("data", [])
    vendors = {str(v.get("id")): v.get("name", "Unknown") for v in payload.get("vendors", [])}
    filtered = []
    for row in rows:
        if vendor and vendors.get(str(row.get("vendor_id")), "").lower() != vendor.lower():
            continue
        if endpoint and endpoint.lower() not in {str(x).lower() for x in row.get("supported_endpoint_types", [])}:
            continue
        if group and group not in row.get("enable_groups", []):
            continue
        if q and q.lower() not in str(row.get("model_name", "")).lower():
            continue
        filtered.append({**row, "vendor_name": vendors.get(str(row.get("vendor_id")), "Custom")})
    return {**payload, "data": filtered, "count": len(filtered)}


@app.get("/api/status")
def status() -> dict[str, Any]:
    payload = load_data()
    return {"system_name": "CODEFARMER", "source_url": payload.get("source_url", SOURCE_URL), "fetched_at": payload.get("fetched_at"), "version": payload.get("pricing_version") or "v1.0.0-rc.27", "models": len(payload.get("data", [])), "theme": "default", "header_nav_modules": {"home": True, "console": True, "pricing": True, "rankings": True, "docs": False, "about": False}, "login_methods": {"password": True, "register": True}}


@app.get("/api/notice")
def notice() -> dict[str, Any]:
    return {"success": True, "data": list_notices()}


@app.get("/api/rankings")
def rankings() -> dict[str, Any]:
    return {"success": True, "data": list_rankings(), "preview": True}


class AuthRequest(BaseModel):
    email: EmailStr
    password: str


class ApiKeyRequest(BaseModel):
    name: str = "默认密钥"
    expires_at: str | None = None


class UsageLogRequest(BaseModel):
    model_name: str
    prompt: str = ""
    api_key_id: int | None = None
    endpoint: str = "chat.completions"
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int | None = None
    cost: float = 0
    status: str = "success"
    latency_ms: int = 0


class WalletCreditRequest(BaseModel):
    amount: float
    description: str = "账户充值"
    reference: str | None = None


class ChannelRequest(BaseModel):
    name: str
    base_url: str
    api_key: str = ""
    model_mapping: dict[str, Any] = {}
    group_name: str = "default"
    weight: float = 1
    enabled: bool = True


class RouteRequest(BaseModel):
    model_name: str
    channel_id: int
    priority: int = 0
    weight: float = 1
    enabled: bool = True


def require_user(request: Request) -> dict[str, Any]:
    user = get_session_user(request.cookies.get("codefarmer_session"))
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return user


@app.post("/api/auth/register")
def register(payload: AuthRequest) -> dict[str, Any]:
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="密码至少需要 8 位")
    if not create_user(str(payload.email), payload.password):
        raise HTTPException(status_code=409, detail="邮箱已注册")
    return {"success": True, "message": "注册成功，请登录"}


@app.post("/api/auth/login")
def login(payload: AuthRequest, response: Response) -> dict[str, Any]:
    user = authenticate_user(str(payload.email), payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    import secrets
    from datetime import timedelta
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    create_session(user["id"], token, expires.isoformat())
    response.set_cookie("codefarmer_session", token, max_age=7 * 24 * 3600, httponly=True, samesite="lax", secure=False, path="/")
    return {"success": True, "message": "登录成功", "user": {"email": user["email"]}}


@app.get("/api/auth/me")
def current_user(request: Request) -> dict[str, Any]:
    user = get_session_user(request.cookies.get("codefarmer_session"))
    if not user:
        raise HTTPException(status_code=401, detail="未登录")
    return {"success": True, "user": user}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict[str, Any]:
    delete_session(request.cookies.get("codefarmer_session"))
    response.delete_cookie("codefarmer_session", path="/")
    return {"success": True, "message": "已退出登录"}


@app.get("/api/keys")
def api_keys(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return {"success": True, "data": list_api_keys(user["id"])}


@app.post("/api/keys")
def api_key_create(payload: ApiKeyRequest, request: Request) -> dict[str, Any]:
    user = require_user(request)
    metadata, raw = create_api_key(user["id"], payload.name, payload.expires_at)
    return {"success": True, "data": metadata, "key": raw, "message": "密钥只会在创建时显示一次"}


@app.post("/api/keys/{key_id}/revoke")
def api_key_revoke(key_id: int, request: Request) -> dict[str, Any]:
    if not revoke_api_key(require_user(request)["id"], key_id):
        raise HTTPException(status_code=404, detail="密钥不存在")
    return {"success": True, "message": "密钥已撤销"}


@app.delete("/api/keys/{key_id}")
def api_key_delete(key_id: int, request: Request) -> dict[str, Any]:
    if not delete_api_key(require_user(request)["id"], key_id):
        raise HTTPException(status_code=404, detail="密钥不存在")
    return {"success": True, "message": "密钥已删除"}


@app.get("/api/wallet")
def wallet(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return {"success": True, "data": ensure_wallet(user["id"])}


@app.get("/api/wallet/transactions")
def wallet_transactions(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    user = require_user(request)
    return {"success": True, "data": list_transactions(user["id"], limit)}


@app.post("/api/wallet/credit")
def wallet_credit(payload: WalletCreditRequest, request: Request) -> dict[str, Any]:
    user = require_user(request)
    if payload.amount <= 0:
        raise HTTPException(status_code=422, detail="充值金额必须大于 0")
    return {"success": True, "data": credit_wallet(user["id"], payload.amount, payload.description, reference=payload.reference)}


@app.get("/api/billing")
def billing(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    user = require_user(request)
    return {"success": True, "wallet": ensure_wallet(user["id"]), "transactions": list_transactions(user["id"], limit)}


@app.get("/api/usage-logs")
def usage_logs(request: Request, limit: int = Query(default=100, ge=1, le=500)) -> dict[str, Any]:
    user = require_user(request)
    return {"success": True, "data": list_usage_logs(user["id"], limit)}


@app.post("/api/usage-logs")
def usage_log_create(payload: UsageLogRequest, request: Request) -> dict[str, Any]:
    user = require_user(request)
    return {"success": True, "data": add_usage_log(user["id"], payload.model_dump())}


@app.get("/api/channels")
def channels(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return {"success": True, "data": list_channels(user["id"])}


@app.post("/api/channels")
def channel_create(payload: ChannelRequest, request: Request) -> dict[str, Any]:
    user = require_user(request)
    return {"success": True, "data": create_channel(user["id"], payload.model_dump())}


@app.patch("/api/channels/{channel_id}")
def channel_update(channel_id: int, payload: ChannelRequest, request: Request) -> dict[str, Any]:
    result = update_channel(require_user(request)["id"], channel_id, payload.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="渠道不存在")
    return {"success": True, "data": result}


@app.delete("/api/channels/{channel_id}")
def channel_delete(channel_id: int, request: Request) -> dict[str, Any]:
    if not delete_channel(require_user(request)["id"], channel_id):
        raise HTTPException(status_code=404, detail="渠道不存在")
    return {"success": True, "message": "渠道已删除"}


@app.get("/api/routes")
def routes(request: Request) -> dict[str, Any]:
    user = require_user(request)
    return {"success": True, "data": list_routes(user["id"])}


@app.post("/api/routes")
def route_create(payload: RouteRequest, request: Request) -> dict[str, Any]:
    result = create_route(require_user(request)["id"], payload.model_dump())
    if not result:
        raise HTTPException(status_code=404, detail="渠道不存在")
    return {"success": True, "data": result}


@app.delete("/api/routes/{route_id}")
def route_delete(route_id: int, request: Request) -> dict[str, Any]:
    if not delete_route(require_user(request)["id"], route_id):
        raise HTTPException(status_code=404, detail="路由不存在")
    return {"success": True, "message": "路由已删除"}


@app.post("/api/playground")
async def playground(payload: UsageLogRequest, request: Request) -> dict[str, Any]:
    user = require_user(request)
    channel = resolve_route_channel(user["id"], payload.model_name)
    if not channel:
        add_usage_log(user["id"], {**payload.model_dump(), "status": "no_route"})
        raise HTTPException(status_code=409, detail="该模型尚未配置启用渠道，请先在渠道管理中添加渠道和路由")
    model_name = channel.get("model_mapping", {}).get(payload.model_name, payload.model_name)
    base_url = str(channel["base_url"]).rstrip("/")
    endpoint = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"
    body = {"model": model_name, "messages": [{"role": "user", "content": payload.prompt}], "stream": False}
    headers = {"Content-Type": "application/json"}
    if channel.get("api_key"):
        headers["Authorization"] = f"Bearer {channel['api_key']}"
    started = datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            upstream = await client.post(endpoint, json=body, headers=headers)
        response_data = upstream.json()
    except (httpx.HTTPError, ValueError) as exc:
        add_usage_log(user["id"], {**payload.model_dump(), "status": "upstream_error"})
        raise HTTPException(status_code=502, detail=f"上游渠道请求失败：{exc.__class__.__name__}") from exc
    if upstream.status_code >= 400:
        add_usage_log(user["id"], {**payload.model_dump(), "status": "upstream_error"})
        detail = response_data.get("error", {}).get("message") if isinstance(response_data, dict) else None
        raise HTTPException(status_code=502, detail=detail or "上游渠道返回错误")
    usage_info = response_data.get("usage", {}) if isinstance(response_data, dict) else {}
    usage = add_usage_log(user["id"], {**payload.model_dump(), "prompt_tokens": usage_info.get("prompt_tokens", 0), "completion_tokens": usage_info.get("completion_tokens", 0), "total_tokens": usage_info.get("total_tokens", 0), "latency_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000)})
    return {"success": True, "model": payload.model_name, "response": response_data.get("choices", [{}])[0].get("message", {}).get("content", "") if isinstance(response_data, dict) else "", "choices": response_data.get("choices", []) if isinstance(response_data, dict) else [], "usage": usage, "upstream": response_data}


@app.get("/api/history")
def history() -> list[dict[str, Any]]:
    history_file = DATA_FILE.with_name("history.json")
    if not history_file.exists():
        return []
    try:
        return json.loads(history_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

