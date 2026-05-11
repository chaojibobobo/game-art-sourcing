"""微信 HTML → 飞书文档 Block 格式转换（保留颜色和对齐）"""

from __future__ import annotations

import re
from bs4 import BeautifulSoup, Tag, NavigableString


def html_to_blocks(html: str) -> tuple[list[dict], dict[int, str]]:
    """将微信文章的 HTML 正文转换为飞书 Block 列表。

    返回 (blocks, image_map):
        blocks: 飞书 Block 列表
        image_map: {block_index: image_src_url} 记录图片块对应的原始图片 URL
    """
    soup = BeautifulSoup(html, "html.parser")
    root = soup.find("div", id="js_content") or soup
    blocks = []
    image_map = {}
    for child in root.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                blocks.append(_text_block(_text_run(text)))
            continue
        if isinstance(child, Tag):
            _convert_element(child, blocks, image_map)
    return _filter_empty_blocks(blocks, image_map)


# ── 颜色映射 ──────────────────────────────────────────────

def _rgb_to_feishu_color(rgb: str) -> int | None:
    """将 CSS rgb() 颜色映射到飞书 FontColor 枚举值。

    飞书 FontColor: 1=粉红 2=橙 3=黄 4=绿 5=蓝 6=紫 7=灰
    """
    m = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", rgb)
    if not m:
        return None
    r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    # 蓝色系: rgb(0, 52, 198)
    if b > 150 and r < 80:
        return 5  # 蓝色
    # 灰色系: rgb(102-136, 102-136, 102-136)
    if abs(r - g) < 20 and abs(g - b) < 20 and r > 80 and r < 180:
        return 7  # 灰色
    # 深灰色: rgb(34-51, 34-51, 34-51)
    if abs(r - g) < 10 and abs(g - b) < 10 and r < 70:
        return None  # 近黑色，用默认
    return None


def _extract_color(style: str) -> int | None:
    """从 CSS style 中提取颜色，映射为飞书 FontColor"""
    m = re.search(r"(?:^|;)\s*color\s*:\s*(rgb\([^)]+\))", style, re.IGNORECASE)
    if m:
        return _rgb_to_feishu_color(m.group(1))
    return None


def _extract_align(style: str) -> int | None:
    """从 CSS style 中提取对齐方式，映射为飞书 Align: 1=左 2=中 3=右"""
    m = re.search(r"text-align\s*:\s*(\w+)", style, re.IGNORECASE)
    if m:
        val = m.group(1).lower()
        if val == "center":
            return 2
        elif val == "right":
            return 3
    return None


def _get_element_align(el: Tag) -> int | None:
    """获取元素及其祖先的 text-align（取最近一层）"""
    current = el
    for _ in range(3):  # 最多向上查 3 层
        if current and isinstance(current, Tag):
            style = current.get("style", "")
            align = _extract_align(style)
            if align:
                return align
            current = current.parent
        else:
            break
    return None


# ── Block 构造工具 ────────────────────────────────────────

def _extract_font_size(style: str) -> float | None:
    """从 CSS style 中提取 font-size，返回 px 等价值"""
    m = re.search(r"font-size\s*:\s*([\d.]+)\s*(px|pt|em|rem)", style, re.IGNORECASE)
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "px":
        return value
    if unit == "pt":
        return value * 1.33
    if unit in ("em", "rem"):
        return value * 16
    return value


def _detect_heading_level(el: Tag) -> int | None:
    """检测元素是否像微信文章中的视觉标题（加粗+大字号）。返回标题级别或 None。"""
    text = el.get_text(strip=True)
    if not text or len(text) > 80:
        return None
    if el.find(["div", "section", "p", "blockquote", "ul", "ol", "table", "pre"]):
        return None
    max_size = 0.0
    has_bold = False
    for node in [el] + el.find_all(["strong", "b", "span", "font"], recursive=True):
        style = node.get("style", "")
        size = _extract_font_size(style)
        if size and size > max_size:
            max_size = size
        if node.name in ("strong", "b"):
            has_bold = True
        if re.search(r"font-weight\s*:\s*(bold|[6-9]00)", style or ""):
            has_bold = True
    if max_size >= 20 and has_bold:
        return 2
    if max_size >= 18 and has_bold:
        return 3
    return None
def _text_block(*parts: dict, style: dict | None = None) -> dict:
    """构造一个飞书 Text Block (block_type=2)"""
    elements = list(parts) if parts else [{"text_run": {"content": "", "text_element_style": {}}}]
    return {"block_type": 2, "text": {"elements": elements, "style": style or {}}}


def _heading_block(level: int, elements: list[dict], align: int | None = None) -> dict:
    """构造标题 Block (block_type=3~5 对应 heading1~3)，elements 为 text_run 列表"""
    block_type = min(level, 9) + 2  # h1→3, h2→4, h3→5
    key = f"heading{min(level, 9)}"
    block = {
        "block_type": block_type,
        key: {
            "elements": elements
        },
    }
    if align:
        block[key]["style"] = {"align": align}
    return block


def _list_block(ordered: bool, text: str) -> dict:
    """构造列表项 Block (block_type=13 有序, 12 无序)"""
    block_type = 13 if ordered else 12
    key = "ordered" if ordered else "bullet"
    return {
        "block_type": block_type,
        key: {
            "elements": [
                {"text_run": {"content": text, "text_element_style": {}}}
            ]
        },
    }


def _quote_block(*parts: dict) -> dict:
    """构造引用 Block (block_type=15)"""
    return {
        "block_type": 15,
        "quote": {
            "elements": list(parts) if parts else [{"text_run": {"content": "", "text_element_style": {}}}]
        },
    }


def _code_block(code: str) -> dict:
    """构造代码 Block (block_type=14)"""
    return {
        "block_type": 14,
        "code": {
            "elements": [
                {"text_run": {"content": code, "text_element_style": {}}}
            ],
            "style": {},
        },
    }


def _image_block() -> dict:
    """构造图片 Block (block_type=27)，空 image 对象，后续由 feishu_client 上传并替换"""
    return {"block_type": 27, "image": {}}


def _is_empty_text_block(block: dict) -> bool:
    """检查 block 是否为空文本块"""
    if block.get("block_type") != 2:
        return False
    for el in block.get("text", {}).get("elements", []):
        content = el.get("text_run", {}).get("content", "")
        if content.strip():
            return False
    return True


def _filter_empty_blocks(blocks: list[dict], image_map: dict[int, str]) -> tuple[list[dict], dict[int, str]]:
    """移除空文本块并调整 image_map 索引"""
    new_blocks = []
    new_image_map = {}
    index_map = {}
    new_idx = 0
    for old_idx, block in enumerate(blocks):
        if _is_empty_text_block(block):
            continue
        index_map[old_idx] = new_idx
        new_blocks.append(block)
        new_idx += 1
    for old_idx, src in image_map.items():
        new_idx = index_map.get(old_idx)
        if new_idx is not None:
            new_image_map[new_idx] = src
    return new_blocks, new_image_map


def build_source_callout(title: str, url: str) -> dict:
    """构造文档开头的来源说明引用块（匹配飞书剪存格式）"""
    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S (UTC+8)")
    link_text = title or url
    return {
        "block_type": 15,
        "quote": {
            "elements": [
                {"text_run": {"content": "🔗 原文链接：", "text_element_style": {}}},
                {"text_run": {"content": link_text, "text_element_style": {"link": {"url": url}}}},
                {"text_run": {"content": f"\n🕐 剪存时间：{now}", "text_element_style": {}}},
                {"text_run": {"content": "\n✂️ 本文档由 ", "text_element_style": {}}},
                {"text_run": {"content": "波波严选", "text_element_style": {"text_color": 5}}},
                {"text_run": {"content": " 一键生成", "text_element_style": {}}},
            ],
        },
    }


def _text_run(content: str, bold: bool = False, italic: bool = False,
              underline: bool = False, strikethrough: bool = False,
              link: str | None = None, inline_code: bool = False,
              color: int | None = None) -> dict:
    """构造一个 text_run 元素"""
    style = {}
    if bold:
        style["bold"] = True
    if italic:
        style["italic"] = True
    if underline:
        style["underline"] = True
    if strikethrough:
        style["strikethrough"] = True
    if inline_code:
        style["inline_code"] = True
    if link:
        style["link"] = {"url": link}
    if color:
        style["text_color"] = color
    return {"text_run": {"content": content, "text_element_style": style}}


# ── 元素转换 ──────────────────────────────────────────────

_HEADING_TAGS = {"h1": 1, "h2": 2, "h3": 3, "h4": 4, "h5": 5, "h6": 6}
_LIST_CONTAINER_TAGS = {"ul", "ol"}


def _convert_element(el: Tag, blocks: list[dict], image_map: dict[int, str]) -> None:
    """递归转换一个 HTML 元素，追加到 blocks 列表"""
    tag = el.name
    el_style = el.get("style", "")

    # 跳过隐藏元素
    if "visibility: hidden" in el_style or "display: none" in el_style:
        # 但如果是 div/section 容器，可能只是容器隐藏，子元素可见
        if tag not in ("div", "section"):
            return

    # 标题
    if tag in _HEADING_TAGS:
        text = el.get_text(strip=True)
        if text:
            align = _extract_align(el_style)
            parts = _collect_text_runs(el)
            if not parts:
                parts = [_text_run(text)]
            blocks.append(_heading_block(_HEADING_TAGS[tag], parts, align=align))
        return

    # 图片
    if tag == "img":
        src = el.get("data-src") or el.get("src", "")
        if src and not src.startswith("data:"):
            idx = len(blocks)
            blocks.append(_image_block())
            image_map[idx] = src
        return

    # 代码块
    if tag == "pre":
        code = el.get_text()
        blocks.append(_code_block(code))
        return

    if tag == "code" and el.parent and el.parent.name != "pre":
        blocks.append(_text_block(_text_run(el.get_text(), inline_code=True)))
        return

    # 引用
    if tag == "blockquote":
        parts = _collect_text_runs(el)
        if parts:
            blocks.append(_quote_block(*parts))
        return

    # 无序 / 有序列表
    if tag in _LIST_CONTAINER_TAGS:
        ordered = tag == "ol"
        for li in el.find_all("li", recursive=False):
            text = li.get_text(strip=True)
            if text:
                blocks.append(_list_block(ordered, text))
        return

    # 表格：提取其中的图片和文本，按顺序输出（飞书不支持 table block）
    if tag == "table":
        for img in el.find_all("img"):
            src = img.get("data-src") or img.get("src", "")
            if src and not src.startswith("data:"):
                idx = len(blocks)
                blocks.append(_image_block())
                image_map[idx] = src
        for td in el.find_all("td"):
            text = td.get_text(strip=True)
            if text and not td.find("img"):
                blocks.append(_text_block(_text_run(text)))
        return

    # 块级容器（div, section, figure）：检测视觉标题，否则递归处理子元素
    if tag in ("div", "section", "figure"):
        heading = _detect_heading_level(el)
        if heading:
            parts = _collect_text_runs(el)
            if not parts:
                text = el.get_text(strip=True)
                if text:
                    parts = [_text_run(text)]
            if parts:
                align = _get_element_align(el)
                blocks.append(_heading_block(heading, parts, align=align))
            return
        for child in el.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    blocks.append(_text_block(_text_run(text)))
            elif isinstance(child, Tag):
                _convert_element(child, blocks, image_map)
        return

    # 段落、行内元素：检测视觉标题，否则收集文本（带颜色和对齐）
    if tag in ("p", "span", "strong", "em", "b", "i", "a"):
        if tag == "p":
            heading = _detect_heading_level(el)
            if heading:
                parts = _collect_text_runs(el)
                if not parts:
                    text = el.get_text(strip=True)
                    if text:
                        parts = [_text_run(text)]
                if parts:
                    align = _get_element_align(el)
                    blocks.append(_heading_block(heading, parts, align=align))
                return
        parts = _collect_text_runs(el)
        if parts:
            align = _get_element_align(el)
            blocks.append(_text_block(*parts, style={"align": align} if align else None))
            return
        # 如果没有直接文本，递归处理子元素
        for child in el.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    blocks.append(_text_block(_text_run(text)))
            elif isinstance(child, Tag):
                _convert_element(child, blocks, image_map)
        return

    # 默认：提取文本
    text = el.get_text(strip=True)
    if text:
        blocks.append(_text_block(_text_run(text)))


def _collect_text_runs(el: Tag, inherited_color: int | None = None,
                       inherited_bold: bool = False, inherited_italic: bool = False) -> list[dict]:
    """从元素中收集内联文本，保留粗体/斜体/链接/颜色等样式"""
    runs = []
    for child in el.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if text.strip():
                runs.append(_text_run(text.strip(), bold=inherited_bold,
                                      italic=inherited_italic, color=inherited_color))
        elif isinstance(child, Tag):
            name = child.name
            child_style = child.get("style", "")
            color = _extract_color(child_style) or inherited_color
            bold = inherited_bold
            italic = inherited_italic

            if name in ("strong", "b"):
                bold = True
            elif name in ("em", "i"):
                italic = True

            text = child.get_text(strip=True)
            if not text and name != "br":
                continue

            # 判断是否有需要递归的子元素
            inner_tags = [c for c in child.children if isinstance(c, Tag) and c.name not in ("br",)]

            if name == "a":
                href = child.get("href", "")
                if inner_tags:
                    runs.extend(_collect_text_runs(child, inherited_color=color,
                                                  inherited_bold=bold, inherited_italic=italic))
                else:
                    runs.append(_text_run(text, bold=bold, italic=italic,
                                          link=href if href else None, color=color))
            elif name == "code":
                runs.append(_text_run(text, inline_code=True, color=color))
            elif name == "br":
                runs.append(_text_run("\n"))
            elif name == "img":
                src = child.get("data-src") or child.get("src", "")
                if src and not src.startswith("data:"):
                    runs.append(_text_run("[图片]"))
            elif name in ("strong", "b", "em", "i", "span", "font"):
                # 这些标签可能是容器，需要递归处理子元素
                child_bold = bold or ("bold" in child_style or "font-weight" in child_style)
                child_italic = italic or ("italic" in child_style or "font-style" in child_style)
                if inner_tags:
                    runs.extend(_collect_text_runs(child, inherited_color=color,
                                                  inherited_bold=child_bold, inherited_italic=child_italic))
                else:
                    runs.append(_text_run(text, bold=child_bold, italic=child_italic, color=color))
            else:
                # 其他标签（div 等），递归处理
                if inner_tags:
                    runs.extend(_collect_text_runs(child, inherited_color=color,
                                                  inherited_bold=bold, inherited_italic=italic))
                else:
                    runs.append(_text_run(text, bold=bold, italic=italic, color=color))
    return runs
