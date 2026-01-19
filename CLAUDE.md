# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AgenticDrill_ClaudeAgent 是一個基於 FastAPI 的 AI Agent 服務，透過 Claude Agent SDK 整合 Anthropic Claude，支援 MCP (Model Context Protocol) 工具定義。

## Development Commands

```bash
# 安裝依賴
uv sync --frozen

# 本地開發 (推薦)
uv run uvicorn main:app

# 本地開發 (自動重載)
# **注意**: 自動重載(--reload) 在 windows 環境無效，會出現錯誤訊息: "Failed to start Claude Code: "。原因： --reload 參數會讓 uvicorn 使用不同的事件迴圈機制（watchfiles），這與 Windows 上的 subprocess 支援有衝突。
uv run uvicorn main:app --reload

# 運行服務
uv run uvicorn main:app --host 127.0.0.1 --port 8000

# Docker 部署
docker-compose up --build
```

## Architecture

**模組化 FastAPI 應用:**
```
main.py                     # 應用程式進入點，註冊路由與中介軟體
api/
├── routers/                # API 路由模組
│   ├── health.py           # /healthz 健康檢查端點
│   ├── query.py            # /query 端點，支援檔案上傳
│   └── chat.py             # /chat 端點，純文字對話
└── sdk_mcp_server.py       # MCP 工具定義 (使用 @tool 裝飾器)
```

**請求流程:**
```
Request → router → ClaudeSDKClient → Claude AI (with MCP tools) → Response
```

**MCP 工具定義模式:**
```python
@tool("tool_name", "description", {"param": type})
async def tool_name(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": "result"}]}
```

## API Endpoints

| 端點 | 方法 | 說明 |
|------|------|------|
| `/healthz` | GET | 健康檢查 |
| `/query` | POST | 支援檔案上傳的查詢 (multipart/form-data) |
| `/chat` | POST | 純文字對話 (JSON) |

## 檔案上傳支援格式 (/query)

- 文字檔：`.csv`, `.json`, `.md`, `.txt`, `.xml`, `.yaml`, `.yml`
- 文件檔：`.pdf`
- 圖片檔：`.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`

## Key Dependencies

- **claude-agent-sdk**: Anthropic 的 Agent SDK，用於 Claude 整合與 MCP 工具定義
- **FastAPI + Uvicorn**: 非同步 Web 框架與 ASGI 伺服器
- **uv**: Python 套件管理器

## Environment

需要 `.env` 檔案設定 `ANTHROPIC_API_KEY`（參考 `.env.sample`）

## Commit Convention

使用繁體中文撰寫 commit 訊息，格式：`[動作]: [描述]`
- Add: 新增功能
- Fix: 修正錯誤
- Refactor: 重構程式碼
- Implement: 實作整合功能
