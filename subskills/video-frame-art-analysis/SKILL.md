---
name: video-frame-art-analysis
description: Child workflow for game-art-sourcing when the input is a YouTube or Bilibili video URL. Use it to extract video metadata, sample key frames, analyze game art style frame by frame, and generate a Feishu-ready JSON report with actionable visual direction for a new game.
---

# Video Frame Art Analysis

This child skill handles video-first game art research. Treat the provided video as the primary visual source, then turn frame observations into reusable art-direction rules.

## When To Use

Use this child workflow when the parent `game-art-sourcing` skill receives:

- A YouTube URL: `youtube.com/watch?v=...`, `youtu.be/...`, `youtube.com/shorts/...`
- A Bilibili URL: `bilibili.com/video/BV...`, `b23.tv/...`
- A user request for "逐帧分析", "拉片", "从视频分析美术风格", or "根据这个视频做游戏美术分析"

## Workflow

Use this progress shape:

```text
[1/7] 正在识别视频来源...
[2/7] 正在获取视频元数据...
[3/7] 正在抽取关键帧...
[4/7] 正在筛选高价值画面...
[5/7] 正在逐帧标注美术特征...
[6/7] 正在生成视频风格 DNA 与新游戏建议...
[7/7] 正在生成/发布飞书报告...
```

### Step 1: Identify Source

Extract:

- Platform: YouTube / Bilibili
- Canonical URL
- Video ID: YouTube id or Bilibili BV id
- Possible game name from title, description, tags, or visible metadata

Use a filesystem-safe slug based on the video ID:

```bash
SLUG=$(python3 -c "import base64;print(base64.urlsafe_b64encode('VIDEO_ID'.strip().lower().encode()).decode().rstrip('=')[:80])")
```

Use these paths:

- Frame directory: `/tmp/game-art-${SLUG}-frames/`
- Research data: `/tmp/game-art-${SLUG}-video-data.json`
- Report JSON: `/tmp/game-art-${SLUG}-report.json`
- Progress JSON: `/tmp/game-art-${SLUG}-gen-progress.json`

### Step 2: Collect Metadata

Collect, when available:

- Title
- Channel / UP 主
- Duration
- Publish date
- Thumbnail / cover URL
- Description summary
- Whether the video is official trailer, gameplay capture, review, cutscene, or mixed edit

Prefer official platform metadata. For YouTube, oEmbed is acceptable for title/channel confirmation. For Bilibili, preserve BV id and page URL even if deeper metadata is blocked.

### Step 3: Extract Frames

Prefer real frames over thumbnails. Use the best available method in the runtime:

1. If video download/extraction tools are available, use `yt-dlp` plus `ffmpeg`.
2. If download is blocked, use browser screenshots at timestamps or platform preview frames.
3. If only thumbnail/cover is accessible, continue with limited evidence and state the limitation clearly.

Sampling strategy:

- **Full-video scan**: sample every 5-8 seconds to map visual variety.
- **Shot keyframes**: capture 1-3 representative frames per major scene change.
- **Micro-action pass**: for combat, VFX bursts, UI popups, traversal, animation beats, or transitions, sample every 0.25-0.5 seconds.

Keep frame filenames timestamped:

```text
/tmp/game-art-${SLUG}-frames/000012.50_scene-forest.jpg
/tmp/game-art-${SLUG}-frames/000045.25_vfx-impact.jpg
```

### Step 4: Select High-Value Frames

Reject:

- Black frames, logos, loading screens, heavy subtitle obstruction
- Near-duplicates
- Frames with severe motion blur unless blur is itself the style evidence
- Pure transition frames with low art information

Keep:

- Hero/character clear views
- Environment establishing shots
- Gameplay readability frames
- VFX peak frames
- UI/HUD/menu frames
- Strong composition frames
- Lighting/color palette shifts
- Frames that reveal material or rendering technique

Target 12-30 analyzed frames for a normal trailer, 30-60 for long gameplay videos.

### Step 5: Frame Annotation Schema

For each selected frame, record:

```json
{
  "timestamp": "00:45.25",
  "frame_path": "/tmp/game-art-xxx-frames/000045.25_vfx-impact.jpg",
  "shot_type": "combat / environment / character / ui / vfx / transition",
  "screen_content": "画面内容一句话",
  "composition": "主体位置、视线引导、前中后景、镜头距离",
  "color": "主色/辅色/强调色、冷暖、饱和度、Hex 推测",
  "lighting": "光源方向、明暗层级、剪影、体积光/泛光",
  "shape_language": "角色比例、轮廓、场景几何、符号形状",
  "material_rendering": "PBR/NPR/手绘贴图/描边/笔触/材质证据",
  "vfx_ui": "特效形状、粒子、UI 层级、字体与图标",
  "animation_note": "速度、停顿、拖影、定格感、夸张幅度",
  "actionable_takeaway": "对新游戏可以复用的设计规则",
  "confidence": "high / medium / low"
}
```

Every technical claim needs visual evidence. Use "疑似/可能" when evidence is incomplete.

### Step 6: Synthesize Style DNA

Aggregate frame annotations into:

- **视觉一句话**: one precise sentence naming the style.
- **Color system**: 3-5 dominant colors, 2-3 accents, usage roles.
- **Shape language**: silhouette, proportions, environment geometry, motif vocabulary.
- **Rendering stack**: PBR/NPR, toon, hand-painted, watercolor, pixel, outline, bloom, color grading, SSAO, DOF, volumetric light.
- **Character rules**: body ratio, costume density, material contrast, face/gesture readability.
- **Environment rules**: scale, camera height, prop density, atmosphere, spatial layering.
- **VFX rules**: timing, color coding, shape, readability, screen coverage.
- **UI rules**: font tone, icon style, edge treatment, opacity, screen placement.
- **Motion/camera rules**: shot distance, cuts, pauses, squash/stretch, stop-motion feel, cinematic framing.

Then translate it into new-game guidance:

- Directly reusable
- Reuse after adaptation
- Do not copy
- Best-fit game genres/camera types
- Production cost/risk
- Small-team implementation route

### Step 7: Feishu JSON Report

Generate the same JSON block schema used by the parent skill. Local frame paths are allowed in image blocks if the publish script supports local images.

Report sections:

1. `heading 2`: `📺 视频来源与抽帧说明`
   - Platform, URL, title, channel/UP, duration, video type
   - Explain extraction method and limitations
2. `heading 2`: `🎞️ 关键帧拉片分析`
   - For each selected frame: bullet summary → image block → caption with timestamp and visual evidence
3. `heading 2`: `🧬 视频风格 DNA`
   - Color, shape, rendering, VFX, UI, motion rules
4. `heading 2`: `🛠️ 美术技法分析`
   - Rendering pipeline, material/texture, post-processing, VFX technique
5. `heading 2`: `🎮 新游戏美术落地建议`
   - Directly reusable, adapt first, avoid copying, cost/risk
6. `heading 2`: `🎨 AI 生成参考 Prompt`
   - English prompts for character, environment, VFX/UI
7. `heading 2`: `📋 关键帧与资产路径汇总`
   - Pipe-delimited text lines with timestamp, frame path, source URL, note

Image caption format:

```text
00:45.25 战斗爆发帧 — 主体被青绿色 VFX 包围，暗背景压低饱和度，技能边缘使用高亮描边保证读招清晰；疑似 Bloom + additive particle。
```

## Quality Rules

- Bind every conclusion to a timestamp or frame.
- Do not write long story summaries unless they explain visual direction.
- Do not overclaim technology from one frame.
- If the video is a cinematic trailer, clearly distinguish cinematic art direction from gameplay-readable art direction.
- If subtitles or compression obscure details, say so.
- Prefer a smaller set of strong frames over many weak frames.
- The final report must be useful for art direction, concept art, UI/VFX briefs, and moodboard construction.

## Fallbacks

- If frame extraction fails, analyze accessible thumbnail/cover frames plus official screenshots found by the parent skill, and mark evidence as "limited".
- If the source video is not a game video, stop with a concise explanation and do not fabricate a game art report.
- If the game name is unknown, title the report with the video title and include `游戏名：未确认`.
