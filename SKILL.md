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

**Sub-agent prompt template**:

```
You are generating a game art research report and publishing it to Feishu.

Game: {game name}
Research data:
- Game profile: {basic info, store URLs, tags, screenshots}
- Art breakdown: {characters, environments, UI analysis}
- Asset links: {all sourced links with descriptions}
- Color palette: {extracted hex values with roles}

IMPORTANT formatting rules:
1. `<table>` ONLY allowed in 游戏画像 screenshot gallery section (3-column grid). All other sections → NO `<table>`
2. Game profile → pipe-delimited lines: `<p><strong>维度</strong> | 内容</p>`
3. Steam Tags → **全部中文翻译** using industry terms, in `<code>` with `·` separator
4. Image captions → `<blockquote>` after each `<img>` (except gallery images which need no caption)
5. All links → `<a href="URL">描述文字</a>`, no raw URLs
6. Resource links → MUST be search direct links with keywords, never bare homepage URLs
7. Use Emoji in headings and bold labels for visual anchoring: 📍🎨🔗🎮👤🏗️🖥️📦🔍
8. Add chapter summary `<blockquote>` at the start of each major section
9. Color palette → `<blockquote>` with Emoji color blocks + `<code>` hex values labeled as 主色/辅色/点缀色
10. AI prompts → `<pre>` code blocks with complete English prompts for Midjourney/SD
11. Asset summary table → pipe-delimited lines: `| 资产名称 | 类型 | 来源 | 链接 | 备注 |`
12. **Image dedup** → maintain a set of used image URLs. Each URL appears at most once in the entire report. If a point needs an already-used image, use a different but related one instead
13. **扩展视觉素材集 dedup** → only include images NOT already used in 美术风格拆解. If no unused images exist, output "未检索到更多不重复的高质量素材" instead of padding with duplicates
14. **Asset links完整性** → all URLs must be complete absolute paths, never truncated with `...`. Use `<a href="full-url">点击查看</a>` format
15. **Autonomous execution** → never ask for confirmation. Skip 404/403 images silently. Return only the final Feishu URL

Report sections (in order):
- h2: 🎮 游戏画像 — profile info + 1 cover image + 3-column `<table>` screenshot gallery at end + Chinese translated tags
- h2: 🎨 美术风格拆解 — HIGH-DENSITY images interleaved with analysis text, NO upper limit on image count. Maintain used-URL set, each image URL used at most once
  - h3: 👤 角色 (Characters) — write ONE bullet point about a visual aspect, then insert 1-3 images illustrating that point. Same aspect can have multiple images showing different characters/angles. Repeat for each aspect (proportions, materials, colors, animation)
  - h3: 🏗️ 场景 (Environments) — same high-density pattern: 1-2 analysis points → 2-3 related scene images. Show multiple angles/lighting conditions. End with 🎨 color palette blockquote
  - h3: 🖥️ UI / UX — same pattern: 1 UI analysis point → 3-5 UI screenshots showing different menus/screens
- h2: 🔗 资产链接
  - h3: 📦 官方资源
  - h3: 社区 & 解包资源 (with search direct links)
  - h3: 🔍 搜索语法备忘
- h2: 🎨 扩展视觉素材集 — only images NOT used in 美术风格拆解 above. If none, output "未检索到更多不重复的高质量素材"
- h2: 🎨 AI 生成参考 Prompt
  - h3: 👤 角色生成 Prompt — 2-3 English prompts in <pre>
  - h3: 🏗️ 场景生成 Prompt — 2-3 English prompts in <pre>
- h2: 📋 离线资产路径汇总 — pipe table with complete absolute URLs in `<a>` tags, no truncation

Steps:
1. Write the full HTML report to /tmp/game-art-report.html
2. Run: python3 ~/.claude/skills/game-art-sourcing/scripts/publish_to_feishu.py /tmp/game-art-report.html --title "{Game Name} — 美术调研报告"
3. Return ONLY the Feishu document URL (or error message if it fails)

If publishing fails, return the full HTML content so the user can handle it manually.
```

The sub-agent handles all text generation, file writing, and the publish script. The main conversation only receives the final Feishu URL (or fallback HTML).

## Report Structure

The HTML body must follow this structure. **`<table>` 仅允许在游戏画像的截图画廊中使用**（3 列网格布局）。其余所有章节禁止使用 `<table>`，改用 pipe-delimited 文本行。

### Formatting Rules

1. **Game profile info** → pipe-delimited text lines: `| 维度 | 内容 |`
2. **Steam Tags** → inline code block with separator: `` `Tag1 · Tag2 · Tag3` ``
3. **Image captions** → `<blockquote>` after each image, not `<em>`
4. **External links** → markdown-style `[描述文字](URL)`, never raw URLs
5. **Asset links** → list items with markdown links + description

### Section Layout

- **h2: 游戏画像**
  - **Info**: pipe-delimited lines, one per dimension. Example:
    ```html
    <p><strong>开发商</strong> | Valve Corporation</p>
    <p><strong>发行年</strong> | 2020</p>
    <p><strong>美术风格</strong> | 风格化 / 卡通</p>
    <p><strong>游戏类型</strong> | FPS / 多人</p>
    <p><strong>Steam</strong> | <a href="https://store.steampowered.com/app/xxx">Steam 商店页</a></p>
    ```
  - **Store cover image**: `<img>` of Steam capsule/header, followed by `<blockquote>` caption
  - **Store Screenshots Gallery (商店截图画廊)**：将所有官方宣传截图集中在游戏画像末尾，使用 3 列 `<table>` 实现一行三图的画廊效果。格式：
    ```html
    <table>
    <tr><td><img src="URL_1" width="100%" /></td><td><img src="URL_2" width="100%" /></td><td><img src="URL_3" width="100%" /></td></tr>
    <tr><td><img src="URL_4" width="100%" /></td><td><img src="URL_5" width="100%" /></td><td><img src="URL_6" width="100%" /></td></tr>
    </table>
    ```
    - 图片总数不是 3 的倍数时，最后单元格留空：`<td></td>`
    - 画廊中的图片也计入全局去重（URL 只出现一次）
    - 画廊图片不需要 blockquote 图注，节省垂直空间
  - **Tags**: single `<p>` with inline code styling, **必须全部中文翻译**：
    ```html
    <p><strong>Steam Tags</strong></p>
    <p><code>角色扮演 · 生活模拟 · 休闲 · 模拟 · 冒险 · 建造 · 沙盒 · 农场模拟 · 制作 · 单人</code></p>
    ```
- **h2: 美术风格拆解** — 文字用精简 bullet points，图片紧跟对应分析点插入，禁止集中堆砌
  - **h3: 角色 (Characters)** — 每个分析维度（体型比例、材质渲染、色彩语言、动画风格）后紧跟 1 张对应图片。示例结构：
    ```html
    <p><strong>👤 体型与轮廓</strong>：略带 Q 版比例，头身比约 1:4，圆润面部特征</p>
    <img src="https://..." width="600" />
    <blockquote>图：角色全身造型 — 可见的 Q 版比例与圆润轮廓</blockquote>
    <p><strong>🎨 色彩方案</strong>：每位 NPC 一个标志性点缀色…</p>
    <img src="https://..." width="600" />
    <blockquote>图：核心 NPC 群像 — 各角色标志性配色对比</blockquote>
    ```
  - **h3: 场景 (Environments)** — 逐区域分析，每个区域 1 张图 + 分析要点。色板 blockquote 放在本节末尾
  - **h3: UI / UX** — 每个 HUD 元素/菜单分析后紧跟对应 UI 截图
- **h2: 资产链接** 🔗 — use `<ul>` lists with `<a>` links. Format:
  ```html
  <ul>
    <li><a href="URL">描述文字</a> — 补充说明</li>
  </ul>
  ```
  - **h3: 官方资源** 📦 — links with descriptions
  - **h3: 社区 & 解包资源** — links with descriptions. MUST use search direct links with keywords (e.g. `sketchfab.com/search?q=game+name&type=models`), never bare homepage URLs
  - **h3: 搜索语法备忘** 🔍 — `<pre>` code block with search queries
- **h2: 🎨 扩展视觉素材集** — 报告末尾的集中图片库。将检索过程中所有未被正文使用的高质量图片（角色立绘图鉴、场景概念图集、UI 切图、材质特写等）集中展示，每张配 blockquote 图注。不遗漏任何有价值的美术参考
- **h2: 🎨 AI 生成参考 Prompt** — Midjourney / Stable Diffusion prompts based on art analysis
  - **h3: 角色生成 Prompt** 👤 — 2-3 English prompts in `<pre>` blocks
  - **h3: 场景生成 Prompt** 🏗️ — 2-3 English prompts in `<pre>` blocks
- **h2: 📋 离线资产路径汇总** — Markdown pipe table:
  ```html
  <p><strong>资产名称</strong> | <strong>类型</strong> | <strong>来源</strong> | <strong>链接</strong> | <strong>备注</strong></p>
  <p>Asset Name | Concept Art | ArtStation | <a href="URL">链接</a> | 备注</p>
  ```
  - Types: Concept Art / 3D Model / Texture / UI / Press Kit / Wiki / Tutorial
  - Copy-paste friendly for Feishu Bitable import

### 高密度图文排版规范 (High-Density Visual-Text Rules)

**这是最高优先级的排版规则，违反即为不合格报告。**

1. **解除图片数量上限，精准锚定**：在美术风格拆解的各个子版块中，取消图片数量上限。只要是高质量的说明性图片，尽可能多地插入。必须确保图片紧贴对应的文字特征分析：
   - 分析"体型比例" → 紧跟角色全身图（可放 2-3 张不同角色的对比）
   - 分析"色彩方案" → 紧跟角色色彩对比图
   - 分析"光照模型" → 紧跟 2-3 张不同光照条件的场景图
   - 分析"UI 交互" → 紧跟 3-5 张不同 UI 界面截图
   - 每个分析要点（bullet point）最多 2 段后必须跟至少 1 张相关图片
   - 同一个要点可以跟多张图展示不同变体/角度
   - **图片去重**：同一张图片 URL 在整篇报告中只能出现一次。如果某个分析点想引用已用在其他章节的图片，换一张不同但相关的图片。游戏画像的封面图也计入去重。在生成 HTML 时维护一个已用图片 URL 集合，每次插入前检查
2. **建立"扩展视觉素材库"**：在报告末尾、离线资产汇总之前，单独增设 **h2: 🎨 扩展视觉素材集** 专区。仅放入正文【美术风格拆解】中未使用过的高质量图片（角色立绘图鉴、场景概念图集、UI 切图等），每张配 blockquote 图注。如果检索到的图片已全部在正文中使用，没有额外新图，则直接输出"未检索到更多不重复的高质量素材"，严禁拿已用图片凑数
3. **视觉提炼（干货化）**：文字描述极度精简为 bullet points，直接提炼：
   - 形体结构（轮廓、比例、剪影、视觉引导线）
   - 色彩比例（标注 Hex 色值）
   - 材质渲染细节（shader 类型、表面处理）
   - 禁止写大段游戏世界观/剧情流水账 — 只写视觉可观察的纯美术干货
4. **规范图注**：每张图下方必须有简短的美术特征解析图注（不只是描述图片内容，还要点出视觉特征）：
   ```html
   <blockquote>图：沙石镇日落光线，注意其暗部的冷色环境光反射</blockquote>
   ```
   图注必须包含视觉特征分析，不是"截图 1"这种编号

### Image Sources

Search for direct image URLs on these hosts (they serve hotlinkable images):
- **Steam CDN** — `store.steampowered.com` screenshots
- **ArtStation** — artwork images (use the `artstation.com/p/assets/...` direct URLs)
- **Fandom Wiki** — full-res uploads, usually direct-accessible
- **Official press kits** — hosted on game domain CDNs
- Use `width="600"` on images for consistent sizing
- If you cannot find a direct URL, use the page URL as an `<a>` link instead — do NOT fabricate image URLs

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

- 在 **美术风格拆解** 的 **场景 (Environments)** 小节末尾，增加一个 `<blockquote>` 色板摘要：
  ```html
  <blockquote>
  <strong>🎨 色板</strong>
  <strong>主色</strong>：🟨 <code>#D4A745</code> (废土黄) · 🟧 <code>#A0522D</code> (铁锈红) · 🟫 <code>#8B6914</code> (风化棕)
  <strong>辅色</strong>：⚫ <code>#4A4A4A</code> (深灰金属) · 🔵 <code>#2C3E50</code> (暗蓝夜空)
  <strong>点缀</strong>：🟡 <code>#FFD700</code> (霓虹金) · 🔴 <code>#FF4444</code> (警告红) · 🩵 <code>#00CED1</code> (科技蓝)
  </blockquote>
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
