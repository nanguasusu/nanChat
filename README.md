# AI Chat

一个用于后续扩展的现代 AI Chat 全栈项目初始版本。

当前版本包含：

- React + TypeScript + Vite + Tailwind CSS 前端
- Zustand 管理按会话隔离的消息、草稿和流状态
- 本地 shadcn 风格基础组件与 Prompt Kit 风格聊天输入/消息组件
- FastAPI + Pydantic 后端
- SQLite 持久化聊天表 `threads`、`messages`，以及知识库表 `documents`、`parent_chunks`
- 侧边栏真实会话列表与多会话切换
- 输入框内的模型选择、思考模式和上下文窗口占用提示
- `GET /health` 健康检查
- `POST /api/chat` 通过 SSE 流式调用 Z.ai `glm-5.3-flash` 的 OpenAI-compatible 接口
- Parent-Child RAG：Child 的 dense + BM25 sparse 向量写入 Qdrant，Parent 内容写入 SQLite
- 混合检索后使用 SiliconFlow `BAAI/bge-reranker-v2-m3` 重排，并显示引用
- 亮色/暗色主题切换

当前阶段使用 `fetch + ReadableStream` 接收 SSE；暂时没有用户系统、登录、LangGraph 或 WebSocket。

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

如果 `.env` 是第一次创建，请将其中的 `LONGCAT_API_KEY` 和 `EMBEDDING_API_KEY` 替换为有效密钥；已有 `.env` 时不要覆盖它。这里的 `LONGCAT_*` 变量名为兼容现有配置保留，实际模型服务为 Z.ai。

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

发送消息前，请在 `backend/.env` 中填写有效的 Z.ai API Key（配置项仍为 `LONGCAT_API_KEY`）。开启输入框的“知识库”开关时，还需要有效的 `EMBEDDING_API_KEY`。API Key 只在后端使用，不会暴露给浏览器。

SQLite 数据库默认写入 `backend/data/ai_chat.db`，该目录已加入 Git 忽略规则。

## 会话 API

- `GET /api/threads`：读取最近会话
- `GET /api/threads/{thread_id}/messages`：读取会话消息
- `GET /api/models`：读取当前后端配置的模型及上下文窗口信息
- `POST /api/chat`：向指定会话发送 SSE 流；不传 `thread_id` 时才创建新线程

`POST /api/chat` 支持以下可选参数：

```json
{
  "model": "glm-5.3-flash",
  "thinking_level": "medium",
  "rag_enabled": false,
  "rag_mode": "standard",
  "query_rewrite_enabled": false
}
```

Z.ai GLM Chat Completions 支持思考模式。`glm-5.3-flash` 强制开启思考，前端的关闭、低、中、高、极高五档会映射为 Z.ai 支持的 `low`、`high`、`max` 思考强度。上下文占用是基于当前消息和草稿的前端估算，不写入数据库。

SSE 事件类型包括 `start`、`delta`、`done` 和 `error`。前端的 Stream Manager 按 `thread_id` 维护独立的 `AbortController`，切换会话不会中断后台生成。

## Knowledge Base

知识库由管理员离线构建，当前只支持普通文本 PDF、TXT 和 Markdown 文件。聊天输入框中的“知识库”开关默认关闭；开启后，发送消息前会检索 Qdrant 的 Child，并从 SQLite 恢复去重后的 Parent，作为本次回答的参考上下文，不写入会话历史。

1. 启动 Qdrant：

   ```bash
   docker compose up --build -d
   ```

   Qdrant 使用 `qdrant_storage` volume 持久化，地址为 <http://localhost:6333>。

2. 将 `.pdf`、`.txt` 或 `.md` 文件放入 `backend/knowledge/documents/`。

3. 在 `backend/.env` 中配置 `EMBEDDING_API_KEY`。该 Key 同时用于硅基流动的 `BAAI/bge-m3` embedding 和 `BAAI/bge-reranker-v2-m3` 重排；默认 API 地址是 `https://api.siliconflow.cn/v1`。

4. 构建或更新知识库：

   ```bash
   cd backend
   python scripts/build_kb.py
   ```

   也可以在 Compose 后端容器中执行：

   ```bash
   docker compose exec backend python scripts/build_kb.py
   ```

   如需删除当前 collection 后完整重建，增加 `--rebuild`。

   当前默认切块参数是 Parent 1600 字符、Child 400 字符、Child overlap 80 字符；当前 splitter 按字符工作，这些数值是对 token 目标的近似值。修改切块参数后请使用 `--rebuild`。

5. 直接检查 Retriever：

   ```bash
   python scripts/search_kb.py "文档中确实存在的问题"
   ```

6. 查询独立 API：

   ```bash
   curl -X POST http://localhost:8000/api/rag/search \
     -H 'Content-Type: application/json' \
     -d '{"query":"文档中确实存在的问题","k":5}'
   ```

当前阶段不包含文件上传、文件管理、权限、多租户或异步任务。检索先分别召回 dense 和 BM25 sparse Child，再由 Qdrant 使用 RRF 融合；按 Parent 去重后，将最多 12 个候选 Parent 提交给 SiliconFlow `BAAI/bge-reranker-v2-m3`，过滤重排分数低于 `RERANK_MIN_SCORE`（默认 `0.4`）的 Parent，最终最多取 4 个合格 Parent 作为模型上下文。打开前端设置中的 Query Rewrite 后，会先使用当前配置的模型将问题改写为适合检索的独立 query；改写只作用于检索，回答模型仍接收原始问题。检索上下文只在本次模型请求中使用，不写入 SQLite 聊天历史，也不改变现有 SSE 事件协议。

当 `rag_enabled=true` 时，API 可通过 `rag_mode` 显式选择 `standard`（默认）或 `agentic`。Agentic RAG 在同一个 `retrieve()` 之上执行“初始检索 → 规划 → 可选范围探索与一次重规划 → 并行回答任务与最多一次定向补检 → 合成”，并继续通过现有 `done.references` 返回去重后的 Parent 引用。中间只增加不含文档正文的 `agentic_stage` 进度事件；当前前端会安全忽略这些事件。此阶段尚未加入自动 Router 和最终 Verification。

## Docker Compose（可选）

项目提供了前后端应用和 Qdrant 的 Compose 配置：

```bash
docker compose up --build
```

前端地址：<http://localhost:5173>

## Z.ai 模型服务配置

`backend/.env.example` 中包含以下配置：

- `LONGCAT_BASE_URL=https://api.z.ai/api/paas/v4/`
- `LONGCAT_MODEL=glm-5.3-flash`
- `LONGCAT_CONTEXT_WINDOW_TOKENS=1048576`
- `LONGCAT_API_KEY`

请将密钥写入本地 `backend/.env`，不要提交到 Git。后端通过 OpenAI Python SDK 调用 `POST /api/paas/v4/chat/completions`，请求使用 `glm-5.3-flash` 和流式模式；输出 token 预算会根据思考强度在 1024 到 8192 之间调整。当前客户端会绕过系统代理环境变量，直接访问 API。

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
│   │   ├── agentic_rag/
│   │   ├── core/
│   │   ├── rag/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── knowledge/
│   │   └── documents/
│   ├── scripts/
│   ├── requirements.txt
│   └── .env.example
├── .gitignore
├── README.md
└── docker-compose.yml
```

## 下一阶段建议

下一步可以在当前多会话流式基础上，再评估消息删除/重命名，以及用户系统。
