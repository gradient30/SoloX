# 常见问题

## 1. SoloX 与 Perfdog 对比

### 优势

- 功能更加丰富：PK模式、设置执行时长、访问其他PC端的移动设备、丰富的本地化报告展现和分发
- 使用更加灵活：自定义部署、支持 API 收集更好的融入 CI 流程
- 免费：开源代码，如果不满足你现在需求，可以自由二次开发（perfdog 很贵，但是品质值得）

### 劣势

- 数据准确性不足：perfdog 采用的方式是安装一个监听 app 在测试设备上，用原生的 api 收集性能数据再返回给工具端，这种方式肯定是更靠谱的（数据准确才是最重要的，条件允许我建议使用 perfdog）

## 2. 连接问题

### 2.1 手机已连接电脑但显示连接失败

#### Android

使用的是 ADB 连接，solox 自带有 ADB 环境，但不一定适配每一台电脑；可以在自己的终端敲打 `adb devices` 测试是否连接上设备。

#### iOS

使用的是 tidevice 连接，如果连接失败可以参考官方文档：https://github.com/alibaba/taobao-iphone-device

### 2.2 iOS 收集不到数据显示 tidevice 报错

1. 插拔 USB 重新连接，多次尝试
2. 更换设备，tidevice 还是有一定的兼容性
3. 检查 tidevice 的版本，不能自己安装最新版本，只能用 solox 自带的，因为部分代码二次开发过
4. 如果日志中提示是支持包下载失败，可以自行到 https://github.com/filsv/iOSDeviceSupport 下载并放到路径 `~/.tidevice/device-support/`

## 3. 数据收集问题

### 3.1 Android 的 FPS 经常为 0

1. 支持 SurfaceView 和 gfxinfo（界面关闭 surfaceview 开关切换）两种方式，可以都切换尝试是否收集到数据
2. 界面相对静止的 fps 预期就是 0，请检查页面是否滑动和动态
3. 游戏类的 APP 大部分机器不支持，多使用华为的机器

### 3.2 Android 不支持收集 GPU 数据

目前只支持部分高通芯片的设备（小米、oppo、vivo 多点）

### 3.3 分析页显示流量数据汇总值和 Chart 图中有出入

头部汇总的数据是根据记录结束和开始数据的差值得到的，chart 中的数据也是准确的，表示的是记录那一秒的流量损耗，但不是每一秒都有记录，所以用 chart 中相加的话会少于实际总损耗

## 4. 启动和运行问题

### 4.1 `python -m solox` 运行失败

1. solox 2.5.4 及以上版本只支持 python 3.10+ 的版本（因为使用了 python 新的特性，3.10 以下版本不支持），2.5.3 及以下版本支持 python3.0 ~3.9
2. 如果显示的是 50003 端口被占用，可以用自定义的方式启动: `python -m solox --host={ip} --port={port}`
3. socket.gaierror: [Errno 8] nodename nor servname provided, or not known: https://github.com/smart-test-ti/SoloX/issues/198

### 4.2 收集速度慢

1. 界面收集每个指标都会起一个进程来达到同时收集的目的；基本上 PC 的配置跟的上，速度没有太大问题；但是不同指标计算复杂度决定了速度，比如 cpu 计算+读取数据的时间最少是 3 秒，而电池的数据基本不需要计算就是秒回
2. 可以在勾选掉部分指标，也会达到加快速度的效果
3. 使用 python api 收集，会比界面的速度有明显的提升

## 5. 兼容性问题

### 5.1 支持的系统版本

- **Android**: 6.0+
- **iOS**: 参见 https://github.com/filsv/iOSDeviceSupport，这个路径有的都支持，因为是外网可能会下载失败，可以自行下载支持包放在本地 `~/.tidevice/device-support/`

### 5.2 Windows 系统编码问题

确保 Windows 系统支持 UTF-8：
1. 打开"控制面板" -> "区域" -> "管理" -> "更改系统区域设置"
2. 勾选"Beta版：使用 Unicode UTF-8 提供全球语言支持"
3. 重启计算机

## 6. 功能使用问题

### 6.1 无线连接设备

#### Android

PC 和移动设备需要在同一个网络，然后通过 `adb connect` 的方式设置成功后，无须 USB 连接在 solox 界面点击 connect 就会看到设备；具体方式可以网上查，很多教程。

#### iOS

不支持无线连接。

### 6.2 屏幕录制

目前支持 Android 端：

1. 界面收集：在首页打开"Record Screen"开关，点击 Start 开始收集数据并同时录制视频，结束后 Report 管理页会显示播放按钮
2. Python API 收集：record=True
3. Mac 电脑录制视频，请检查 Scrcpy 是否安装成功，可以自行安装：`brew install scrcpy`

### 6.3 Start-up Time 使用

#### Android

首先打开目标 app 的启动到达界面，接着在 Start-up Time 弹窗点击按钮"Get current activity"。如果要测试热启动就直接点 Start 按钮，如果测试冷启动就杀掉 app 点击 Start 按钮。

#### iOS

事先要装好模块 `pip install py-ios-device`，然后点击 Start（由于 windows 安装会报错，解决繁琐，solox 没有自带该模块）。

### 6.4 微信小程序性能获取

在进程选择框中找到 appbrand 开头的进程就是小程序的，选中该进程点击 Start 即可收集。

## 7. Android 指标依赖说明

以下指标依赖 app 的进程需要存活：
- CPU
- Memory
- Network
- FPS

界面如果不选择进程就点击 Start 收集，那么默认使用的是这个包名的主进程。

界面选择了 app 的某个进程收集，如果收集过程中将 app 杀掉，然后再恢复后自动使用的是主进程，有可能和你界面选择的进程不一致。

## 8. 电池统计指标不一致

### Android

基本上新版本的系统已经不能通过 adb 的方式拿到能耗数据了，目前提供电量和温度两个指标其实已经足够；电量收集时 solox 会在执行前断开充电，执行结束才恢复充电。

### iOS

选择能耗的方式来评估性能，这里可能会觉得充电会影响，但是我们测试是要和竞品对比，在相同条件下对比能耗即可，无需关注充电的影响。

## 9. 分析页截图问题

分析页截图会出现明显的遮层，这和浏览器有关，调用的是浏览器的截图功能。