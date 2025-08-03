#### 0. 拉取远程仓库
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

#### 5. 推送到远程（可选）
git push -u gradient30 solox-gemini

#### 6.设置全局提交身份
git config --global user.email "gradi@example.com"
git config --global user.name "Gradi"

#### 7. 验证是否生效
git config user.email
git config user.name

#### 8. 提交代码
git add .
git commit -m "msg:添加git使用说明文档"