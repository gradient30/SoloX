## 默认已配置"文件"-"设置"-"版本控制"-"github"-"添加对应github授权"

#### 0. 快速拉取远程仓库
git pull https://github.com/gradient30/SoloX.git

#### 1. 检查当前仓库/远程配置
git branch -v
git remote -v

#### 2. 添加远程仓库（如果尚未添加）
git remote add gradient30 https://github.com/gradient30/SoloX.git

#### 3. 拉取最新代码
git pull gradient30 master

#### 4. 创建并切换到新分支
git checkout -b solox-gemini

#### 5. 推送到远程（单个/或推送所有）
git push -u gradient30 solox-gemini
git push --all origin

#### 6.设置全局提交身份
git config --global user.email "gradi@example.com"
git config --global user.name "Gradi"

#### 7. 验证是否生效了
git config user.email
git config user.name

#### 8. 提交代码到远程仓库
git add .
git commit -m "fix: 修复中文乱码的问题"

#### 9. 同步效果
远程仓库会完全镜像你推送的本地分支结构
其他协作者可以通过 git fetch --all 获取这些新分支。


### 1. Git编码配置
为解决Git中的乱码问题，需要进行以下配置：
1. Git 配置（全局设置
`
git config --global core.quotepath off
git config --global i18n.commitencoding utf-8
git config --global i18n.logoutputencoding utf-8
git config --global i18n.commitcharset utf-8

`
2. PowerShell 编码设置
chcp 65001
$env:LC_ALL="zh_CN.UTF-8"

3.打开 PowerShell 配置文件（如果没有则创建）
notepad $PROFILE
添加如下内容：
chcp 65001
$env:LC_ALL="zh_CN.UTF-8"

4.Windows 系统设置
确保 Windows 系统支持 UTF-8：
打开"控制面板" -> "区域" -> "管理" -> "更改系统区域设置"
勾选"Beta版：使用 Unicode UTF-8 提供全球语言支持"
重启计算机
