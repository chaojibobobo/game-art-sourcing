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

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from feishu_client import FeishuClient  # noqa: E402
from block_builder import json_to_blocks  # noqa: E402
import requests  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("feishu-publish")

CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")
STATUS_FILE = "/tmp/game-art-publish-status.json"


def _write_status(stage: str, **kwargs):
    data = {"stage": stage, "ts": time.time(), **kwargs}
    with open(STATUS_FILE, "w") as f:
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

    _write_status("converting", input_file=args.input_file)

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
    _write_status("converted", blocks=len(blocks), images=len(image_map))

    # Create document
    cfg = load_config()
    client = FeishuClient(
        app_id=cfg["app_id"],
        app_secret=cfg["app_secret"],
        folder_token=cfg.get("folder_token", ""),
        user_open_id=cfg.get("user_open_id", ""),
        doc_domain=cfg.get("doc_domain", "open.feishu.cn"),
    )
    _write_status("creating_doc", title=title)
    doc_id = client.create_document(title)
    log.info("Created document: %s", doc_id)
    _write_status("doc_created", doc_id=doc_id)

    # Download images in parallel
    img_data_map = {}
    if image_map:
        _write_status("downloading_images", total=len(image_map))
        from concurrent.futures import ThreadPoolExecutor, as_completed
        downloaded = 0
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {
                pool.submit(requests.get, url, timeout=15): idx
                for idx, url in image_map.items()
            }
            for f in as_completed(futures):
                idx = futures[f]
                try:
                    resp = f.result()
                    resp.raise_for_status()
                    img_data_map[idx] = resp.content
                    downloaded += 1
                    log.info("Downloaded image [%d]: %d bytes", idx, len(resp.content))
                except Exception as e:
                    log.warning("Failed to download image [%s]: %s", image_map[idx], e)
        _write_status("images_downloaded", downloaded=downloaded)

    # Write blocks
    _write_status("writing_blocks", doc_id=doc_id)
    client.create_blocks(doc_id, blocks, img_data_map)

    url = client.get_document_url(doc_id)
    _write_status("done", url=url, doc_id=doc_id)
    print(url)


if __name__ == "__main__":
    main()
