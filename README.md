# Game Art Sourcing

Claude Code Skill — 游戏美术风格深度调研，自动生成结构化报告并发布到飞书云文档。

输入一个游戏名，自动完成：信息检索 → 美术分析（角色/场景/UI） → JSON 报告生成 → 飞书文档发布。终端只输出一个飞书 URL。

## 功能

- **游戏画像**：自动从 Steam/官方源收集基本信息、商店截图、Steam Tags
- **美术风格拆解**：角色（比例/材质/色彩/剪影）、场景（色温/构图/光照）、UI/UX 三个维度
- **资产链接**：官方 Press Kit、ArtStation、Sketchfab、Fandom Wiki 等资源直链
- **视觉色板**：自动提取 Hex 色值，带 Emoji 色块标注
- **AI 生成 Prompt**：基于分析自动生成 Midjourney/SD 英文描述词
- **飞书一键发布**：JSON 直接转飞书 Block API，图片并行下载上传
- **搜索缓存**：7 天内重复调研同一游戏，跳过网络请求直接生成报告

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
pip install requests PyYAML
```

### 4. 减少确认提示（推荐）

技能运行时会执行 Python 脚本，Claude Code 默认会逐个请求确认。项目已内置 `.claude/settings.json` 自动授权常用命令，克隆后无需额外配置。

如需手动配置，将以下内容加入你的 `~/.claude/settings.json`：

```json
{
  "permissions": {
    "allow": [
      "Bash(python3 ~/.claude/skills/game-art-sourcing/*)"
    ]
  }
}
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
SKILL.md                ← 技能定义（工作流、排版规范、子代理模板）
block_builder.py         ← JSON schema → 飞书 Block API 转换器
cache_manager.py         ← 搜索结果缓存（7 天 TTL）
feishu_client.py         ← 飞书 Block API 封装（支持并行图片上传）
converter.py             ← HTML → 飞书 Block（旧模式保留）
config.example.yaml      ← 飞书凭证示例
scripts/
  publish_to_feishu.py   ← 发布脚本：JSON/HTML → 创建文档 → 并行上传 → 写入
cache/                   ← 本地缓存目录（gitignore）
```

## 缓存管理

```bash
# 查看所有缓存
python3 cache_manager.py list

# 清除指定游戏缓存
python3 cache_manager.py clear "沙石镇时光"

# 清空全部缓存
python3 cache_manager.py clear --all
```

缓存有效期 7 天，过期自动重新调研。

## 技术要点

- **JSON 直出**：跳过 HTML 中间层，`block_builder.py` 直接将 JSON schema 转为飞书 Block API 格式
- **并行图片处理**：`ThreadPoolExecutor` 并行下载（6 线程）和上传（4 线程），图片处理耗时从串行 20s 压缩到 3-5s
- **飞书 Block API**：不支持 `<table>` 渲染，报告使用 pipe-delimited 文本行
- **图片处理**：3 步流程（创建空块 → 上传 media → patch 替换），单张失败不阻塞
- **子代理委托**：报告生成和发布在子代理中执行，防止主对话上下文溢出
- **自动容错**：图片 404/403 自动跳过，不中断流程
- **搜索缓存**：URL-safe base64 键名，支持中英文游戏名

## License

MIT
