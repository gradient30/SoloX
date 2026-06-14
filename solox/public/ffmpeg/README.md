# ffmpeg（可选内置）

录屏 MKV → MP4 无损封装依赖 **ffmpeg**。仓库不提交二进制（体积约 300MB），请在本机或发布打包时自行放置。

## 查找顺序

1. 环境变量 `SOLOX_FFMPEG`（指向 `ffmpeg` 或 `ffmpeg.exe`）
2. 本目录 `bin/ffmpeg`（Windows: `bin/ffmpeg.exe`）
3. 系统 `PATH` 中的 `ffmpeg`

未找到时 `/apm/record/start` 会失败并提示安装路径。

## Windows 本地安装

1. 从 [gyan.dev ffmpeg builds](https://www.gyan.dev/ffmpeg/builds/) 下载 **release essentials** zip
2. 解压后将 `bin/ffmpeg.exe`、`bin/ffprobe.exe` 放入 `solox/public/ffmpeg/bin/`
3. 或设置：`set SOLOX_FFMPEG=C:\path\to\ffmpeg.exe`

## 发布打包

`MANIFEST.in` / `pyproject.toml` 已包含 `public/ffmpeg/**/*`；发版前在构建机放入对应平台二进制后再 `python -m build`。

## 许可

ffmpeg 为 LGPL/GPL。随 SoloX 分发时请保留上游 LICENSE 并遵守相应条款。
