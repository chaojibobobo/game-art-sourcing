"""Publish a report to Feishu cloud document.

Supports two input formats:
  - JSON (.json): Direct block schema → no HTML parsing, no converter.py needed
  - HTML (.html): Legacy mode → uses converter.py from wechat2feishu

Usage:
    python publish_to_feishu.py report.json --title "标题"
    python publish_to_feishu.py report.html --title "标题"
"""
import sys
import os
import json
import argparse
import time
import yaml
import logging
import io

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from feishu_client import FeishuClient  # noqa: E402
from block_builder import json_to_blocks  # noqa: E402
import requests  # noqa: E402
from urllib.parse import urlparse  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("feishu-publish")

# Domains that require Referer/User-Agent to bypass hotlink protection
_HOTLINK_DOMAINS = {
    "artstation.com": "https://www.artstation.com",
    "cdnb.artstation.com": "https://www.artstation.com",
    "cdna.artstation.com": "https://www.artstation.com",
}
_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"


def _fix_steam_url(url: str) -> str:
    """Fix old-format Steam screenshot URLs to current CDN format.

    Old: /apps/{id}/ss_{hash}.jpg
    New: /apps/{id}/{hash}/ss_{hash}.1920x1080.jpg?t={now}
    """
    import re as _re
    m = _re.match(
        r"(https?://[^/]+/store_item_assets/steam/apps/\d+)/ss_([a-f0-9]+)\.jpg$",
        url,
    )
    if m:
        prefix, hash_val = m.group(1), m.group(2)
        fixed = f"{prefix}/{hash_val}/ss_{hash_val}.1920x1080.jpg?t={int(time.time())}"
        log.info("Steam URL fix: %s → %s", url, fixed)
        return fixed
    return url


def _download(url: str, timeout: int = 15) -> requests.Response:
    """Download with hotlink bypass and CDN fallback strategies."""
    url = _fix_steam_url(url)
    domain = urlparse(url).hostname or ""
    headers = {"User-Agent": _UA}
    for blocked, referer in _HOTLINK_DOMAINS.items():
        if domain == blocked or domain.endswith("." + blocked):
            headers["Referer"] = referer
            break

    resp = requests.get(url, timeout=timeout, headers=headers)
    if resp.status_code != 403 or "artstation" not in domain:
        return resp

    # ArtStation CDN 403 — try fallback strategies
    log.info("ArtStation CDN 403, trying fallbacks for %s", url)
    parsed = urlparse(url)
    path = parsed.path

    # Fallback 1: /covers/images/ path (proven accessible for og:image URLs)
    if "/images/images/" in path:
        alt = parsed._replace(path=path.replace("/images/images/", "/covers/images/"))
        log.info("  → covers path: %s", alt.geturl())
        r = requests.get(alt.geturl(), timeout=timeout, headers=headers)
        if r.ok:
            return r

    # Fallback 2: rotate CDN subdomain (cdna → cdnb → cdnc)
    for src, dst in [("cdna", "cdnb"), ("cdnb", "cdnc"), ("cdnc", "cdna")]:
        if (parsed.hostname or "").startswith(src + "."):
            alt = parsed._replace(netloc=parsed.hostname.replace(src, dst, 1))
            log.info("  → %s subdomain: %s", dst, alt.geturl())
            r = requests.get(alt.geturl(), timeout=timeout, headers=headers)
            if r.ok:
                return r
            break

    # Fallback 3: size downgrade (large → medium → small → 4k)
    size_fallbacks = ["/medium/", "/small/", "/4k/"]
    for size in size_fallbacks:
        if "/large/" in path:
            alt = parsed._replace(path=path.replace("/large/", size))
            log.info("  → %s size: %s", size.strip("/"), alt.geturl())
            r = requests.get(alt.geturl(), timeout=timeout, headers=headers)
            if r.ok:
                return r

    # Fallback 4: strip query parameters
    if parsed.query:
        alt = parsed._replace(query="")
        log.info("  → no query: %s", alt.geturl())
        r = requests.get(alt.geturl(), timeout=timeout, headers=headers)
        if r.ok:
            return r

    log.warning("All ArtStation fallbacks failed for %s", url)
    return resp


def _compress_image(data: bytes, max_width: int = 1200, quality: int = 85) -> tuple[bytes, int, int]:
    """Compress image: resize if wider than max_width, return (bytes, width, height)."""
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    w, h = img.size

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    if w > max_width:
        ratio = max_width / w
        img = img.resize((max_width, int(h * ratio)), Image.LANCZOS)
        w, h = img.size

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue(), w, h


CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")


def _get_status_file(input_file: str) -> str:
    """Derive status file path from input file to avoid concurrent collisions."""
    base = os.path.splitext(os.path.basename(input_file))[0]
    return f"/tmp/{base}-publish-status.json"


def _write_status(status_file: str, stage: str, **kwargs):
    data = {"stage": stage, "ts": time.time(), **kwargs}
    with open(status_file, "w") as f:
        json.dump(data, f, ensure_ascii=False)


def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: config.yaml not found at {CONFIG_PATH}")
        print("Copy config.example.yaml to config.yaml and fill in your Feishu credentials.")
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)["feishu"]


def load_html(input_file: str) -> tuple[list[dict], dict[int, str]]:
    """Legacy: parse HTML via converter.py."""
    W2F_DIR = os.path.expanduser("~/studio/tools/wechat2feishu")
    if W2F_DIR not in sys.path:
        sys.path.insert(0, W2F_DIR)
    from converter import html_to_blocks
    import re

    with open(input_file) as f:
        html = f.read()
    body_match = re.search(r"<body[^>]*>(.*)</body>", html, re.DOTALL | re.IGNORECASE)
    body_content = body_match.group(1) if body_match else html
    wrapped = f'<html><body><div id="js_content">{body_content}</div></body></html>'
    return html_to_blocks(wrapped)


def load_json(input_file: str) -> tuple[list[dict], dict[int, str]]:
    """Load JSON report and convert to blocks."""
    with open(input_file) as f:
        data = json.load(f)
    return json_to_blocks(data)


def main():
    parser = argparse.ArgumentParser(description="Publish report to Feishu doc")
    parser.add_argument("input_file", help="Report file (.json or .html)")
    parser.add_argument("--title", default=None, help="Document title")
    args = parser.parse_args()

    is_json = args.input_file.endswith(".json")
    status_file = _get_status_file(args.input_file)

    _write_status(status_file, "converting", input_file=args.input_file)

    # Load and convert
    if is_json:
        blocks, image_map = load_json(args.input_file)
        title = args.title
        if not title:
            with open(args.input_file) as f:
                data = json.load(f)
            title = data.get("title", "Game Art Research Report")
    else:
        blocks, image_map = load_html(args.input_file)
        title = args.title or "Game Art Research Report"

    log.info("Converted to %d blocks, %d images", len(blocks), len(image_map))
    _write_status(status_file, "converted", blocks=len(blocks), images=len(image_map))

    # Create document
    cfg = load_config()
    client = FeishuClient(
        app_id=cfg["app_id"],
        app_secret=cfg["app_secret"],
        folder_token=cfg.get("folder_token", ""),
        user_open_id=cfg.get("user_open_id", ""),
        doc_domain=cfg.get("doc_domain", "open.feishu.cn"),
    )
    _write_status(status_file, "creating_doc", title=title)
    doc_id = client.create_document(title)
    log.info("Created document: %s", doc_id)
    _write_status(status_file, "doc_created", doc_id=doc_id)

    # Download images in parallel
    img_data_map = {}
    img_size_map = {}  # {block_index: (width, height)}
    if image_map:
        _write_status(status_file, "downloading_images", total=len(image_map))
        from concurrent.futures import ThreadPoolExecutor, as_completed
        downloaded = 0
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {
                pool.submit(_download, url): idx
                for idx, url in image_map.items()
            }
            for f in as_completed(futures):
                idx = futures[f]
                try:
                    resp = f.result()
                    resp.raise_for_status()
                    raw = resp.content
                    try:
                        compressed, w, h = _compress_image(raw)
                        img_data_map[idx] = compressed
                        img_size_map[idx] = (w, h)
                        log.info("Downloaded+compressed [%d]: %d→%d bytes (%dx%d)",
                                 idx, len(raw), len(compressed), w, h)
                    except Exception as ce:
                        img_data_map[idx] = raw
                        log.info("Downloaded [%d]: %d bytes (compress skipped: %s)",
                                 idx, len(raw), ce)
                    downloaded += 1
                except Exception as e:
                    log.warning("Failed to download image [%s]: %s", image_map[idx], e)
        _write_status(status_file, "images_downloaded", downloaded=downloaded)

    # Patch image blocks with width/height from actual downloads
    for idx, (w, h) in img_size_map.items():
        if idx < len(blocks) and blocks[idx].get("block_type") == 27:
            blocks[idx]["image"]["width"] = w
            blocks[idx]["image"]["height"] = h

    # Write blocks
    _write_status(status_file, "writing_blocks", doc_id=doc_id)
    client.create_blocks(doc_id, blocks, img_data_map)

    url = client.get_document_url(doc_id)
    _write_status(status_file, "done", url=url, doc_id=doc_id)
    print(url)


if __name__ == "__main__":
    main()
