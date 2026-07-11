# -*- coding: utf-8 -*-
"""基于 pymobiledevice3 的 iOS 扩展后端（隔离、可选、惰性）。

本包补齐 tidevice 链路缺失的 iOS 能力：iOS 17+ 隧道连接、程序化弱网
（Condition Inducer）、截图/录屏、真实 Jank（CoreProfileSessionTap 帧时序）。

设计约束：
    - ``pymobiledevice3`` 为**可选依赖**，所有导入均在函数内部惰性完成；
      未安装时本包的探测函数返回"不可用"，绝不影响核心 SoloX（Android/旧
      iOS 链路）。
    - 仅供个人、非商业、纯本地使用（详见 docs/plans/2026-07-11-ios-pmd3-
      backend.md 的许可证说明）。

真机验收边界：设备相关能力需 iOS 真机（A/B 需 iOS 17+ 且 tunneld 守护进程）
方可端到端验证；本模块提供真实调用代码与 mock 单测，真机联通性属"待验收"。
"""

from __future__ import annotations

import importlib.util
from typing import Any

__all__ = ["is_available", "pmd3_version", "capabilities"]


def is_available() -> bool:
    """判断 ``pymobiledevice3`` 是否已安装且可导入。

    Returns:
        bool: 已安装返回 ``True``，否则 ``False``。仅做存在性检查，不真正
        import 重量级子模块，避免拖慢核心链路启动。
    """
    try:
        return importlib.util.find_spec("pymobiledevice3") is not None
    except (ImportError, ValueError):
        return False


def pmd3_version() -> str | None:
    """返回已安装的 ``pymobiledevice3`` 版本字符串。

    Returns:
        Optional[str]: 版本号；未安装或无法探测时返回 ``None``。
    """
    if not is_available():
        return None
    try:
        from importlib.metadata import PackageNotFoundError, version

        try:
            return version("pymobiledevice3")
        except PackageNotFoundError:
            return None
    except ImportError:
        return None


def capabilities() -> dict[str, Any]:
    """汇总 iOS 扩展后端各项能力的可用性。

    该结果仅反映"依赖是否就绪"，不代表已连接真机或真机联通性验证通过。

    Returns:
        Dict[str, Any]: 形如::

            {
                "backend": "pymobiledevice3",
                "available": bool,       # 依赖是否就绪
                "version": str | None,
                "features": {
                    "device_link": bool,   # A 设备连接/枚举
                    "weaknet": bool,       # B Condition Inducer 弱网
                    "screenshot": bool,    # C 截图/录屏
                    "frametime": bool,     # D 帧时序/真实 Jank
                },
                "notes": str,
            }
    """
    available = is_available()
    return {
        "backend": "pymobiledevice3",
        "available": available,
        "version": pmd3_version(),
        "features": {
            "device_link": available,
            "weaknet": available,
            "screenshot": available,
            "frametime": available,
        },
        "notes": (
            "个人自用后端；A/B 能力需 iOS 17+ 真机与 tunneld 守护进程，"
            "真机联通性属待验收项"
        ),
    }
