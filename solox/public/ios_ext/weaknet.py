# -*- coding: utf-8 -*-
"""iOS 程序化弱网（B）：基于 Instruments Condition Inducer。

与 Android 的 ``tc netem`` 不同，iOS Condition Inducer 的网络条件**仅在
DVT/Instruments 会话保持存活期间生效**，会话关闭即自动恢复。因此本模块把"设置
条件 → 保持会话 → 收到停止信号后恢复"整体作为一个协程跑在共享事件循环上，直到
显式 :func:`IOSWeakNetManager.clear`。

pymobiledevice3 9.x 的 Condition Inducer API 为 ``async``（``connect``/``list``/
``set``/``clear`` 均为协程）。iOS 17+ 需 tunneld 守护进程（见 device 模块）。
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from dataclasses import dataclass, field
from typing import Any

from solox.public.ios_ext import _aio
from solox.public.ios_ext import device as _dev

# 网络相关 Condition 的筛选关键字
_NETWORK_HINTS = ("network", "slownetwork", "networklink")


@dataclass
class _Session:
    """一个保持存活的弱网会话句柄。"""

    udid: str
    profile_identifier: str
    stop_event: asyncio.Event
    task: "concurrent.futures.Future[Any]"
    error: str | None = None
    info: dict[str, Any] = field(default_factory=dict)


class IOSWeakNetManager:
    """管理 iOS Condition Inducer 弱网会话的生命周期。

    典型用法::

        IOSWeakNetManager.apply(udid, "3G-GoodNetwork")
        ...  # 采集期间保持弱网
        IOSWeakNetManager.clear(udid)
    """

    _sessions: dict[str, _Session] = {}
    _lock = threading.Lock()
    _READY_TIMEOUT = 20.0

    # ------------------------------------------------------------------
    # 只读查询
    # ------------------------------------------------------------------
    @classmethod
    def list_profiles(
        cls,
        udid: str,
        ios_major: int | None = None,
    ) -> list[dict[str, Any]]:
        """列出设备支持的网络类 Condition 及其子档位（同步）。

        Args:
            udid: 设备标识。
            ios_major: 已知 iOS 主版本；``None`` 时自动探测。

        Returns:
            List[Dict[str, Any]]: 每项含 ``identifier`` / ``name`` /
            ``is_destructive`` / ``profiles``。
        """
        _dev._require_pmd3()
        raw = _aio.run(cls._list_profiles_async(udid, ios_major))
        return [
            cls._normalize_condition(cond)
            for cond in raw
            if cls._is_network_condition(cond)
        ]

    @classmethod
    def status(cls, udid: str) -> dict[str, Any]:
        """查询设备当前弱网会话状态（同步）。

        Args:
            udid: 设备标识。

        Returns:
            Dict[str, Any]: 含 ``active`` 及（活动时）``profile_identifier``。
        """
        with cls._lock:
            session = cls._sessions.get(udid)
        if session is None:
            return {"engine": "ios_condition_inducer", "active": False}
        active = not session.task.done()
        return {
            "engine": "ios_condition_inducer",
            "active": active,
            "profile_identifier": session.profile_identifier,
            "error": session.error,
        }

    # ------------------------------------------------------------------
    # 应用 / 清除
    # ------------------------------------------------------------------
    @classmethod
    def apply(
        cls,
        udid: str,
        profile_identifier: str,
        ios_major: int | None = None,
    ) -> dict[str, Any]:
        """应用指定弱网档位，并在后台保持会话存活（同步）。

        Args:
            udid: 设备标识。
            profile_identifier: 子档位标识，如 ``"3G-GoodNetwork"``。
            ios_major: 已知 iOS 主版本；``None`` 时自动探测。

        Returns:
            Dict[str, Any]: 含 ``active`` / ``profile_identifier``。

        Raises:
            RuntimeError: 会话在超时内未能就绪（含底层错误信息）。
        """
        _dev._require_pmd3()
        cls.clear(udid)

        stop_event = asyncio.Event()
        ready: "concurrent.futures.Future[Any]" = concurrent.futures.Future()
        task = _aio.submit(
            cls._session_coro(
                udid, profile_identifier, stop_event, ready, ios_major
            )
        )
        session = _Session(
            udid=udid,
            profile_identifier=profile_identifier,
            stop_event=stop_event,
            task=task,
        )
        with cls._lock:
            cls._sessions[udid] = session

        try:
            ready.result(timeout=cls._READY_TIMEOUT)
        except concurrent.futures.TimeoutError:
            cls.clear(udid)
            raise RuntimeError("iOS 弱网会话启动超时")
        except Exception as exc:  # noqa: BLE001 - 底层错误原样上报
            session.error = str(exc)
            cls.clear(udid)
            raise RuntimeError(f"iOS 弱网应用失败：{exc}")

        return {
            "engine": "ios_condition_inducer",
            "active": True,
            "profile_identifier": profile_identifier,
        }

    @classmethod
    def clear(cls, udid: str) -> dict[str, Any]:
        """清除设备上的弱网条件并结束后台会话（同步）。

        Args:
            udid: 设备标识。

        Returns:
            Dict[str, Any]: 含 ``active=False``。
        """
        with cls._lock:
            session = cls._sessions.pop(udid, None)
        if session is not None:
            _aio.call_threadsafe(session.stop_event.set)
            try:
                session.task.result(timeout=cls._READY_TIMEOUT)
            except Exception:  # noqa: BLE001 - 清理等待失败不阻塞返回
                pass
        return {"engine": "ios_condition_inducer", "active": False}

    # ------------------------------------------------------------------
    # async 内核
    # ------------------------------------------------------------------
    @staticmethod
    async def _list_profiles_async(
        udid: str,
        ios_major: int | None,
    ) -> list[dict[str, Any]]:
        from pymobiledevice3.services.dvt.instruments.condition_inducer \
            import ConditionInducer

        async with _dev.dvt_session_async(
            udid, ios_major=ios_major
        ) as dvt:
            inducer = ConditionInducer(dvt)
            await inducer.connect()
            return await inducer.list()

    @staticmethod
    async def _session_coro(
        udid: str,
        profile_identifier: str,
        stop_event: asyncio.Event,
        ready: "concurrent.futures.Future[Any]",
        ios_major: int | None,
    ) -> None:
        """保活协程：设置条件 → 等待停止 → 恢复。"""
        from pymobiledevice3.services.dvt.instruments.condition_inducer \
            import ConditionInducer

        try:
            async with _dev.dvt_session_async(
                udid, ios_major=ios_major
            ) as dvt:
                inducer = ConditionInducer(dvt)
                await inducer.connect()
                await inducer.set(profile_identifier)
                if not ready.done():
                    ready.set_result(True)
                await stop_event.wait()
                try:
                    await inducer.clear()
                except Exception:  # noqa: BLE001 - 恢复失败不影响退出
                    pass
        except Exception as exc:  # noqa: BLE001 - 通过 ready 上报错误
            if not ready.done():
                ready.set_exception(exc)

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------
    @staticmethod
    def _is_network_condition(cond: dict[str, Any]) -> bool:
        """判断某个 Condition 是否与网络相关。"""
        text = " ".join(
            str(cond.get(key, "")).lower()
            for key in ("identifier", "name", "profilesSorted")
        )
        return any(hint in text for hint in _NETWORK_HINTS)

    @staticmethod
    def _normalize_condition(cond: dict[str, Any]) -> dict[str, Any]:
        """将底层 Condition 字典规整为稳定的对外结构。"""
        profiles = []
        for prof in cond.get("profiles", []) or []:
            if not isinstance(prof, dict):
                continue
            profiles.append({
                "identifier": prof.get("identifier"),
                "name": prof.get("name"),
                "description": prof.get("description"),
            })
        return {
            "identifier": cond.get("identifier"),
            "name": cond.get("name"),
            "is_destructive": bool(cond.get("isDestructive")),
            "profiles": profiles,
        }
