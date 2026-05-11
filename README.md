# Game Art Sourcing

Claude Code Skill — 游戏美术风格深度调研，自动生成结构化报告并发布到飞书云文档。

输入一个游戏名，自动完成：信息检索 → 美术分析（角色/场景/UI） → HTML 报告生成 → 飞书文档发布。终端只输出一个飞书 URL。

## 功能

- **游戏画像**：自动从 Steam/官方源收集基本信息、商店截图、Steam Tags
- **美术风格拆解**：角色（比例/材质/色彩/剪影）、场景（色温/构图/光照）、UI/UX 三个维度
- **资产链接**：官方 Press Kit、ArtStation、Sketchfab、Fandom Wiki 等资源直链
- **视觉色板**：自动提取 Hex 色值，带 Emoji 色块标注
- **AI 生成 Prompt**：基于分析自动生成 Midjourney/SD 英文描述词
- **飞书一键发布**：HTML 转飞书 Block API，图片自动下载上传

## 安装

### 1. 一键安装

```bash
git clone https://github.com/chaojibobobo/game-art-sourcing.git ~/.claude/skills/game-art-sourcing
cd ~/.claude/skills/game-art-sourcing
cp config.example.yaml config.yaml
```

### 2. 配置飞书凭证

编辑 `config.yaml`，填入你的飞书应用凭证：

```yaml
feishu:
  app_id: "your_app_id"
  app_secret: "your_app_secret"
  folder_token: ""
  user_open_id: "your_user_open_id"
```

飞书应用需要以下权限：
- `docx:document` — 创建和编辑文档
- `drive:drive` — 上传图片媒体
- `contact:user.id:readonly` — 获取用户 Open ID

### 3. 安装 Python 依赖

```bash
pip install requests beautifulsoup4 PyYAML
```

## 使用

在 Claude Code 中输入：

```
/game-art-sourcing 沙石镇时光
/game-art-sourcing Overwatch 2 Junkertown
/game-art-sourcing 塞尔达传说：王国之泪
```

或在对话中提及 "调研"、"美术参考"、"素材" 等关键词时自动触发。

## 项目结构

```
SKILL.md              ← 技能定义（工作流、排版规范、子代理模板）
config.example.yaml   ← 飞书凭证示例
config.yaml           ← 实际凭证（gitignore）
converter.py          ← HTML → 飞书 Block 格式转换
feishu_client.py      ← 飞书 Block API 封装
scripts/
  publish_to_feishu.py ← 发布脚本：转换 → 创建文档 → 上传图片 → 写入
```

## 技术要点

- **飞书 Block API**：不支持 `<table>` 渲染（block_type 22 不可用），报告使用 pipe-delimited 文本行
- **图片处理**：3 步流程（创建空块 → 上传 media → patch 替换），每张图独立处理，单张失败不阻塞
- **子代理委托**：报告生成和发布在子代理中执行，防止主对话上下文溢出
- **自动容错**：图片 404/403 自动跳过，不中断流程

## License

MIT
