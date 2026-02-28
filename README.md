# 标准智能助手（Web 单页问答）

## 目录结构

- `frontend/`: React + Vite Web 前端
- `backend/`: FastAPI 后端
- `docs/`: 需求与开发文档

## 快速启动（Docker）

```bash
docker compose up --build
```

启动后：
- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/api/v1/health`

## 本地开发（不使用 Docker）

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## GitHub 提交

- 提交流程见文档：`docs/GitHub提交与协作指南.md`
