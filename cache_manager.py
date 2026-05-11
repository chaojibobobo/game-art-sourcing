"""Search cache for game-art-sourcing.

Usage:
    python3 cache_manager.py read "My Time at Sandrock"
    python3 cache_manager.py write "My Time at Sandrock" /tmp/game-art-research.json
    python3 cache_manager.py list
    python3 cache_manager.py clear [--all | "Game Name"]
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
TTL_SECONDS = 7 * 24 * 3600  # 7 days


def _slug(name: str) -> str:
    raw = name.strip().lower().encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")[:120]


def _path(slug: str) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{slug}.json")


def read(name: str) -> dict | None:
    """Return cached data if it exists and is not expired, else None."""
    p = _path(_slug(name))
    if not os.path.exists(p):
        return None
    try:
        with open(p) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    cached_at = data.get("cached_at", 0)
    if time.time() - cached_at > TTL_SECONDS:
        return None
    return data


def write(name: str, data: dict) -> str:
    """Save data to cache. Returns the cache file path."""
    data["cached_at"] = time.time()
    data["game"] = name
    p = _path(_slug(name))
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return p


def list_caches() -> list[dict]:
    """List all cached entries with metadata."""
    if not os.path.isdir(CACHE_DIR):
        return []
    entries = []
    for fname in sorted(os.listdir(CACHE_DIR)):
        if not fname.endswith(".json"):
            continue
        p = os.path.join(CACHE_DIR, fname)
        try:
            with open(p) as f:
                data = json.load(f)
            age_hours = (time.time() - data.get("cached_at", 0)) / 3600
            entries.append({
                "game": data.get("game", fname),
                "age_hours": round(age_hours, 1),
                "expired": age_hours > TTL_SECONDS / 3600,
                "file": p,
            })
        except (json.JSONDecodeError, OSError):
            continue
    return entries


def clear(name: str | None = None) -> int:
    """Delete cache. If name is None, delete all. Returns count deleted."""
    if not os.path.isdir(CACHE_DIR):
        return 0
    if name:
        p = _path(_slug(name))
        if os.path.exists(p):
            os.remove(p)
            return 1
        return 0
    count = 0
    for fname in os.listdir(CACHE_DIR):
        if fname.endswith(".json"):
            os.remove(os.path.join(CACHE_DIR, fname))
            count += 1
    return count


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "read":
        if len(sys.argv) < 3:
            print("Usage: cache_manager.py read \"Game Name\"")
            sys.exit(1)
        data = read(sys.argv[2])
        if data:
            print(json.dumps(data, ensure_ascii=False))
        else:
            print("CACHE_MISS")

    elif cmd == "write":
        if len(sys.argv) < 4:
            print("Usage: cache_manager.py write \"Game Name\" data.json")
            sys.exit(1)
        name = sys.argv[2]
        src = sys.argv[3]
        if src == "-":
            data = json.load(sys.stdin)
        else:
            with open(src) as f:
                data = json.load(f)
        p = write(name, data)
        print(f"Cached: {p}")

    elif cmd == "list":
        entries = list_caches()
        if not entries:
            print("No cached entries.")
        for e in entries:
            status = "EXPIRED" if e["expired"] else f"{e['age_hours']}h ago"
            print(f"  {e['game']}  ({status})")

    elif cmd == "clear":
        if len(sys.argv) >= 3 and sys.argv[2] != "--all":
            count = clear(sys.argv[2])
        else:
            count = clear()
        print(f"Cleared {count} cache(s)")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
