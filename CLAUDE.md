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

**單體式 FastAPI 應用 (main.py):**
- `ClaudeSDKClient` 處理與 Claude AI 的互動
- MCP 工具透過 `@tool` 裝飾器定義 (如 `get_current_time`)
- `/query` 端點接收用戶查詢，經 Claude 處理後回傳結果
- `/healthz` 健康檢查端點

**請求流程:**
```
QueryRequest → FastAPI Handler → ClaudeSDKClient → Claude AI (with MCP tools) → Response
```

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
