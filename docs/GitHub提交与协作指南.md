# GitHub 提交与协作指南

## 1. 提交前检查（防止敏感信息泄露）
在项目根目录执行：

```bash
cd "/Users/lfc/Documents/New project"
git status --short
```

检查要点：
- 不要提交 `backend/.env`（只提交 `backend/.env.example`）。
- 不要提交 `node_modules`、`.venv`、`dist`、`.idea`。
- 已通过 `.gitignore` 屏蔽上述目录和文件。

## 2. 首次提交到 GitHub（新仓库）

### 2.1 本地提交
```bash
cd "/Users/lfc/Documents/New project"
git add .
git commit -m "feat: init standard assistant MVP with frontend/backend split"
```

### 2.2 在 GitHub 创建空仓库
在 GitHub 页面创建一个新仓库，例如：`standard-assistant`  
创建时不要勾选 README、.gitignore（避免和本地冲突）。

### 2.3 绑定远程并推送
把下面 `<YOUR_REPO_URL>` 替换成你的仓库地址：

```bash
cd "/Users/lfc/Documents/New project"
git branch -M main
git remote add origin <YOUR_REPO_URL>
git push -u origin main
```

示例 URL：
- HTTPS: `https://github.com/<your_name>/standard-assistant.git`
- SSH: `git@github.com:<your_name>/standard-assistant.git`

## 3. 后续开发提交流程（推荐）

### 3.1 新功能开分支
```bash
git checkout -b codex/<feature-name>
```

### 3.2 开发并提交
```bash
git add .
git commit -m "feat: <your change summary>"
```

### 3.3 推送分支
```bash
git push -u origin codex/<feature-name>
```

然后在 GitHub 发起 Pull Request 合并到 `main`。

## 4. 常用命令

查看改动：
```bash
git status
git diff
```

查看提交历史：
```bash
git log --oneline --decorate --graph -20
```

更新本地主分支：
```bash
git checkout main
git pull --ff-only
```

## 5. 你这个项目的建议提交顺序
1. `chore: setup project structure and docker compose`
2. `feat: integrate langchain with deepseek`
3. `feat: support streaming response via sse`
4. `feat: render markdown output in frontend`
5. `feat: add redis-backed conversation memory`
6. `docs: add detailed execution plan and github guide`
