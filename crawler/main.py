import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

SOURCE = os.getenv("SOURCE_URL", "https://newapi.zxdj.club/api/pricing")
STATUS_SOURCE = os.getenv("STATUS_URL", "https://newapi.zxdj.club/api/status")
DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
INTERVAL = int(os.getenv("CRAWL_INTERVAL_SECONDS", "1800"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY_SECONDS", "5"))


def fetch(url: str) -> dict:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with httpx.Client(timeout=20, headers={"User-Agent": "pricing-catalog-crawler/1.0 (+public-data-only)"}) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed to fetch {url}") from last_error


def atomic_write(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def sync_once() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = fetch(SOURCE)
    time.sleep(REQUEST_DELAY)
    try:
        status = fetch(STATUS_SOURCE)
    except Exception:
        status = {}
    now = datetime.now(timezone.utc).isoformat()
    stable_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    payload["source_url"] = SOURCE
    payload["fetched_at"] = now
    payload["status_snapshot"] = status.get("data", {})
    payload["snapshot_hash"] = stable_hash
    output = DATA_DIR / "pricing.json"
    old = output.read_text(encoding="utf-8") if output.exists() else ""
    if old:
        history_file = DATA_DIR / "history.json"
        try:
            history = json.loads(history_file.read_text(encoding="utf-8")) if history_file.exists() else []
        except json.JSONDecodeError:
            history = []
        previous = json.loads(old)
        if previous.get("snapshot_hash") != payload["snapshot_hash"]:
            history.insert(0, {"fetched_at": previous.get("fetched_at"), "pricing_version": previous.get("pricing_version"), "snapshot_hash": previous.get("snapshot_hash")})
            atomic_write(history_file, history[:100])
            snapshots = DATA_DIR / "snapshots"
            snapshots.mkdir(exist_ok=True)
            atomic_write(snapshots / f"pricing-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json", payload)
    atomic_write(output, payload)
    print(f"synced {len(payload.get('data', []))} models at {now}", flush=True)


if __name__ == "__main__":
    while True:
        try:
            sync_once()
        except Exception as exc:
            print(f"sync failed: {exc}", flush=True)
        time.sleep(max(INTERVAL, 300))
