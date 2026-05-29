# 🏛️ Athena

**轻量级本地 AI Agent 框架**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/yeli/athena-agent.svg?style=social)](https://github.com/yeli/athena-agent)

Athena 是一个轻量级、注重隐私的本地 AI Agent 框架。基于 Ollama 运行，所有数据存储在本地。

## ✨ 特性

- 🚀 **极简设计** - 核心代码 < 500 行，易于理解和扩展
- 🔒 **完全本地** - 基于 Ollama，数据不离开你的电脑
- 🧠 **持久记忆** - SQLite + FTS5 全文搜索
- 🔧 **工具调用** - MCP 兼容的工具注册系统
- 💬 **交互式聊天** - 命令行界面，即装即用

## 🚀 快速开始

### 安装

```bash
# 1. 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. 下载模型
ollama pull llama3.2:3b

# 3. 安装 Athena
pip install git+https://github.com/yeli/athena-agent.git
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
```

## 📖 核心概念

### Agent（代理）

Athena 的核心是 `Agent` 类，它处理：

1. **对话管理** - 维护对话历史
2. **工具调用** - 自动检测和执行工具
3. **记忆存储** - 重要信息自动保存

```python
from athena import Agent

agent = Agent(model="llama3.2:3b")
response = agent.chat("帮我写一个 Python 函数")
print(response)
```

### Memory（记忆）

基于 SQLite 的持久化记忆，支持全文搜索：

```python
from athena.memory import Memory

memory = Memory("~/.athena/memory.db")
memory.save("Python 是最好的编程语言", category="tech")
results = memory.search("编程")
```

### Tools（工具）

可扩展的工具系统，兼容 MCP 协议：

```python
from athena.tools import ToolRegistry

registry = ToolRegistry()

@registry.register("weather")
def get_weather(city: str) -> str:
    """获取城市天气"""
    return f"{city} 今天晴天"

# 执行工具
result = registry.execute("weather", city="北京")
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

## 🛣️ 路线图

- [ ] v0.2 - MCP 服务器连接
- [ ] v0.3 - 定时任务（Cron）
- [ ] v0.4 - 多渠道支持（Telegram/Discord）
- [ ] v0.5 - RAG（检索增强生成）
- [ ] v1.0 - 稳定版本

## 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE)

## 🙏 致谢

- [Ollama](https://ollama.com/) - 本地 LLM 运行时
- [MCP](https://modelcontextprotocol.io/) - 模型上下文协议
- [钱学森工程控制论](https://zh.wikipedia.org/wiki/工程控制论) - 系统设计哲学
