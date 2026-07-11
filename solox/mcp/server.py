# -*- coding: utf-8 -*-
"""SoloX MCP stdio 服务入口。

将 :mod:`solox.mcp.tools` 中的只读工具通过 MCP 协议暴露给任意 AI 客户端
（Cursor / Claude / 自定义 Agent）。MCP SDK 为**可选依赖**，仅在实际运行本
服务时才需要，因此这里惰性导入，避免影响 SoloX 主体与测试的导入。

运行::

    pip install "mcp>=1.0"          # 可选依赖
    python -m solox.mcp.server

客户端（如 Cursor）配置示例::

    {
      "mcpServers": {
        "solox": { "command": "python", "args": ["-m", "solox.mcp.server"] }
      }
    }
"""

from __future__ import annotations

import sys

from solox.mcp import tools


def _require_mcp():
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except Exception:
        sys.stderr.write(
            'SoloX MCP 需要可选依赖 mcp SDK：\n'
            '  pip install "mcp>=1.0"\n'
        )
        raise SystemExit(2)
    return FastMCP


def build_server():
    """构建并注册 FastMCP 服务（在此才导入 SDK）。"""
    FastMCP = _require_mcp()
    server = FastMCP('solox')

    @server.tool()
    def list_reports(limit: int = 20) -> dict:
        """列出最近的 SoloX 性能报告。"""
        return tools.list_reports(limit=limit)

    @server.tool()
    def get_report_metrics(scene: str) -> dict:
        """获取某个报告的 min/max/avg 指标汇总。"""
        return tools.get_report_metrics(scene)

    @server.tool()
    def detect_issues(scene: str) -> dict:
        """对某个报告运行规则引擎，输出性能问题结论。"""
        return tools.detect_issues(scene)

    @server.tool()
    def compare_reports(base: str, target: str) -> dict:
        """对比两个报告，输出回归 diff（改善/恶化）。"""
        return tools.compare_reports(base, target)

    return server


def main() -> int:
    server = build_server()
    server.run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
