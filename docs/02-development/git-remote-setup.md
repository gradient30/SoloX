# Git 远程协作（Fork 工作流）

> 面向公开发布仓库 [smart-test-ti/SoloX](https://github.com/smart-test-ti/SoloX)。请勿在文档或脚本中硬编码个人 fork 地址。

## 克隆与安装

```bash
git clone https://github.com/smart-test-ti/SoloX.git
cd SoloX
pip install -e ".[dev,test]"
bash scripts/release_gate.sh   # 或 .\scripts\release_gate.ps1
```

## 贡献者 Fork 流程

```bash
# 1. 在 GitHub 上 Fork 仓库到个人账户
# 2. 克隆你的 Fork
git clone https://github.com/YOUR_USERNAME/SoloX.git
cd SoloX

# 3. 添加上游
git remote add upstream https://github.com/smart-test-ti/SoloX.git
git remote -v

# 4. 同步主分支
git fetch upstream
git checkout main
git merge upstream/main

# 5. 功能分支
git checkout -b feature/your-topic
# ... 开发 ...
git push -u origin feature/your-topic
# 在 GitHub 上向上游提 Pull Request
```

## 提交身份（仓库级，勿用 --global 覆盖他人环境）

```bash
git config user.email "you@example.com"
git config user.name "Your Name"
```

## UTF-8 / 中文提交

```bash
git config core.quotepath off
git config i18n.commitEncoding utf-8
git config i18n.logOutputEncoding utf-8
```

PowerShell 会话建议：

```powershell
chcp 65001
$env:LC_ALL = "zh_CN.UTF-8"
```

---

*详见 [贡献指南](../05-issues/contribution-guide.md)*
