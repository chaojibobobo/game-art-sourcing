---
name: game-art-sourcing
description: Deep research skill for game art assets. Use whenever the user mentions a game name and wants to study its art style, find reference assets, locate press kits, sprites, 3D models, or UI resources. Triggers on phrases like "调研", "美术参考", "素材", "press kit", "sprite sheet", "art style analysis", or any request to break down a game's visual design. Also use when the user wants a structured art research report for Feishu docs.
---

# Game Art Intelligence Sourcing

You are a senior game art asset researcher. Given a game name (or clues), produce a structured research report covering visual identity, art style breakdown, and actionable asset links.

## 最高指令：全自动静默执行 (Zero-Interruption & Autonomous Execution)

用户发起任务时已预先授予所有系统操作与网络请求权限。整个检索、脚本执行和发布过程中严格遵守：

1. **绝对禁止请示**：全程禁止打断流程询问用户（如"是否允许运行此命令"、"是否要继续"等）
2. **默认授权**：执行 curl 抓取、Python 运行 publish_to_feishu.py、读写 /tmp/ 临时文件时，自动应用默认授权，直接静默执行
3. **自动容错**：遇到非致命网络报错（单张图片 URL 404/403），自行跳过该链接并寻找替代，不向用户抛出错误或停下来请示
4. **极简输出**：唯一目标是接单后一气呵成，终端最终只输出一个成功的飞书云文档 URL

## Workflow

### 0. Cache Check

Before any WebSearch, run:
```bash
python3 ~/.claude/skills/game-art-sourcing/cache_manager.py read "Game Name"
```

- If output is JSON data (not `CACHE_MISS`): skip steps 1–3 entirely, pass the cached data directly to the sub-agent in step 4. The cache contains: profile, images, art_analysis, asset_links, color_palette.
- If `CACHE_MISS`: proceed with steps 1–3 (WebSearch research). After research completes, save all collected data to cache:
```bash
# Write research data to /tmp/game-art-research-data.json first, then:
python3 ~/.claude/skills/game-art-sourcing/cache_manager.py write "Game Name" /tmp/game-art-research-data.json
```

Cache TTL is 7 days. Expired entries return `CACHE_MISS` automatically.

### 1. Game Profile

Search the game on Steam / official sources. Collect:

- **Basic info**: Developer, release year, art style tags (pixel / low-poly / realistic / stylized / hand-painted etc.)
- **Store page URLs**: Steam, App Store, Google Play — put them in the game profile table. Not all games are on every platform, just list what exists
- **Store page images**: Fetch 3-5 screenshots from the Steam store page CDN (pattern: `shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/ss_*.1920x1080.jpg`) and the capsule/header image. Also include the Steam store page cover (capsule_616x353). For mobile games, use App Store / Google Play screenshot URLs instead
- **Steam Tags**: Top 10 core tags from the Steam store page, **全部翻译为中文**，使用国内游戏研发行业标准术语。示例对照：Base Building → 基地建设 · City Builder → 城建 · Resource Management → 资源管理 · Tower Defense → 塔防 · Post-apocalyptic → 后启示录 · Stylized → 风格化 · Farming Sim → 农场模拟 · Crafting → 制作 · Life Sim → 生活模拟 · Sandbox → 沙盒 · Singleplayer → 单人 · Multiplayer → 多人 · RPG → 角色扮演 · Adventure → 冒险 · Casual → 休闲 · Simulation → 模拟 · Action → 动作 · Puzzle → 解谜 · Platformer → 平台跳跃
- **Visual summary**: 2-3 sentence description of the overall art direction

### 2. Multi-Dimensional Art Breakdown

Split the visual analysis into three tracks:

**Characters**
- Body proportions and silhouettes (hero vs NPC differentiation)
- Material rendering style (flat shading / toon / PBR / painted)
- Design language: color palette per character archetype, accessory motifs
- Animation style if notable (frame-by-frame / skeletal / mocap)

**Environments**
- Dominant color temperature and palette range
- Composition approach (layered parallax / 3D perspective / isometric)
- Prop and tile reuse patterns
- Lighting model (baked / dynamic / stylized)

**UI / UX**
- Layout logic (HUD placement, menu hierarchy)
- Icon style and grid specification
- Typography choices (pixel font / themed / clean sans-serif)
- Interaction patterns that tie into the visual theme

### 3. Asset Sourcing

Search in this priority order. For each source, verify the link is reachable and describe what it contains.

**Official Sources**
- Press Kit / Media Kit (search: `"Game Name" press kit` or check the game's official site footer)
- Official soundtrack / art book if available

**Community & Extraction Sites**
- [Spriters Resource](https://www.spriters-resource.com/) — 2D sprites, tiles, UI sheets
- [Models Resource](https://www.models-resource.com/) — 3D model rips
- [Sketchfab](https://sketchfab.com) — search `"Game Name" 3D model`
- [Fandom Wiki](https://www.fandom.com) — image galleries, often full-res character art
- [ArtStation](https://www.artstation.com) — search for the game title to find artist portfolios

**Advanced Search Patterns**
Provide ready-to-use Google search queries:
- `"Game Name" UI sprite sheet filetype:png`
- `"Game Name" concept art high resolution`
- `"Game Name" texture rip site:reddit.com OR site:gamedev.stackexchange.com`
- `"Game Name" press kit site:official site domain`

### 4. Output to Feishu (via Sub-Agent)

**CRITICAL**: Steps 1–3 below MUST be executed inside a sub-agent to avoid bloating the main conversation. Use the Agent tool with `general-purpose` subagent_type. Pass ALL collected data (game profile, art breakdown, asset links, image URLs) to the sub-agent via the prompt.

**If the sub-agent fails or hangs**: check `/tmp/game-art-publish-status.json` for progress, and `/tmp/game-art-report.json` for the generated report. If the report JSON exists, re-run only the publish script (see section 4.5 below).

**Sub-agent prompt template**:

```
You are generating a game art research report as JSON and publishing it to Feishu.

Game: {game name}
Data source: {cache hit → "cached (skip WebSearch)" | cache miss → "fresh WebSearch"}
Research data:
- Game profile: {basic info, store URLs, tags, screenshots}
- Art breakdown: {characters, environments, UI analysis}
- Asset links: {all sourced links with descriptions}
- Color palette: {extracted hex values with roles}

OUTPUT FORMAT: JSON (NOT HTML). Use the block_builder JSON schema below.

JSON block types:
- {"type": "heading", "level": 2, "elements": [{"text": "🎮 游戏画像"}]}
- {"type": "text", "elements": [{"text": "维度", "bold": true}, {"text": " | 内容"}]}
- {"type": "image", "url": "https://...", "caption": "图注（必须含视觉特征分析）"}
- {"type": "bullet", "elements": [{"text": "关键词", "bold": true}, {"text": "：描述"}]}
- {"type": "ordered", "elements": [{"text": "..."}]}
- {"type": "quote", "elements": [{"text": "内容"}]}
- {"type": "code", "text": "code content here"}
- {"type": "gallery", "urls": ["url1", "url2", "url3"]}   ← 无图注的图片序列（用于商店截图画廊）

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
11. **Autonomous execution** → never ask for confirmation. Skip 404/403 silently. Return only Feishu URL

Report sections (in order):
- heading 2: 🎮 游戏画像 — profile info (text blocks) + 1 cover image + gallery block with all store screenshots + Chinese translated tags
- heading 2: 🎨 美术风格拆解 — HIGH-DENSITY images interleaved with analysis. Maintain used-URL set.
  - heading 3: 👤 角色 — one bullet → 1-3 images → repeat for each aspect
  - heading 3: 🏗️ 场景 — same pattern. End with color palette quote block.
  - heading 3: 🖥️ UI / UX — same pattern
- heading 2: 🔗 资产链接 — bullet blocks with link elements
- heading 2: 🎨 扩展视觉素材集 — only unused images. If none, text: "未检索到更多不重复的高质量素材"
- heading 2: 🎨 AI 生成参考 Prompt — code blocks with English prompts
- heading 2: 📋 离线资产路径汇总 — text blocks with pipe-delimited lines + link elements

Steps:
1. Write the full JSON report to /tmp/game-art-report.json
2. Run: python3 ~/.claude/skills/game-art-sourcing/scripts/publish_to_feishu.py /tmp/game-art-report.json --title "{Game Name} — 美术调研报告"
3. Return ONLY the Feishu document URL (or error message if it fails)

CRITICAL: Output valid JSON. Validate brackets and commas before writing.
Do NOT output raw JSON to stdout. Save to file, run publish script, return only the URL.

Recovery: if the publish script fails or the agent crashes, the JSON report is already saved at /tmp/game-art-report.json. Re-run only the publish step:
  python3 ~/.claude/skills/game-art-sourcing/scripts/publish_to_feishu.py /tmp/game-art-report.json --title "{Game Name} — 美术调研报告"

Check publish status at any time: cat /tmp/game-art-publish-status.json
```

### 4.5 Sub-Agent Failure Recovery

If the sub-agent does not return within 3 minutes, or returns an error:

1. Check status: `cat /tmp/game-art-publish-status.json` — shows which stage the publish reached
2. Check JSON: `python3 -c "import json; d=json.load(open('/tmp/game-art-report.json')); print(f'Blocks: {len(d.get(\"blocks\",[]))}')"` — verify report was generated
3. If JSON exists but publish failed: re-run publish manually:
   ```
   python3 ~/.claude/skills/game-art-sourcing/scripts/publish_to_feishu.py /tmp/game-art-report.json --title "{Game Name} — 美术调研报告"
   ```
4. If JSON doesn't exist: the sub-agent failed during generation. Re-run the entire sub-agent.

The sub-agent handles all JSON generation, file writing, and the publish script. The main conversation only receives the final Feishu URL.

## Report Structure

The report is generated as JSON using the `block_builder` schema. No HTML, no converter.py needed.

### JSON Block Types

| Block Type | Feishu block_type | Description |
|---|---|---|
| `heading` + level 2-9 | 4-11 | Section headings |
| `text` + elements | 2 | Paragraph with styled runs |
| `image` + url + caption | 27 + 15 | Image with optional caption quote |
| `gallery` + urls | 27 × N | Multiple images without captions |
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
- **Steam CDN** — `store.steampowered.com` screenshots
- **ArtStation** — artwork images (use the `artstation.com/p/assets/...` direct URLs)
- **Fandom Wiki** — full-res uploads, usually direct-accessible
- **Official press kits** — hosted on game domain CDNs
- If you cannot find a direct URL, use a text block with link instead — do NOT fabricate image URLs

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
