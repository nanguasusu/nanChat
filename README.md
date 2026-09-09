# AI Chat

一个用于后续扩展的现代 AI Chat 全栈项目初始版本。

当前版本包含：

- React + TypeScript + Vite + Tailwind CSS 前端
- Zustand 管理按会话隔离的消息、草稿和流状态
- 本地 shadcn 风格基础组件与 Prompt Kit 风格聊天输入/消息组件
- FastAPI + Pydantic 后端
- SQLite 持久化 `threads` 和 `messages` 两张表
- 侧边栏真实会话列表与多会话切换
- 输入框内的模型选择、思考模式和上下文窗口占用提示
- `GET /health` 健康检查
- `POST /api/chat` 通过 SSE 流式调用 LongCat-2.0 的 OpenAI-compatible 接口
- 亮色/暗色主题切换

当前阶段使用 `fetch + ReadableStream` 接收 SSE；暂时没有用户系统、登录、LangChain、LangGraph 或 WebSocket。

## 本地启动

### 1. 启动 backend

要求 Python 3.11+。

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

如果 `.env` 是第一次创建，请将其中的 `LONGCAT_API_KEY` 替换为你的有效密钥；已有 `.env` 时不要覆盖它。

后端地址：<http://localhost:8000>

健康检查：<http://localhost:8000/health>

### 2. 启动 frontend

要求 Node.js 20+。

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

前端地址：<http://localhost:5173>

前端会将聊天请求发送到 `VITE_API_BASE_URL`，默认值为 `http://localhost:8000`。

发送消息前，请在 `backend/.env` 中填写有效的 `LONGCAT_API_KEY`。API Key 只在后端使用，不会暴露给浏览器。

SQLite 数据库默认写入 `backend/data/ai_chat.db`，该目录已加入 Git 忽略规则。

## 会话 API

- `GET /api/threads`：读取最近会话
- `GET /api/threads/{thread_id}/messages`：读取会话消息
- `GET /api/models`：读取当前后端配置的模型及上下文窗口信息
- `POST /api/chat`：向指定会话发送 SSE 流；不传 `thread_id` 时才创建新线程

`POST /api/chat` 支持以下可选参数：

```json
{
  "model": "LongCat-2.0",
  "thinking_level": "medium"
}
```

LongCat Chat Completions 当前原生提供开启/关闭思考模式。前端提供关闭、低、中、高、极高五档；除关闭/开启外，其余档位通过调整回答 token 预算实现，不伪造 provider 未公开的 reasoning effort 参数。上下文占用是基于当前消息和草稿的前端估算，不写入数据库。

SSE 事件类型包括 `start`、`delta`、`done` 和 `error`。前端的 Stream Manager 按 `thread_id` 维护独立的 `AbortController`，切换会话不会中断后台生成。

## Docker Compose（可选）

项目提供了只包含前后端应用的 Compose 配置，不包含数据库或其他基础设施：

```bash
docker compose up --build
```

前端地址：<http://localhost:5173>

## LongCat 配置

`backend/.env.example` 中包含以下配置：

- `LONGCAT_BASE_URL=https://api.longcat.chat/openai`
- `LONGCAT_MODEL=LongCat-2.0`
- `LONGCAT_CONTEXT_WINDOW_TOKENS=1048576`
- `LONGCAT_API_KEY`

请将密钥写入本地 `backend/.env`，不要提交到 Git。后端通过 OpenAI Python SDK 调用 `POST /openai/v1/chat/completions`，请求使用 `LongCat-2.0` 和流式模式；输出 token 预算会根据思考强度在 1024 到 8192 之间调整。当前 LongCat 客户端会绕过系统代理环境变量，直接访问 API。

## 目录结构

```text
ai-chat/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── chat/
│       │   ├── layout/
│       │   └── ui/
│       ├── pages/
│       ├── services/
│       ├── stores/
│       ├── types/
│       ├── App.tsx
│       └── main.tsx
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── requirements.txt
│   └── .env.example
├── .gitignore
├── README.md
└── docker-compose.yml
```

## 下一阶段建议

下一步可以在当前多会话流式基础上，再评估消息删除/重命名，以及用户系统。
