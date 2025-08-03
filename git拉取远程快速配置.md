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

#### 7. 设置Git编码配置（解决中文乱码问题）

git config --global core.quotepath off
git config --global i18n.commitcharset utf-8
git config --global i18n.logoutputencoding utf-8

---

- 永久解决 PowerShell 中文输入问题，建议在 PowerShell 配置文件中添加编码设置
- echo $PROFILE
- 如果文件不存在，创建该文件，并添加以下内容
- $OutputEncoding = New-Object -typename System.Text.UTF8Encoding
---

#### 8. 验证是否生效了
git config user.email
git config user.name

#### 9. 提交代码到远程仓库
git add .
git commit -m "fix: 修复中文乱码的问题"

#### 10. 同步效果啊
远程仓库会完全镜像你推送的本地分支结构
其他协作者可以通过 git fetch --all 获取这些新分支。