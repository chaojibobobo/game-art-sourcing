"""Publish an HTML report to Feishu cloud document.

Usage:
    python publish_to_feishu.py <html_file> [--title TITLE]

Reads HTML from file, creates a Feishu doc via Block API,
downloads images, uploads to Feishu, and prints the document URL.

Config: reads config.yaml from the project root (same dir as this script's parent).
"""

import sys
import os
import argparse
import yaml
import logging

# Project root is one level up from scripts/
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_DIR)

from feishu_client import FeishuClient  # noqa: E402
from converter import html_to_blocks  # noqa: E402
import requests  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("feishu-publish")

CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: config.yaml not found at {CONFIG_PATH}")
        print("Copy config.example.yaml to config.yaml and fill in your Feishu credentials.")
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)["feishu"]


def wrap_for_converter(html: str) -> str:
    """Wrap generic HTML in a js_content div so converter.py processes it."""
    import re
    body_match = re.search(r"<body[^>]*>(.*)</body>", html, re.DOTALL | re.IGNORECASE)
    body_content = body_match.group(1) if body_match else html
    return f'<html><body><div id="js_content">{body_content}</div></body></html>'


def main():
    parser = argparse.ArgumentParser(description="Publish HTML to Feishu doc")
    parser.add_argument("html_file", help="HTML file to publish")
    parser.add_argument("--title", default=None, help="Document title (default: from <title> tag)")
    args = parser.parse_args()

    with open(args.html_file) as f:
        html = f.read()

    title = args.title
    if not title:
        import re
        m = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
        title = m.group(1) if m else "Game Art Research Report"

    cfg = load_config()
    client = FeishuClient(
        app_id=cfg["app_id"],
        app_secret=cfg["app_secret"],
        folder_token=cfg.get("folder_token", ""),
        user_open_id=cfg.get("user_open_id", ""),
    )

    wrapped = wrap_for_converter(html)
    blocks, image_map = html_to_blocks(wrapped)
    log.info("Converted to %d blocks, %d images", len(blocks), len(image_map))

    doc_id = client.create_document(title)
    log.info("Created document: %s", doc_id)

    img_data_map = {}
    for idx, src_url in image_map.items():
        try:
            resp = requests.get(src_url, timeout=15)
            resp.raise_for_status()
            img_data_map[idx] = resp.content
            log.info("Downloaded image [%d]: %d bytes", idx, len(resp.content))
        except Exception as e:
            log.warning("Failed to download image [%s]: %s", src_url, e)

    client.create_blocks(doc_id, blocks, img_data_map)

    url = client.get_document_url(doc_id)
    print(url)


if __name__ == "__main__":
    main()
