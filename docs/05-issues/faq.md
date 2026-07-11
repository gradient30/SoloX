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

- **数据源**：Android GPU **利用率(busy%)** 读自高通 Adreno 的 `/sys/class/kgsl/kgsl-3d0/gpubusy`。该节点在多数**未 root** 设备上被 SELinux 拒绝读取（`Permission denied`），因此只有**部分已 root 或该节点对 shell 可读**的高通机型（小米、OPPO、vivo 等较多）能取到数据。
- **诚实性行为（重要）**：当读取失败/无权限时，SoloX **返回 `gpu: null` 并置 `gpu_supported=false`**（前端会提示一次"GPU 利用率不可用"），**不再伪造 `gpu: 0`**——0 会误导用户以为"GPU 空闲"。
- **`dumpsys gfxinfo` 能替代吗？不能。** gfxinfo 提供的是 **HWUI（Android View 层）单帧的 GPU 绘制耗时(ms)** 与 **HWUI 显存**，**不是 GPU 利用率**；且对使用 SurfaceView 的游戏（Unity/UE/Cocos 等），gfxinfo 只统计到很薄的 Android View 层，**看不到游戏 GL 的真实渲染**。实测某 Cocos 游戏 gfxinfo 仅记录到 148 帧、GPU 显存 9.28KB，与游戏真实渲染（SurfaceFlinger 测得 61fps）完全不对应。故 gfxinfo 不作为 GPU 利用率的替代来源。
- **Mali/其它 GPU**：非高通芯片暂无统一的免 root 利用率来源，同样如实标注不支持。

## 1️⃣7️⃣.1 CPU 占用率是怎么算的？为什么和 top / PerfDog 数值对不上？

- SoloX 的 App CPU% 口径为 **100% = 全机所有核心满载**（进程 CPU 时间增量 ÷ 全部核心 CPU 时间增量之和）。例如 8 核机上单核跑满 ≈ 12.5%。
- `top` / PerfDog 常用 **100% = 单核** 口径（单核跑满=100%，多核可 >100%）。
- **换算**：SoloX 的 App CPU% × 核数 ≈ 单核口径数值。真机核对显示：SoloX app% × 核数 ≈ `dumpsys cpuinfo` 各核百分比之和，两者一致，只是分母不同。

## 1️⃣7️⃣.2 Network 流量是"仅该 App"的吗？

- Android 侧流量读自 `/proc/<pid>/net/dev`（`wlan0`/`rmnet_ipa0`）。该文件是**网络命名空间级**统计，而普通 App 共享默认命名空间，因此读到的是**采集窗口内本机该网卡的总流量**，并非严格"仅该 App"。
- 当被测 App 是前台主要流量来源时，可近似其流量；若后台有其它 App 大量联网，会一并计入。
- 严格 App 级流量需 **UID 级统计**（Android 10+ 走 eBPF，通常需 root），本项目未采用，如实以命名空间级口径记录。

## 1️⃣8️⃣ 如何在收集过程中录制APP的屏幕？

### Android屏幕录制
- **界面收集**: 在首页打开"Record Screen"开关，点击Start开始收集数据并同时录制视频，结束后Report管理页会显示播放按钮
- **Python API收集**: 设置参数 `record=True`
- **Mac电脑**: 录制视频请检查Scrcpy是否安装成功，可以自行安装：`brew install scrcpy`

### iOS屏幕录制
iOS 官方调试通道（Instruments / usbmuxd）**不提供可直接落地的 H.264 视频录制接口**，只提供**截图 / MJPEG 帧流**。因此 SoloX 的 iOS 录屏采用**截图序列 → ffmpeg 合成 mp4** 的务实方案，受 screenshotr 吞吐限制，实际帧率通常仅数帧/秒，适合「操作留证/低频回放」，**不等价于高帧率录屏**。

- **可选后端（个人自用）**：安装 `pip install "solox[ios]"`（引入 pymobiledevice3）后，可用：
  - `GET /apm/ios/screenshot?device=<udid>` —— 单帧截图（经 lockdown screenshotr，全 iOS 版本可用，无需隧道）；
  - `solox.public.ios_ext.screen.ScreenRecorder` —— 截图序列录制并用 ffmpeg 合成 mp4。
- **真机验收待定**：以上代码已落地并有 mock 单测，但抓帧帧率/清晰度需 iOS 真机端到端验证。
- 如需高帧率 iOS 屏幕**视频**录制，仍建议系统级方案：
  - **Mac**: QuickTime Player → 文件 → 新建影片录制 → 选择已连接的 iOS 设备；
  - **iOS 自带**: 控制中心「屏幕录制」，录制后从设备导出。
- 许可证提示：pymobiledevice3 为 **GPL-3.0**，仅在**个人、非商业、纯本地、不对外分发**前提下作为可选依赖使用（见 [docs/plans/2026-07-11-ios-pmd3-backend.md](../plans/2026-07-11-ios-pmd3-backend.md)）。

## 1️⃣9️⃣ Android哪些指标依赖app的进程需要存活？

### 依赖进程的指标
- CPU、Memory、Network、FPS

### 进程选择说明
- 界面如果不选择进程就点击Start收集，那么默认使用的是这个包名的主进程
- 界面选择了app的某个进程收集，如果收集过程中将app杀掉，然后再恢复后自动使用的是主进程，有可能和你界面选择的进程不一致

## 2️⃣0️⃣ iOS 能做弱网测试吗？

**Android** 用 Root `tc netem` 或非 Root 的 QAS Network Agent VPN 做设备侧注入。**iOS** 现提供两条路径：

### 手动（无需额外依赖，即刻可用）
1. 在被测 iPhone 安装 **Developer 描述文件**（通过 Xcode 连接一次即可开启「开发者」菜单）。
2. 打开 **设置 → 开发者 → Network Link Conditioner**，选择内置档位（100% Loss、High Latency DNS、Very Bad Network、3G、LTE 等）或自定义。
3. 在 SoloX 中正常连接该 iOS 设备并采集 —— 弱网由系统施加，SoloX 如实记录此期间的性能数据。

### 程序化（可选后端，个人自用）
安装 `pip install "solox[ios]"` 后，SoloX 可经 Instruments 的 **Condition Inducer** 在设备侧程序化启停网络条件：

- `GET /apm/weaknet/ios/profiles?device=<udid>` —— 列出可用档位；
- `GET /apm/weaknet/apply?platform=iOS&device=<udid>&preset=<profile_id>` —— 应用档位；
- `GET /apm/weaknet/clear?platform=iOS&device=<udid>` —— 恢复。

注意：Condition Inducer 的条件**仅在会话保持期间生效**，SoloX 用后台会话保活，收到 clear 后自动恢复。

- **真机验收待定**：代码已落地并有 mock 单测；iOS 17+ 需 `sudo pymobiledevice3 remote tunneld` 隧道守护进程（Windows 还需 `wintun.dll`），各档位实际生效需真机验证。
- 许可证提示：pymobiledevice3 为 **GPL-3.0**，仅在**个人、非商业、纯本地、不对外分发**前提下使用。

详见 [docs/plans/2026-07-11-ios-pmd3-backend.md](../plans/2026-07-11-ios-pmd3-backend.md) 与 [docs/plans/2026-07-11-ios-gap-and-oss-survey.md](../plans/2026-07-11-ios-gap-and-oss-survey.md)。

## 2️⃣1️⃣ Android/iOS最高支持的系统版本？

### 系统版本支持
- **Android**: 6.0+
- **iOS**: 参考 [iOSDeviceSupport](https://github.com/filsv/iOSDeviceSupport)，这个路径有的都支持

### iOS支持包
- 因为是外网可能会下载失败
- 可以自行下载支持包放在本地 `~/.tidevice/device-support/`

## 2️⃣2️⃣ iOS 有真实 Jank（卡顿）吗？

- **默认 FPS 通道**：iOS 经 Instruments opengl 采样器只给**聚合帧率标量**，无逐帧时戳，因此**默认不计算 iOS Jank**（接口按 `jank_supported=false` 如实标注）。
- **实验后端（个人自用）**：安装 `pip install "solox[ios]"` 后，可经 **CoreProfileSessionTap**（内核 kdebug 追踪）提取逐帧呈现时间，再复用与 Android **完全一致**的 PerfDog 抖动定义计算 Jank：
  - `GET /apm/ios/jank?device=<udid>&duration=10`
- **真机标定待定**：kdebug 中「帧呈现」对应的 trace code 随 iOS 版本/图形栈变化，需在真机上用 `get_trace_codes()` 核对后传入匹配器；未命中时接口如实返回 `supported=false` 并提示需标定，**绝不臆造 Jank 数据**。
- 需 iOS 17+ 时同样依赖 `sudo pymobiledevice3 remote tunneld` 隧道守护进程。详见 [docs/plans/2026-07-11-ios-pmd3-backend.md](../plans/2026-07-11-ios-pmd3-backend.md)。

---

*相关文档: [故障排除](./troubleshooting.md) • [贡献指南](./contribution-guide.md)*
