# 常见问题解答 (FAQ)

## 1️⃣ SoloX和Perfdog对比？

### 优势

* **功能更加丰富**: PK模式、设置执行时长、访问其他PC端的移动设备、丰富的本地化报告展现和分发
* **使用更加灵活**: 自定义部署、支持API收集更好的融入CI流程
* **免费开源**: 开源代码，如果不满足现在需求，可以自由二次开发（perfdog很贵，但是品质值得）

### 劣势

* **数据准确性**: perfdog采用的方式是安装一个监听app在测试设备上，用原生的API收集性能数据再返回给工具端，这种方式数据更准确（数据准确才是最重要的，条件允许建议使用perfdog）

## 2️⃣ 如何使用SoloX？

1. 点击Connect连接移动设备（第一次会自动连接，如果选择框显示了设备信息表示连接成功）
2. 选择需要测试的包名
3. 选择包名对应的进程（一个app有可能有多个进程，比如微信小程序，如果没有进程说明这个app没有在运行）
4. 点击Start开始收集性能指标
5. 点击Stop结束收集，生成报告跳转到报告管理页

## 3️⃣ 性能指标计算方法？

* **Android**: 详见 [Android平台技术实现](../04-user-guides/performance-monitoring.md#android-平台实现)
* **iOS**: 基于 [tidevice](https://github.com/alibaba/taobao-iphone-device) 实现

## 4️⃣ 为什么手机已经连接电脑，但是还是显示连接失败？

### Android设备
- 使用的是adb连接，solox自带有adb环境，但不一定适配每一台电脑
- 可以在自己的终端敲打 `adb devices` 测试是否连接上设备
- 参考：[Android设备连接问题](./troubleshooting.md#android-设备未识别)

### iOS设备
- 使用的是tidevice连接，如果连接失败可以参考官方文档
- 参考：[iOS设备连接问题](./troubleshooting.md#ios-设备连接失败)

## 5️⃣ 为什么Android的FPS经常会为0？

* **监控模式**: 支持SurfaceView和gfxinfo两种方式，可以切换尝试是否收集到数据
* **设置要求**: 如果使用gfxinfo方式需要到手机设置：开发者 → GPU渲染模式 → adb shell dumpsys gfxinfo
* **界面状态**: 界面相对静止的fps预期就是0，请检查页面是否滑动和动态
* **游戏兼容**: 已支持主流游戏引擎 (Unity, UE4/5, Cocos2d-x/Creator, Laya)。游戏应用会自动检测引擎类型并切换到 SurfaceView 模式采集 FPS，无论用户选择哪种模式。如果游戏 FPS 仍为 0，请确认：
  - 游戏已在前台运行且画面有动态更新
  - 设备通过 `adb devices` 可正常识别
  - 尝试手动选择 SurfaceView 模式

## 6️⃣ 为什么"python -m solox"会运行失败？

### 版本要求
- **Python版本**: solox 2.5.4及以上版本只支持python 3.10+的版本
- **低版本支持**: 2.5.3及以下版本支持python 3.0~3.9

### 端口问题
- **端口占用**: 如果显示50003端口被占用，可以用自定义方式启动：`python -m solox --host={ip} --port={port}`

### 网络问题
- **DNS错误**: `socket.gaierror: [Errno 8] nodename nor servname provided, or not known`
- **解决方案**: 参考 [GitHub Issue #198](https://github.com/smart-test-ti/SoloX/issues/198)

## 7️⃣ 为什么感觉收集速度慢？

### 性能因素
* **并发收集**: 界面收集每个指标都会起一个进程来达到同时收集的目的
* **计算复杂度**: 不同指标计算复杂度决定了速度，比如cpu计算+读取数据的时间最少是3秒，而电池的数据基本不需要计算就是秒回

### 优化建议
* **选择性监控**: 可以勾选掉部分指标，达到加快速度的效果
* **使用API**: 使用python API收集，会比界面的速度有明显的提升

## 8️⃣ 如何无线连接设备？

### Android设备
- PC和移动设备需要在同一个网络
- 通过adb connect的方式设置成功后，无需USB连接
- 在solox界面点击connect就会看到设备
- 具体方式可以网上查找相关教程

### iOS设备
- 目前不支持无线连接

## 9️⃣ 如何部署SoloX？

### 核心思路
让 `python -m solox` 这条命令在后台执行即可

### 部署方式
- **简单方式**: `nohup python -m solox &`
- **Docker部署**: 参考 [部署指南](../03-deployment/deployment-guide.md)
- **其他方式**: Gunicorn、systemd等

## 1️⃣0️⃣ SoloX部署在云机器，远程访问本地的移动设备？

### 配置步骤
1. 在连接移动设备的PC机器起solox的服务
2. 将host配置在SoloX设置页的Agent中（右上角红点的设置按钮可查看）

### 网络要求
- 可以不用在同一个局域网
- 要保证本地的网络防火墙是放开的，可以让云机器访问

## 1️⃣1️⃣ SoloX如何获取微信小程序的性能？

在进程选择框中找到appbrand开头的进程就是小程序的，选中该进程点击Start即可收集。

## 1️⃣2️⃣ Start-up Time如何使用？

### Android启动时间测试
1. 首先打开目标app的启动到达界面
2. 接着在Start-up Time弹窗点击按钮"Get current activity"
3. **热启动测试**: 直接点Start按钮
4. **冷启动测试**: 杀掉app点击Start按钮

### iOS启动时间测试
- 事先要装好模块：`pip install py-ios-device`
- 然后点击Start（由于windows安装会报错，解决繁琐，solox没有自带该模块）

## 1️⃣3️⃣ 为什么分析页截图会出现明显的遮层？

这个和浏览器有关，调用的是浏览器的截图功能。

## 1️⃣4️⃣ 分析页显示流量数据汇总值和Chart图中有出入？

### 数据说明
- **汇总数据**: 头部汇总的数据是根据记录结束和开始数据的差值得到的
- **图表数据**: chart中的数据也是准确的，表示的是记录那一秒的流量损耗
- **差异原因**: 不是每一秒都有记录，所以用chart中相加的话会少于实际总损耗

## 1️⃣5️⃣ 为什么Android和iOS的电池统计指标不一致？

### Android电池监控
- 基本上新版本的系统已经不能通过adb的方式拿到能耗数据了
- 目前提供电量和温度两个指标其实已经足够
- 电量收集时solox会在执行前断开充电，执行结束才恢复充电

### iOS电池监控
- 选择能耗的方式来评估性能
- 测试是要和竞品对比，在相同条件下对比能耗即可，无需关注充电的影响

## 1️⃣6️⃣ 如果iOS收集不到数据显示tidevice报错，怎么解决？

### 常见解决方案
1. **重新连接**: 插拔USB重新连接，多次尝试
2. **更换设备**: tidevice还是有一定的兼容性问题
3. **版本检查**: 检查tidevice的版本，不能自己安装最新版本，只能用solox自带的
4. **支持包**: 如果日志中提示支持包下载失败，可以自行到 [iOSDeviceSupport](https://github.com/filsv/iOSDeviceSupport) 下载放到路径 `~/.tidevice/device-support/`

## 1️⃣7️⃣ 为什么Android不支持收集GPU数据？

目前只支持部分高通芯片的设备（小米、OPPO、vivo等品牌较多支持）。

## 1️⃣8️⃣ 如何在收集过程中录制APP的屏幕？

### Android屏幕录制
- **界面收集**: 在首页打开"Record Screen"开关，点击Start开始收集数据并同时录制视频，结束后Report管理页会显示播放按钮
- **Python API收集**: 设置参数 `record=True`
- **Mac电脑**: 录制视频请检查Scrcpy是否安装成功，可以自行安装：`brew install scrcpy`

### iOS屏幕录制
SoloX **不支持 iOS 设备的视频录制**，这是 iOS 调试通道的能力边界，而非暂未实现：

- 非越狱设备上，Apple 官方调试通道（Instruments / usbmuxd）只提供**截图 / MJPEG 帧流**，不提供可直接落地的 H.264 视频录制接口。开源生态中的同类工具也是如此（例如 [go-ios](https://github.com/danielpaulus/go-ios) 的 `screenshot` 为截图或 MJPEG 流、[sonic-ios-bridge](https://github.com/SonicCloudOrg/sonic-ios-bridge) 的 `screenshoot` 同理）。
- 因此 SoloX iOS 侧仅具备**低频截图**能力（`iter_screenshot`），报告页不会出现 iOS 录屏播放按钮。
- 如需 iOS 屏幕**视频**录制，请使用系统级方案：
  - **Mac**: QuickTime Player → 文件 → 新建影片录制 → 选择已连接的 iOS 设备；
  - **iOS 自带**: 控制中心「屏幕录制」，录制后从设备导出。

## 1️⃣9️⃣ Android哪些指标依赖app的进程需要存活？

### 依赖进程的指标
- CPU、Memory、Network、FPS

### 进程选择说明
- 界面如果不选择进程就点击Start收集，那么默认使用的是这个包名的主进程
- 界面选择了app的某个进程收集，如果收集过程中将app杀掉，然后再恢复后自动使用的是主进程，有可能和你界面选择的进程不一致

## 2️⃣0️⃣ iOS 能做弱网测试吗？

SoloX 的**设备侧弱网注入目前仅支持 Android**（Root `tc netem` 或非 Root 的 QAS Network Agent VPN）。iOS 侧没有等价的设备侧注入，原因与可选路径如下：

### 当前推荐（手动，即刻可用）
1. 在被测 iPhone 安装 **Developer 描述文件**（通过 Xcode 连接一次即可开启「开发者」菜单）。
2. 打开 **设置 → 开发者 → Network Link Conditioner**，选择内置档位（100% Loss、High Latency DNS、Very Bad Network、3G、LTE 等）或自定义。
3. 在 SoloX 中正常连接该 iOS 设备并采集 —— 弱网由系统施加，SoloX 如实记录此期间的性能数据。

### 未来可选（程序化，尚未集成）
iOS 17+ 可通过 Instruments 的 **Condition Inducer** 服务在设备侧程序化启用网络/热状态条件（对应 [go-ios](https://github.com/danielpaulus/go-ios) 的 `ios devicestate enable`、[pymobiledevice3](https://github.com/doronz88/pymobiledevice3) 的 `developer dvt condition`）。SoloX 暂未集成，原因：

- 现有 iOS 链路锁定在 `tidevice==0.9.7`，**不含** Condition Inducer 与 iOS 17+ 的 RemoteXPC 隧道能力；
- iOS 17+ 需 `sudo` 启动隧道守护进程（Windows 还需 `wintun.dll`），部署成本高；
- 许可证约束：SoloX 为 **MIT**，可移植 **MIT** 的 go-ios 思路/代码（需署名），但**不可**将 **GPL-3.0** 的 pymobiledevice3、**AGPL-3.0** 的 sonic-ios-bridge 源码并入本仓库。

详见 [docs/plans/2026-07-11-ios-gap-and-oss-survey.md](../plans/2026-07-11-ios-gap-and-oss-survey.md)。

## 2️⃣1️⃣ Android/iOS最高支持的系统版本？

### 系统版本支持
- **Android**: 6.0+
- **iOS**: 参考 [iOSDeviceSupport](https://github.com/filsv/iOSDeviceSupport)，这个路径有的都支持

### iOS支持包
- 因为是外网可能会下载失败
- 可以自行下载支持包放在本地 `~/.tidevice/device-support/`

---

*相关文档: [故障排除](./troubleshooting.md) • [贡献指南](./contribution-guide.md)*
