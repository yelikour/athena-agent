# 🏛️ Athena

**轻量级本地 AI Agent 框架 — 隐私优先，即装即用**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-22%20passed-brightgreen)](https://github.com/yelikour/athena-agent)
[![Stars](https://img.shields.io/github/stars/yelikour/athena-agent.svg?style=social)](https://github.com/yelikour/athena-agent)

## ✨ 特性

- 🚀 **极简设计** — 核心代码 < 500 行，易于理解和扩展
- 🔒 **完全本地** — 基于 Ollama，数据不离开你的电脑
- 🧠 **持久记忆** — SQLite + FTS5 全文搜索，跨会话记住信息
- 🔧 **工具调用** — MCP 兼容的工具注册系统，可扩展
- 💬 **交互式聊天** — 命令行界面，即装即用

## 🚀 快速开始

### 前置要求

- Python 3.10+
- [Ollama](https://ollama.com/) 已安装并运行

### 安装

```bash
# 1. 安装 Ollama (如果还没装)
curl -fsSL https://ollama.com/install.sh | sh

# 2. 下载一个模型
ollama pull llama3.2:3b

# 3. 安装 Athena
pip install git+https://github.com/yelikour/athena-agent.git
```

### 使用

```bash
# 启动聊天
athena

# 使用特定模型
athena -m llama3.2:3b

# 搜索记忆
athena --memory-search "Python"

# 保存到记忆
athena --memory-save "记住：我喜欢用 Python"

# 查看记忆
athena --memory-list

# 列出可用工具
athena --list-tools
```

## 📖 使用示例

### Python API

```python
from athena import Agent

# 创建 Agent
agent = Agent(model="llama3.2:3b")

# 聊天
response = agent.chat("帮我写一个 Python 排序函数")
print(response)

# 保存记忆
agent.memory.save("用户偏好：中文回复", category="preferences")

# 搜索记忆
results = agent.memory.search("偏好")

# 添加自定义工具
@agent.tools.register("weather")
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city} 今天晴天，25°C"

# 使用工具
response = agent.chat("北京天气怎么样？")
```

### 命令行

```bash
$ athena
🏛️ Athena v0.1.0 - Lightweight Local AI Agent
   Model: llama3.2:3b
   Memory: /home/user/.athena/memory.db
   Tools: 6 available

   Commands: 'quit' to exit, 'clear' to reset, 'memory' for info

You: 你好！
Athena: 你好！我是 Athena，你的本地 AI 助手。有什么我可以帮你的吗？

You: 帮我记一下，明天下午3点有会议
Athena: 好的，我已经记住了。让我保存到记忆中...
[memory_save] Saved to memory (id: 42, category: conversations)
我已经帮你记住了：明天下午3点有会议。我会在你需要时提醒你。

You: memory
📊 Memory entries: 42
```

## 🏗️ 架构

```
athena/
├── __init__.py      # 包入口
├── agent.py         # 核心代理（对话 + 工具调用）
├── memory.py        # 持久化记忆（SQLite + FTS5）
├── tools.py         # 工具注册系统（MCP 兼容）
└── cli.py           # 命令行界面
```

### 核心组件

| 组件 | 说明 |
|------|------|
| `Agent` | 核心代理，处理对话和工具调用 |
| `Memory` | SQLite + FTS5 全文搜索记忆 |
| `ToolRegistry` | MCP 兼容的工具注册系统 |
| `CLI` | 用户友好的命令行界面 |

## 🔧 内置工具

| 工具 | 说明 |
|------|------|
| `memory_search` | 搜索记忆 |
| `memory_save` | 保存到记忆 |
| `memory_recent` | 获取最近记忆 |
| `run_command` | 执行 shell 命令 |
| `get_time` | 获取当前时间 |
| `read_file` | 读取文件内容 |
| `list_files` | 列出目录文件 |

## 🛣️ 路线图

- [x] v0.1.0 — 核心 Agent + 记忆 + 工具
- [ ] v0.2.0 — MCP 服务器连接
- [ ] v0.3.0 — 定时任务（Cron）
- [ ] v0.4.0 — 多渠道支持（Telegram/Discord）
- [ ] v0.5.0 — RAG（检索增强生成）
- [ ] v1.0.0 — 稳定版本

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 许可证

MIT License — 详见 [LICENSE](LICENSE)

## 🙏 致谢

- [Ollama](https://ollama.com/) — 本地 LLM 运行时
- [MCP](https://modelcontextprotocol.io/) — 模型上下文协议
- [钱学森工程控制论](https://zh.wikipedia.org/wiki/工程控制论) — 系统设计哲学

---

<p align="center">
  <i>"建立这门技术科学，能赋予人们更宽阔、更缜密的眼光去观察老问题，为解决新问题开辟意想不到的新前景"</i>
  <br>— 钱学森
</p>
