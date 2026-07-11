# -*- coding: utf-8 -*-
"""SoloX MCP 集成：将性能报告查询/分析能力暴露给 AI 客户端。

- ``tools``：平台无关的纯函数工具（可单测，不依赖 MCP SDK）。
- ``server``：MCP stdio 服务入口，惰性导入 ``mcp`` SDK（未安装时给出提示）。
"""
