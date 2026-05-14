---
name: game-art-sourcing
description: Deep research skill for game art assets. Use whenever the user mentions a game name and wants to study its art style, find reference assets, locate press kits, sprites, 3D models, or UI resources. Triggers on phrases like "调研", "美术参考", "素材", "press kit", "sprite sheet", "art style analysis", or any request to break down a game's visual design. Also use when the user wants a structured art research report for Feishu docs.
---

# Game Art Intelligence Sourcing

You are a senior game art asset researcher. Given a game name (or clues), produce a structured research report covering visual identity, art style breakdown, and actionable asset links.

## 最高指令：全自动执行 + 实时进度 (Zero-Interruption & Progress Visibility)

用户发起任务时已预先授予所有系统操作与网络请求权限。整个检索、脚本执行和发布过程中严格遵守：

1. **绝对禁止请示**：全程禁止打断流程询问用户（如"是否允许运行此命令"、"是否要继续"等）
2. **默认授权**：执行 curl 抓取、Python 运行 publish_to_feishu.py、读写 /tmp/ 临时文件时，自动应用默认授权，直接静默执行
3. **自动容错**：遇到非致命网络报错（单张图片 URL 404/403），自行跳过该链接并寻找替代，不向用户抛出错误或停下来请示
4. **实时进度**：主代理在每个步骤开始和完成时，输出一行简短进度。格式：`[Step N/M] 正在... → 完成描述`
5. **最终输出**：终端最终输出一个成功的飞书云文档 URL

进度输出示例（主代理在执行每个步骤时打印）：
```
[1/6] 正在检查缓存...
[1/6] 缓存未命中，开始调研
[2/6] 正在搜索 Steam 商店页面...
[2/6] 找到 AppID 1084600，收集商店截图 5 张
[3/6] 正在搜索 Bilibili 视频...
[3/6] 找到 4 个相关视频
[4/6] 正在搜索美术参考资源（ArtStation/Wiki/Press Kit）...
[4/6] 收集到 12 张参考图、6 个资产链接
[5/6] 正在生成 JSON 报告...
[5/6] 报告生成完毕：45 blocks, 6 images
[6/6] 正在发布到飞书...
[6/6] https://xxx.feishu.cn/docx/xxx
```

## Workflow

**IMPORTANT**: Steps 0-3 are executed by the MAIN AGENT with progress output. Step 4 delegates JSON generation to a sub-agent. Step 5 runs the publish script in the main conversation.

### Pre-Step: Generate Slug — 主代理

Before starting any step, generate a filesystem-safe slug from the game name. This slug isolates all temp files per game, preventing collisions when running multiple games concurrently.

```bash
SLUG=$(python3 -c "import base64;print(base64.urlsafe_b64encode('{Game Name}'.strip().lower().encode()).decode().rstrip('=')[:80])")
echo "Slug: $SLUG"
```

Example: "Hi-Fi RUSH" → `aGktZmkgcnVzaA`, "沙石镇时光" → `5rKZ55-z6ZWH5pe25YWJ`, "Overwatch 2" → `b3zlcndhddsayw`

All subsequent temp files use this slug:
- Report JSON: `/tmp/game-art-${SLUG}-report.json`
- Progress JSON: `/tmp/game-art-${SLUG}-gen-progress.json`
- Publish status: `/tmp/game-art-${SLUG}-publish-status.json`
- Research data: `/tmp/game-art-${SLUG}-research-data.json`

### Step 0: Cache Check — 主代理

Output: `[1/6] 正在检查缓存...`

```bash
python3 ~/.claude/skills/game-art-sourcing/cache_manager.py read "Game Name"
```

- If cache hit: output `[1/6] 缓存命中，跳过调研` → skip to Step 4
- If cache miss: output `[1/6] 缓存未命中，开始调研` → continue to Step 1

### Step 1: Game Profile — 主代理 (WebSearch)

Output: `[2/6] 正在搜索 Steam 商店页面...`

Search the game on Steam / official sources. Collect:

- **Basic info**: Developer, release year, art style tags
- **Store page URLs**: Steam, App Store, Google Play
- **Store page images**: 3-5 screenshots from Steam CDN + header image
- **Steam Tags**: Top 10, **全部中文翻译**
- **Visual summary**: 2-3 sentence art direction description

Output when done: `[2/6] 找到 AppID xxx，收集商店截图 N 张`

### Step 2: Game Videos — 主代理 (WebSearch)

Output: `[3/6] 正在搜索 Bilibili 视频...`

Search: `site:bilibili.com {game name} 游戏介绍` or `site:bilibili.com {game name} review`

Collect 3-5 videos: title + URL (`https://www.bilibili.com/video/BVxxxxxxx`)

Output when done: `[3/6] 找到 N 个相关视频`

### Step 3: Art Breakdown + Asset Sourcing — 主代理 (WebSearch)

Output: `[4/6] 正在搜索美术参考资源...`

Search ArtStation, Fandom Wiki, Sketchfab, Press Kit for:
- Character concept art, environment screenshots, UI screenshots
- Asset links with descriptions
- Color palette data

See detailed criteria in sections below (Characters, Environments, UI/UX, Asset Sourcing).

Output when done: `[4/6] 收集到 N 张参考图、M 个资产链接`

Save all research data to cache:
```bash
python3 ~/.claude/skills/game-art-sourcing/cache_manager.py write "Game Name" /tmp/game-art-${SLUG}-research-data.json
```

### Step 4: Generate JSON Report — Background Sub-Agent + Progress Monitor

Output: `[5/6] 正在生成 JSON 报告...`

This step runs the sub-agent **in the background** and monitors progress in real-time.

**Sub-agent execution**: Use the Agent tool with `run_in_background: true`. Pass ALL collected data to the sub-agent.

**Sub-agent prompt template**:

```
You are generating a game art research report as JSON. DO NOT publish — just generate the JSON file.

Game: {game name}
Slug: {SLUG}
Data source: {cache hit → "cached (skip WebSearch)" | cache miss → "fresh WebSearch"}
Research data:
- Game profile: {basic info, store URLs, tags, screenshots}
- Art breakdown: {characters, environments, UI analysis}
- Asset links: {all sourced links with descriptions}
- Videos: {list of Bilibili videos with title and URL}
- Color palette: {extracted hex values with roles}

OUTPUT FORMAT: JSON (NOT HTML). Use the block_builder JSON schema below.

JSON block types:
- {"type": "heading", "level": 2, "elements": [{"text": "🎮 游戏画像"}]}
- {"type": "text", "elements": [{"text": "维度", "bold": true}, {"text": " | 内容"}]}
- {"type": "image", "url": "https://...", "caption": "图注（必须含视觉特征分析）", "width": 800, "height": 450}
- {"type": "bullet", "elements": [{"text": "关键词", "bold": true}, {"text": "：描述"}]}
- {"type": "ordered", "elements": [{"text": "..."}]}
- {"type": "quote", "elements": [{"text": "内容"}]}
- {"type": "code", "text": "code content here"}
- {"type": "gallery", "urls": ["url1", "url2", "url3"], "width": 600}   ← 无图注的图片序列（用于商店截图画廊），gallery 统一用较小的 width

Element (text run) properties:
- text (required): string
- bold, italic, underline, strikethrough: boolean
- link: URL string
- inline_code: boolean
- color: int (1=pink 2=orange 3=yellow 4=green 5=blue 6=purple 7=gray)

IMPORTANT rules:
1. Steam Tags → **全部中文翻译** using industry terms, use inline_code
2. All links → use {"text": "描述", "link": "URL"} in elements
3. Resource links → MUST be search direct links with keywords, never bare homepage URLs
4. Use Emoji in headings: 🎮🎨🔗👤🏗️🖥️📦🔍📋
5. Add chapter summary {"type": "quote"} at start of each major section
6. Color palette → {"type": "quote"} with Emoji color blocks + inline_code hex values
7. AI prompts → {"type": "code", "text": "..."} with complete English prompts
8. **Image dedup** → maintain a used-URL set. Each URL at most once in entire report
9. **扩展视觉素材集 dedup** → only images NOT used in 美术风格拆解. If none, output a text block: "未检索到更多不重复的高质量素材"
10. **Asset links** → complete absolute URLs, never truncated
11. **Autonomous execution** → never ask for confirmation. Skip 404/403 silently.

**PROGRESS TRACKING** — You MUST write progress after completing each section:
```bash
echo '{"section":"游戏画像","done":1,"total":7}' > /tmp/game-art-{SLUG}-gen-progress.json
```
Sections to track (in order):
1. 游戏画像
2. 游戏视频
3. 美术风格拆解 - 角色
4. 美术风格拆解 - 场景
5. 美术风格拆解 - UI
6. 资产链接 + 扩展视觉素材集
7. AI Prompt + 离线资产汇总

Report sections (in order):
- heading 2: 🎮 游戏画像 — profile info (text blocks) + 1 cover image + gallery block with all store screenshots + Chinese translated tags
- heading 2: 📺 游戏视频 — 3-5 Bilibili video links as bullet blocks with link elements. Example:
  ```json
  {"type": "heading", "level": 2, "elements": [{"text": "📺 游戏视频"}]},
  {"type": "quote", "elements": [{"text": "Bilibili 精选视频 — 点击观看游戏实机演示与评测"}]},
  {"type": "bullet", "elements": [{"text": "【官方预告】游戏名 — 官方中文预告片", "link": "https://www.bilibili.com/video/BVxxxxxxx"}]},
  {"type": "bullet", "elements": [{"text": "【评测】游戏名 全面评测 — 画面/玩法/美术风格", "link": "https://www.bilibili.com/video/BVyyyyyyy"}]},
  {"type": "bullet", "elements": [{"text": "【实机演示】游戏名 前 30 分钟实机通关", "link": "https://www.bilibili.com/video/BVzzzzzzz"}]}
  ```
  - Each bullet: video title as link text, full Bilibili URL as link
  - Prioritize: official trailers, high-quality reviews, art-style breakdowns
  - If no Bilibili results found, output: {"type": "text", "elements": [{"text": "未检索到 Bilibili 相关视频"}]}
- heading 2: 🎨 美术风格拆解 — HIGH-DENSITY images interleaved with analysis. Maintain used-URL set.
  - heading 3: 👤 角色 — one bullet → 1-3 images → repeat for each aspect
  - heading 3: 🏗️ 场景 — same pattern. End with color palette quote block.
  - heading 3: 🖥️ UI / UX — same pattern
- heading 2: 🔗 资产链接 — bullet blocks with link elements
- heading 2: 🎨 扩展视觉素材集 — only unused images. If none, text: "未检索到更多不重复的高质量素材"
- heading 2: 🎨 AI 生成参考 Prompt — code blocks with English prompts
- heading 2: 📋 离线资产路径汇总 — text blocks with pipe-delimited lines + link elements

Steps:
1. Clear progress: `echo '{"section":"starting","done":0,"total":7}' > /tmp/game-art-{SLUG}-gen-progress.json`
2. Generate the full JSON report, writing progress after EACH section
3. Write the final JSON to /tmp/game-art-{SLUG}-report.json
4. Return ONLY: "JSON report written to /tmp/game-art-{SLUG}-report.json with N blocks and M images"

CRITICAL: Output valid JSON. Validate brackets and commas before writing.
Do NOT output raw JSON to stdout. Save to file, return the summary line only.
```

**Progress monitor**: While the sub-agent runs in background, run this bash monitoring loop in the main conversation:

```bash
echo '{"section":"starting","done":0,"total":7}' > /tmp/game-art-${SLUG}-gen-progress.json
```

(Spawn the background sub-agent, then immediately run:)

```bash
LAST_SEC=""; LAST_DONE=0; ELAPSED=0; START=$(date +%s)
while [ ! -s /tmp/game-art-${SLUG}-report.json ]; do
  PROG=$(cat /tmp/game-art-${SLUG}-gen-progress.json 2>/dev/null || echo '{}')
  SEC=$(echo "$PROG" | python3 -c "import sys,json; print(json.load(sys.stdin).get('section',''))" 2>/dev/null)
  DONE=$(echo "$PROG" | python3 -c "import sys,json; print(json.load(sys.stdin).get('done',0))" 2>/dev/null)
  NOW=$(date +%s); ELAPSED=$(( NOW - START ))
  if [ "$SEC" != "$LAST_SEC" ] || [ "$DONE" != "$LAST_DONE" ]; then
    echo "  → [$DONE/7] $SEC ... ($((ELAPSED))s)"
    LAST_SEC="$SEC"; LAST_DONE="$DONE"
  fi
  if [ $ELAPSED -gt 300 ] && [ $((ELAPSED % 60)) -eq 0 ]; then
    echo "  ⚠️ 已运行 $((ELAPSED/60)) 分钟，仍在生成 $SEC ..."
  fi
  sleep 8
done
echo "  → 报告生成完毕 (总耗时 $((ELAPSED))s)"
```

This loop outputs real-time progress to the user. If generation takes over 5 minutes, it prints a warning every 60 seconds.

After the loop exits, read the sub-agent result and output: `[5/6] 报告生成完毕：N blocks, M images`

### Step 5: Publish to Feishu — 主代理

Output: `[6/6] 正在发布到飞书...`

Run the publish script directly in the main conversation:

```bash
python3 ~/.claude/skills/game-art-sourcing/scripts/publish_to_feishu.py /tmp/game-art-${SLUG}-report.json --title "{Game Name} — 美术调研报告"
```

The publish script outputs progress to the terminal, so the user sees real-time status.

After publish completes, output: `[6/6] https://xxx.feishu.cn/docx/xxx`

### Sub-Agent Failure Recovery

If the sub-agent fails, crashes, or hangs:

1. Check if JSON was generated: `ls -la /tmp/game-art-${SLUG}-report.json`
2. If JSON exists: the sub-agent completed generation before crashing. Run the publish script directly in the main conversation:
   ```bash
   python3 ~/.claude/skills/game-art-sourcing/scripts/publish_to_feishu.py /tmp/game-art-${SLUG}-report.json --title "{Game Name} — 美术调研报告"
   ```
3. If JSON doesn't exist: the sub-agent failed during generation. Re-run the entire sub-agent.
4. Check publish status: `cat /tmp/game-art-${SLUG}-publish-status.json` — shows which stage the publish reached

## Report Structure

The report is generated as JSON using the `block_builder` schema. No HTML, no converter.py needed.

### JSON Block Types

| Block Type | Feishu block_type | Description |
|---|---|---|
| `heading` + level 2-9 | 4-11 | Section headings |
| `text` + elements | 2 | Paragraph with styled runs |
| `image` + url + caption | 27 + 15 | Image with optional caption quote. Supports `width`, `height`, `align` |
| `gallery` + urls | 27 × N | Multiple images without captions. Supports `width`, `height` |
| `bullet` + elements | 12 | Unordered list item |
| `ordered` + elements | 13 | Ordered list item |
| `quote` + elements | 15 | Blockquote |
| `code` + text | 14 | Code block |

### Element (Text Run) Properties

```json
{"text": "content", "bold": true, "italic": false, "link": "https://...", "inline_code": false, "color": 5}
```

Color values: 1=pink 2=orange 3=yellow 4=green 5=blue 6=purple 7=gray

### Section Layout

- **heading 2: 游戏画像** — Example JSON:
  ```json
  {"type": "heading", "level": 2, "elements": [{"text": "🎮 游戏画像"}]},
  {"type": "quote", "elements": [{"text": "沙石镇时光美术风格调研报告"}]},
  {"type": "text", "elements": [{"text": "开发商", "bold": true}, {"text": " | Pathea Games（中国重庆）"}]},
  {"type": "text", "elements": [{"text": "美术风格", "bold": true}, {"text": " | 风格化半卡通 3D"}]},
  {"type": "text", "elements": [{"text": "Steam", "bold": true}, {"text": " | "}, {"text": "商店页面", "link": "https://store.steampowered.com/app/xxx"}]},
  {"type": "image", "url": "https://...header.jpg", "caption": "Steam 封面 — 沙漠小镇全景"},
  {"type": "text", "elements": [{"text": "Steam Tags", "bold": true}]},
  {"type": "text", "elements": [{"text": "角色扮演 · 生活模拟 · 休闲 · 模拟 · 冒险 · 建造 · 沙盒 · 农场模拟 · 制作 · 单人", "inline_code": true}]},
  {"type": "gallery", "urls": ["https://...ss_01.jpg", "https://...ss_02.jpg", "https://...ss_03.jpg", "..."]}
  ```
  - Tags **必须全部中文翻译**，使用 `inline_code`
  - Gallery 集中所有商店截图，无需图注，节省空间
  - Gallery 图片计入全局去重

- **heading 2: 美术风格拆解** — bullet → image 交替，禁止集中堆砌
  ```json
  {"type": "heading", "level": 3, "elements": [{"text": "👤 角色"}]},
  {"type": "bullet", "elements": [{"text": "比例", "bold": true}, {"text": "：半 Q 版，头身比 1:4，圆润面部"}]},
  {"type": "image", "url": "https://...concept.png", "caption": "Fang 概念设定 — 深蓝 #2C3E6B 主色，长外套+口罩高辨识度剪影"},
  {"type": "bullet", "elements": [{"text": "设计语言", "bold": true}, {"text": "：每个 NPC 一个标志色"}]},
  {"type": "image", "url": "https://...concept2.png", "caption": "Amirah 概念设定 — 紫色 #8E44AD 标志色，柔和圆润剪影"}
  ```
  - **场景小节末尾**必须加色板 quote：
  ```json
  {"type": "quote", "elements": [
    {"text": "🎨 色板\n", "bold": true},
    {"text": "主色", "bold": true}, {"text": "：🟨 "}, {"text": "#D4A745", "inline_code": true}, {"text": " (沙漠黄) · 🟧 "}, {"text": "#CC7351", "inline_code": true}, {"text": " (陶瓦红)\n"},
    {"text": "辅色", "bold": true}, {"text": "：🟤 "}, {"text": "#8B4513", "inline_code": true}, {"text": " (台地棕) · 🩵 "}, {"text": "#87CEEB", "inline_code": true}, {"text": " (尘蓝天)\n"},
    {"text": "点缀", "bold": true}, {"text": "：🟢 "}, {"text": "#4A7023", "inline_code": true}, {"text": " (仙人掌绿) · 🟠 "}, {"text": "#FF8C00", "inline_code": true}, {"text": " (落日橙)"}
  ]}
  ```

- **heading 2: 资产链接** — bullet blocks with link elements
  ```json
  {"type": "heading", "level": 2, "elements": [{"text": "🔗 资产链接"}]},
  {"type": "text", "elements": [{"text": "📦 官方资源", "bold": true}]},
  {"type": "bullet", "elements": [{"text": "Steam 商店页", "link": "https://store.steampowered.com/app/xxx"}]},
  {"type": "bullet", "elements": [{"text": "数字设定集 DLC", "link": "https://store.steampowered.com/app/yyy"}]},
  {"type": "text", "elements": [{"text": "🔍 社区资源", "bold": true}]},
  {"type": "bullet", "elements": [{"text": "ArtStation 搜索", "link": "https://www.artstation.com/search?q=game+name"}]},
  {"type": "text", "elements": [{"text": "搜索语法备忘", "bold": true}]},
  {"type": "code", "text": "\"Game Name\" concept art high resolution\n\"Game Name\" texture rip site:reddit.com"}
  ```
  - 资源链接必须带搜索关键词直链，禁止裸域名

- **heading 2: 扩展视觉素材集** — 仅放正文未用过的图片。无新图则输出文本提示
- **heading 2: AI 生成参考 Prompt** — code blocks with English prompts
- **heading 2: 离线资产路径汇总** — text blocks with pipe-delimited lines + link elements
  ```json
  {"type": "text", "elements": [{"text": "资产名称", "bold": true}, {"text": " | "}, {"text": "类型", "bold": true}, {"text": " | "}, {"text": "来源", "bold": true}, {"text": " | "}, {"text": "链接", "bold": true}, {"text": " | "}, {"text": "备注", "bold": true}]},
  {"type": "text", "elements": [{"text": "Steam Header"}, {"text": " | "}, {"text": "封面"}, {"text": " | "}, {"text": "Steam CDN"}, {"text": " | "}, {"text": "点击查看", "link": "https://...header.jpg"}, {"text": " | "}]}
  ```

### 高密度图文排版规范 (High-Density Visual-Text Rules)

**这是最高优先级的排版规则，违反即为不合格报告。**

1. **解除图片数量上限，精准锚定**：在美术风格拆解的各个子版块中，取消图片数量上限。只要是高质量的说明性图片，尽可能多地插入。必须确保图片紧贴对应的文字特征分析：
   - 分析"体型比例" → 紧跟角色全身图（可放 2-3 张不同角色的对比）
   - 分析"色彩方案" → 紧跟角色色彩对比图
   - 分析"光照模型" → 紧跟 2-3 张不同光照条件的场景图
   - 分析"UI 交互" → 紧跟 3-5 张不同 UI 界面截图
   - 每个分析要点（bullet point）最多 2 段后必须跟至少 1 张相关图片
   - 同一个要点可以跟多张图展示不同变体/角度
   - **图片去重**：同一张图片 URL 在整篇报告中只能出现一次。如果某个分析点想引用已用在其他章节的图片，换一张不同但相关的图片。游戏画像的封面图也计入去重。在生成 JSON 时维护一个已用图片 URL 集合，每次插入前检查
2. **建立"扩展视觉素材库"**：在报告末尾、离线资产汇总之前，单独增设 **h2: 🎨 扩展视觉素材集** 专区。仅放入正文【美术风格拆解】中未使用过的高质量图片（角色立绘图鉴、场景概念图集、UI 切图等），每张配 blockquote 图注。如果检索到的图片已全部在正文中使用，没有额外新图，则直接输出"未检索到更多不重复的高质量素材"，严禁拿已用图片凑数
3. **视觉提炼（干货化）**：文字描述极度精简为 bullet points，直接提炼：
   - 形体结构（轮廓、比例、剪影、视觉引导线）
   - 色彩比例（标注 Hex 色值）
   - 材质渲染细节（shader 类型、表面处理）
   - 禁止写大段游戏世界观/剧情流水账 — 只写视觉可观察的纯美术干货
4. **规范图注**：每张 image block 必须带 caption，包含视觉特征分析（不只是描述图片内容）：
   ```json
   {"type": "image", "url": "https://...", "caption": "沙漠日落 — 天空从 #FF8C00 橙过渡到 #6B5B7B 紫，台地轮廓在逆光中形成鲜明剪影"}
   ```

### Image Sources

Search for direct image URLs on these hosts (they serve hotlinkable images):
- **Steam CDN** — ⚠️ **URL format changed in 2026** (see Steam Screenshot URL Format below)
- **ArtStation** — ⚠️ **requires special handling** (see ArtStation Image Extraction below)
- **Fandom Wiki** — full-res uploads, usually direct-accessible
- **Official press kits** — hosted on game domain CDNs
- If you cannot find a direct URL, use a text block with link instead — do NOT fabricate image URLs

### Steam Screenshot URL Format (2026)

Steam changed their CDN URL structure. You MUST use the **new format** or images will 404:

```
# OLD (BROKEN — do NOT use):
https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{APPID}/ss_{HASH}.jpg

# NEW (correct):
https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{APPID}/{HASH}/ss_{HASH}.1920x1080.jpg?t={timestamp}
```

Key differences:
1. Hash directory segment: `/{HASH}/` added before the filename
2. Size suffix: `.1920x1080.jpg` instead of `.jpg`
3. Timestamp query: `?t={unix_timestamp}` (use current timestamp)

**How to get correct URLs**: Fetch the Steam store page and extract screenshot URLs from the JSON data in the page HTML. Look for the `"screenshots"` array which contains `"full"`, `"standard"`, and `"thumbnail"` URLs — all in the correct new format.

**Automatic fix**: The publish script (`publish_to_feishu.py`) includes `_fix_steam_url()` which auto-corrects old-format URLs. But generating correct URLs from the start is more reliable.

### Image Size & Compression

The publish pipeline automatically compresses images before upload:
- Max width: 1200px (wider images are resized proportionally)
- Format: JPEG at 85% quality
- RGBA/P mode images are converted to RGB

You can optionally specify `width` and `height` on image/gallery blocks to control rendering:
```json
{"type": "image", "url": "...", "caption": "...", "width": 800, "height": 450}
{"type": "gallery", "urls": ["..."], "width": 600}
```

### ArtStation Image Extraction

ArtStation uses aggressive CDN hotlink protection (S3 AccessDenied 403). Direct CDN URLs (`/p/assets/images/images/`) are blocked programmatically. Use this strategy:

1. **During research (Step 3)**: When you find an ArtStation artwork page (e.g. `https://www.artstation.com/artwork/XXXXX`), use `mcp__web_reader__webReader` to fetch the page
2. **Extract image URLs** from the page's metadata — look for:
   - `og:image` meta tag → usually points to `/p/assets/covers/images/` path which is **publicly accessible**
   - `twitter:image` meta tag → same accessible path
   - Any `<img>` src attributes in the fetched content
3. **Prefer cover URLs**: URLs matching `/p/assets/covers/images/` are proven downloadable. URLs matching `/p/assets/images/images/` will likely 403
4. **URL transformation fallback** (handled automatically by publish_to_feishu.py):
   - The script tries: covers path → CDN subdomain rotation → small size variant → strip query params
   - But getting the right URL upfront is more reliable
5. **If web_reader fails**: Use a text block with a link to the ArtStation page instead of an image block — do NOT fabricate CDN URLs

### AI Prompt 参考

- **h2: 🎨 AI 生成参考 Prompt** — 为角色和场景各生成一组可用于 Midjourney / Stable Diffusion 的英文描述词
  - **h3: 角色生成 Prompt** — 基于 角色 分析中的体型、材质、色彩语言，生成 2-3 组 prompt。格式：`<pre>` 代码块，每行一个完整 prompt
  - **h3: 场景生成 Prompt** — 基于 场景 分析中的色温、构图、光照模型，生成 2-3 组 prompt。格式同上
  - Prompt 风格指南：以英文输出，包含 medium (game concept art / digital painting)、主体描述、色彩关键词、光照描述、风格限定词 (stylized / semi-realistic / Blizzard style)

### 离线资产汇总

- **h2: 📋 离线资产路径汇总** — 结尾附加一个 Markdown pipe 表格，汇总所有资源链接。列：
  - `| 资产名称 | 类型 | 来源 | 链接 | 备注 |`
  - 类型填：Concept Art / 3D Model / Texture / UI / Press Kit / Wiki / Tutorial
  - 此表格方便直接粘贴到飞书多维表格中作为记录
  - **链接完整性**：所有 URL 必须是完整且未经截断的绝对路径（Absolute URL）。严禁使用带有 `...` 的缩略文本
  - **有效超链接**：表格中的链接必须使用 `<a href="完整URL">点击查看</a>` 格式，确保在飞书中可以一键点击跳转

### 视觉色板

- 在 **美术风格拆解** 的 **场景 (Environments)** 小节末尾，增加一个 `quote` block 色板摘要：
  ```json
  {"type": "quote", "elements": [
    {"text": "🎨 色板\n", "bold": true},
    {"text": "主色", "bold": true}, {"text": "：🟨 "}, {"text": "#D4A745", "inline_code": true}, {"text": " (废土黄) · 🟧 "}, {"text": "#A0522D", "inline_code": true}, {"text": " (铁锈红) · 🟫 "}, {"text": "#8B6914", "inline_code": true}, {"text": " (风化棕)\n"},
    {"text": "辅色", "bold": true}, {"text": "：⚫ "}, {"text": "#4A4A4A", "inline_code": true}, {"text": " (深灰金属) · 🔵 "}, {"text": "#2C3E50", "inline_code": true}, {"text": " (暗蓝夜空)\n"},
    {"text": "点缀", "bold": true}, {"text": "：🟡 "}, {"text": "#FFD700", "inline_code": true}, {"text": " (霓虹金) · 🔴 "}, {"text": "#FF4444", "inline_code": true}, {"text": " (警告红) · 🩵 "}, {"text": "#00CED1", "inline_code": true}, {"text": " (科技蓝)"}
  ]}
  ```
  - 色板必须从分析内容中提取，至少 3 个主色 + 2 个辅色 + 2-3 个点缀色
  - 每个颜色标注 Hex 值和中文用途描述
  - **Emoji 色块**：每个 Hex 色值前必须加上对应颜色的 Emoji（🔴红 🟠橙 🟡黄 🟢绿 🔵蓝 🟣紫 ⚫黑 ⚪白 🟤棕 🩵浅蓝 🩷粉 🟨金黄 🟧橙红 🟫深棕 等），并用 `<code>` 包裹 Hex 值，让色板在飞书中视觉跳跃、取色直观

## Formatting & Readability Rules

- **链接工具化**：所有资源站链接（ArtStation / Sketchfab / Models Resource 等）必须生成带搜索关键词的直链。例如：
  - `https://www.artstation.com/search?q=overwatch+junkertown` 而非 `https://www.artstation.com`
  - `https://sketchfab.com/search?q=overwatch+junkertown&type=models` 而非 `https://sketchfab.com`
  - 绝不输出裸域名首页链接
- **排版减负**：使用飞书友好的排版增强可读性
  - 在 `<strong>` 标签旁适当使用 Emoji 作为视觉锚点：`📍` 定位信息、`🎨` 美术风格、`🔗` 链接、`🎮` 游戏、`👤` 角色、`🏗️` 场景、`🖥️` UI、`📦` 资产、`🎨` 色板
  - 每个大章节开头用一行引用块 `<blockquote>` 做摘要导读
  - 长列表中每项用 `<strong>` 加粗关键标签，描述跟在后面
  - 避免大段连续纯文本，每 3-5 段插入一个图片或引用块打断视觉节奏

## Guidelines

- **Delegate heavy text work to sub-agents**: Report generation (writing the full HTML) and Feishu publishing MUST run inside a sub-agent (Agent tool with `general-purpose` type). Pass all collected research data to the sub-agent via the prompt. This keeps the main conversation context clean and avoids hitting context limits.
- **Autonomous execution**: Never ask for user confirmation during research, generation, or publishing. Auto-skip 404/403 images. Return only the final Feishu URL.
- Use WebSearch for every lookup. Do not guess or fabricate URLs.
- If a search yields no results for a specific category, state it explicitly rather than skipping.
- For Chinese games, search both Chinese and English names.
- Keep the report actionable — every link should be something the user can click and use immediately.
- The report should be comprehensive enough to serve as a project reference document, not just a quick summary.
- Prefer direct image URLs (`<img src="...">`) over page links when showing visual examples — Feishu renders them inline.
