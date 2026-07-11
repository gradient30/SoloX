# -*- coding: utf-8 -*-
"""异步→同步桥接层。

pymobiledevice3 9.x 的绝大多数 API 是 ``async``，而 SoloX（Flask）是同步的。
本模块维护**一个常驻后台事件循环线程**，把协程调度到该循环上执行，并向同步
世界暴露阻塞式 :func:`run` 与非阻塞式 :func:`submit`。

统一使用同一个循环，确保 pymobiledevice3 创建的连接对象在其整个生命周期内都
运行在同一事件循环中（跨循环使用会导致连接不可用）。
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import threading
from typing import Any, Awaitable, Callable, TypeVar

_T = TypeVar("_T")

_loop: asyncio.AbstractEventLoop | None = None
_thread: threading.Thread | None = None
_lock = threading.Lock()


def get_loop() -> asyncio.AbstractEventLoop:
    """返回（必要时惰性创建并启动）常驻后台事件循环。

    Returns:
        asyncio.AbstractEventLoop: 正在后台线程中运行的事件循环。
    """
    global _loop, _thread
    with _lock:
        if _loop is not None and _loop.is_running():
            return _loop
        loop = asyncio.new_event_loop()
        thread = threading.Thread(
            target=loop.run_forever,
            name="ios-ext-aio",
            daemon=True,
        )
        thread.start()
        _loop = loop
        _thread = thread
        return loop


def run(coro: Awaitable[_T], timeout: float | None = None) -> _T:
    """在后台事件循环上阻塞式执行一个协程并返回其结果。

    Args:
        coro: 待执行的协程/可等待对象。
        timeout: 最长等待秒数；``None`` 表示不限。

    Returns:
        协程的返回值。

    Raises:
        Exception: 协程内部抛出的任何异常将原样传播。
    """
    loop = get_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout)


def submit(coro: Awaitable[_T]) -> "concurrent.futures.Future[_T]":
    """把协程调度到后台循环，立即返回 Future（不阻塞）。

    用于需要持续存活的会话（如弱网保活、录屏抓帧循环）。

    Args:
        coro: 待执行的协程。

    Returns:
        concurrent.futures.Future: 可用于等待/取消的跨线程 Future。
    """
    loop = get_loop()
    return asyncio.run_coroutine_threadsafe(coro, loop)


def call_threadsafe(callback: Callable[..., Any], *args: Any) -> None:
    """线程安全地把一个回调投递到事件循环执行（如设置 asyncio.Event）。

    Args:
        callback: 在循环线程中调用的可调用对象。
        *args: 传给回调的位置参数。
    """
    loop = get_loop()
    loop.call_soon_threadsafe(callback, *args)


async def aclose(obj: Any) -> None:
    """尽量健壮地关闭一个连接对象（兼容同步/异步 close）。

    Args:
        obj: 具备 ``aclose``/``close`` 的连接对象。
    """
    for name in ("aclose", "close"):
        method = getattr(obj, name, None)
        if method is None:
            continue
        try:
            result = method()
            if asyncio.iscoroutine(result):
                await result
        except Exception:  # noqa: BLE001 - 关闭失败不应影响主流程
            pass
        return
