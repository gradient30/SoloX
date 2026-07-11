# -*- coding: utf-8 -*-
"""iOS 截图与录屏（C）。

能力与边界（诚实说明）：

    - **单帧截图**：经 lockdown ``com.apple.mobile.screenshotr`` 服务，全 iOS
      版本可用，无需隧道，稳定可靠。
    - **录屏**：iOS 未开放可直接抓取的 H.264 视频流。本模块采用**截图序列
      → ffmpeg 合成 mp4** 的务实方案。受 screenshotr 吞吐限制，实际帧率通常
      仅数帧/秒，适合"操作留证/低频回放"，**不等价于高帧率录屏**。

pymobiledevice3 9.x 的截图 API 为 ``async``；本模块提供 async 内核与同步门面。
mp4 合成额外依赖 ffmpeg（复用 SoloX 既有查找逻辑）。
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import subprocess
import tempfile
from typing import Any

from solox.public.ios_ext import _aio
from solox.public.ios_ext import device as _dev


# ---------------------------------------------------------------------------
# async 内核
# ---------------------------------------------------------------------------
async def _open_screenshot_service(udid: str) -> tuple[Any, Any]:
    """创建 lockdown 与 screenshotr 服务（调用方负责关闭）。"""
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.screenshot import ScreenshotService

    lockdown = await create_using_usbmux(serial=udid)
    service = ScreenshotService(lockdown=lockdown)
    return service, lockdown


async def _take_screenshot_async(udid: str) -> bytes:
    service, lockdown = await _open_screenshot_service(udid)
    try:
        return await service.take_screenshot()
    finally:
        await _aio.aclose(service)
        await _aio.aclose(lockdown)


# ---------------------------------------------------------------------------
# 同步门面：截图
# ---------------------------------------------------------------------------
def take_screenshot(udid: str) -> bytes:
    """抓取一帧屏幕截图（PNG 字节流，同步）。

    Args:
        udid: 设备标识。

    Returns:
        bytes: PNG 图像字节。

    Raises:
        IOSBackendUnavailable: pymobiledevice3 未安装时。
    """
    _dev._require_pmd3()
    return _aio.run(_take_screenshot_async(udid))


def save_screenshot(udid: str, out_path: str) -> str:
    """抓取并保存一帧截图到磁盘。

    Args:
        udid: 设备标识。
        out_path: 目标 PNG 文件路径。

    Returns:
        str: 实际写入的文件路径。
    """
    data = take_screenshot(udid)
    directory = os.path.dirname(os.path.abspath(out_path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(out_path, "wb") as handle:
        handle.write(data)
    return out_path


def _find_ffmpeg() -> str:
    """复用 SoloX 既有 ffmpeg 查找逻辑。

    Returns:
        str: ffmpeg 可执行路径；未找到返回空串。
    """
    try:
        from solox.public.common import Scrcpy

        return Scrcpy._find_ffmpeg_binary() or ""
    except Exception:  # noqa: BLE001 - 回退到 PATH 查找
        import shutil

        return shutil.which("ffmpeg") or ""


class ScreenRecorder:
    """iOS 截图序列录制器（共享事件循环抓帧 → 停止时 ffmpeg 合成 mp4）。

    Attributes:
        udid: 设备标识。
        fps: 目标抓帧帧率（受 screenshotr 吞吐限制，实际可能更低）。
        output_path: 最终 mp4 输出路径。
    """

    def __init__(
        self,
        udid: str,
        output_path: str,
        fps: int = 2,
        frames_dir: str | None = None,
    ) -> None:
        """初始化录制器。

        Args:
            udid: 设备标识。
            output_path: 最终 mp4 输出路径。
            fps: 目标帧率，默认 2（务实值，避免过度请求截图服务）。
            frames_dir: 帧缓存目录；``None`` 时使用临时目录。
        """
        self.udid = udid
        self.output_path = output_path
        self.fps = max(1, int(fps))
        self._frames_dir = frames_dir
        self._stop_event: asyncio.Event | None = None
        self._task: "concurrent.futures.Future[Any] | None" = None
        self._frame_count = 0
        self._error: str | None = None

    def start(self) -> None:
        """启动抓帧协程（调度到共享事件循环）。"""
        _dev._require_pmd3()
        if self._task is not None and not self._task.done():
            return
        if self._frames_dir is None:
            self._frames_dir = tempfile.mkdtemp(prefix="solox-ios-rec-")
        os.makedirs(self._frames_dir, exist_ok=True)
        self._frame_count = 0
        self._error = None
        self._stop_event = asyncio.Event()
        self._task = _aio.submit(self._capture_coro())

    def stop(self, assemble: bool = True) -> dict[str, Any]:
        """停止抓帧，并（可选）合成 mp4。

        Args:
            assemble: 是否用 ffmpeg 合成 mp4；``False`` 则仅保留帧。

        Returns:
            Dict[str, Any]: 含 ``frames`` / ``output`` / ``assembled`` /
            ``error``。
        """
        if self._stop_event is not None:
            _aio.call_threadsafe(self._stop_event.set)
        if self._task is not None:
            try:
                self._task.result(timeout=30)
            except Exception as exc:  # noqa: BLE001 - 抓帧异常如实记录
                self._error = self._error or str(exc)
        result: dict[str, Any] = {
            "frames": self._frame_count,
            "output": None,
            "assembled": False,
            "error": self._error,
        }
        if assemble and self._frame_count > 0 and not self._error:
            try:
                self._assemble()
                result["output"] = self.output_path
                result["assembled"] = True
            except Exception as exc:  # noqa: BLE001 - 合成失败如实返回
                result["error"] = str(exc)
        return result

    async def _capture_coro(self) -> None:
        """抓帧协程：按目标帧率抓取截图并编号落盘。"""
        interval = 1.0 / self.fps
        service = None
        lockdown = None
        try:
            service, lockdown = await _open_screenshot_service(self.udid)
            while not self._stop_event.is_set():
                data = await service.take_screenshot()
                frame_path = os.path.join(
                    self._frames_dir,
                    f"frame_{self._frame_count:06d}.png",
                )
                with open(frame_path, "wb") as handle:
                    handle.write(data)
                self._frame_count += 1
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(), timeout=interval
                    )
                except asyncio.TimeoutError:
                    pass
        except Exception as exc:  # noqa: BLE001 - 记录错误供 stop 读取
            self._error = str(exc)
        finally:
            if service is not None:
                await _aio.aclose(service)
            if lockdown is not None:
                await _aio.aclose(lockdown)

    def _assemble(self) -> None:
        """用 ffmpeg 将截图序列合成为浏览器可播放的 mp4。

        Raises:
            RuntimeError: 未找到 ffmpeg 或合成失败时。
        """
        ffmpeg = _find_ffmpeg()
        if not ffmpeg:
            raise RuntimeError(
                "未找到 ffmpeg，无法合成 mp4；请安装 ffmpeg 或设置 "
                "SOLOX_FFMPEG"
            )
        out_dir = os.path.dirname(os.path.abspath(self.output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        pattern = os.path.join(self._frames_dir, "frame_%06d.png")
        cmd = [
            ffmpeg,
            "-y",
            "-framerate",
            str(self.fps),
            "-i",
            pattern,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            self.output_path,
        ]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "ffmpeg 合成失败：%s"
                % proc.stderr.decode("utf-8", "ignore")[-500:]
            )
