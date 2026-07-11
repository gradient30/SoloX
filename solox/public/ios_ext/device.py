# -*- coding: utf-8 -*-
"""iOS 设备连接与发现（A）。

统一封装两条连接路径：

    - **lockdown（usbmux）**：适用于 iOS < 17，以及 17+ 上仍走 lockdown 的
      服务（如 screenshotr 截图）。
    - **RSD（RemoteServiceDiscovery via tunneld）**：iOS 17+ 的开发者服务
      （DVT/Instruments、Condition Inducer、CoreProfileSessionTap 等）必须
      经由 ``pymobiledevice3 remote tunneld`` 隧道守护进程建立的 RSD 连接。

pymobiledevice3 9.x 的 API 为 ``async``；本模块提供 ``async`` 内核（``*_async``）
与同步门面（经 :mod:`solox.public.ios_ext._aio` 桥接）。所有 ``pymobiledevice3``
导入均惰性完成，缺失依赖时抛出 :class:`IOSBackendUnavailable`。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from solox.public.ios_ext import _aio

DEFAULT_TUNNELD_ADDRESS = ("127.0.0.1", 49151)
# iOS 主版本 >= 该值时，DVT 系服务需经 RSD/tunneld 连接
RSD_REQUIRED_MAJOR = 17


class IOSBackendUnavailable(RuntimeError):
    """pymobiledevice3 未安装或 iOS 扩展后端不可用时抛出。"""


class TunnelUnavailable(RuntimeError):
    """iOS 17+ 需要的 tunneld 守护进程不可用时抛出。"""


def _require_pmd3() -> None:
    """确保 pymobiledevice3 可用，否则抛出带安装指引的异常。

    Raises:
        IOSBackendUnavailable: 依赖缺失时。
    """
    from solox.public import ios_ext

    if not ios_ext.is_available():
        raise IOSBackendUnavailable(
            "iOS 扩展后端需要 pymobiledevice3，请执行："
            'pip install "solox[ios]" 或 pip install pymobiledevice3'
        )


def _parse_major(product_version: str | None) -> int | None:
    """从形如 ``"17.4.1"`` 的版本串解析主版本号。"""
    if not product_version:
        return None
    head = str(product_version).split(".", 1)[0].strip()
    try:
        return int(head)
    except ValueError:
        return None


def needs_rsd(ios_major: int | None) -> bool:
    """判断该 iOS 主版本的 DVT 服务是否必须走 RSD/tunneld（iOS 17+）。

    Args:
        ios_major: iOS 主版本号。

    Returns:
        bool: 主版本 >= 17 返回 ``True``。
    """
    return bool(ios_major is not None and ios_major >= RSD_REQUIRED_MAJOR)


# ---------------------------------------------------------------------------
# async 内核
# ---------------------------------------------------------------------------
async def _list_devices_async() -> list[dict[str, Any]]:
    from pymobiledevice3.usbmux import list_devices as _list

    devices: list[dict[str, Any]] = []
    for dev in await _list():
        udid = getattr(dev, "serial", None)
        if not udid:
            continue
        devices.append({
            "udid": udid,
            "connection_type": getattr(dev, "connection_type", None),
        })
    return devices


async def _get_device_info_async(udid: str) -> dict[str, Any]:
    from pymobiledevice3.lockdown import create_using_usbmux

    client = await create_using_usbmux(serial=udid)
    try:
        values = _safe_all_values(client)
        product_version = values.get("ProductVersion")
        return {
            "udid": udid,
            "product_version": product_version,
            "product_type": values.get("ProductType"),
            "device_name": values.get("DeviceName"),
            "ios_major": _parse_major(product_version),
        }
    finally:
        await _aio.aclose(client)


async def _create_lockdown_async(udid: str) -> Any:
    from pymobiledevice3.lockdown import create_using_usbmux

    return await create_using_usbmux(serial=udid)


async def _create_rsd_async(
    udid: str,
    tunneld_address: tuple[str, int] = DEFAULT_TUNNELD_ADDRESS,
) -> Any:
    from pymobiledevice3.tunneld.api import (
        TunneldConnectionError,
        get_tunneld_device_by_udid,
    )

    try:
        rsd = await get_tunneld_device_by_udid(
            udid, tunneld_address=tunneld_address
        )
    except TunneldConnectionError as exc:
        raise TunnelUnavailable(
            "无法连接 tunneld 守护进程，请先运行："
            "sudo pymobiledevice3 remote tunneld"
        ) from exc
    if rsd is None:
        raise TunnelUnavailable(
            f"tunneld 中未找到设备 {udid}，请确认已连接并启动隧道"
        )
    return rsd


@asynccontextmanager
async def dvt_session_async(
    udid: str,
    ios_major: int | None = None,
    tunneld_address: tuple[str, int] = DEFAULT_TUNNELD_ADDRESS,
) -> AsyncIterator[Any]:
    """建立并管理一个 DVT（Instruments）会话（async 上下文）。

    自动按 iOS 版本选择底层连接：17+ 走 RSD/tunneld，其余走 lockdown。退出上
    下文时自动关闭 DVT 与底层连接。

    Args:
        udid: 设备标识。
        ios_major: 已知主版本；为 ``None`` 时自动探测。
        tunneld_address: tunneld 地址（仅 17+ 使用）。

    Yields:
        Any: 已连接的 ``DtxServiceProvider``，可直接传给
        :class:`ConditionInducer` / :class:`Screenshot` /
        :class:`CoreProfileSessionTap`。
    """
    _require_pmd3()
    from pymobiledevice3.dtx_service_provider import DtxServiceProvider

    if ios_major is None:
        info = await _get_device_info_async(udid)
        ios_major = info.get("ios_major")

    if needs_rsd(ios_major):
        underlying = await _create_rsd_async(
            udid, tunneld_address=tunneld_address
        )
    else:
        underlying = await _create_lockdown_async(udid)

    dvt = DtxServiceProvider(underlying)
    try:
        await dvt.connect()
        yield dvt
    finally:
        await _aio.aclose(dvt)
        await _aio.aclose(underlying)


def _safe_all_values(client: Any) -> dict[str, Any]:
    """尽量健壮地取回 lockdown 的全部键值。"""
    values = getattr(client, "all_values", None)
    if isinstance(values, dict):
        return values
    getter = getattr(client, "get_value", None)
    if callable(getter):
        try:
            result = getter()
            if isinstance(result, dict):
                return result
        except Exception:  # noqa: BLE001 - 读值失败即回退空
            return {}
    return {}


# ---------------------------------------------------------------------------
# 同步门面
# ---------------------------------------------------------------------------
def list_devices() -> list[dict[str, Any]]:
    """枚举当前通过 USB 连接的 iOS 设备（同步）。

    Returns:
        List[Dict[str, Any]]: 每项含 ``udid`` / ``connection_type``。

    Raises:
        IOSBackendUnavailable: pymobiledevice3 未安装时。
    """
    _require_pmd3()
    return _aio.run(_list_devices_async())


def get_device_info(udid: str) -> dict[str, Any]:
    """读取设备基础信息（型号、系统版本等，同步）。

    Args:
        udid: 设备唯一标识（usbmux serial）。

    Returns:
        Dict[str, Any]: 含 ``product_version`` / ``product_type`` /
        ``device_name`` / ``ios_major``。

    Raises:
        IOSBackendUnavailable: pymobiledevice3 未安装时。
    """
    _require_pmd3()
    return _aio.run(_get_device_info_async(udid))
