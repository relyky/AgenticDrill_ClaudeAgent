# Claude Agent Drlll
此專案是為了練習 Claude Agent SDK 開發。

## 總方案 Agentic Drill
目的: 練習 Agentic AI 開發。共有三個專案。

### AgenticDrill_ReactApp (React App Server)
- 提供使用者介面。

- 框架: React and ASP.NET Core
- 後端: ASP.NET Core 10
- 前端: React 19

### AgenticDrill_ClaudeAgent (Claude Agent Drill)
- 提供 Agentic AI 服務。
- 用 Claude Agent SDK 實作。其 root agent 只能使用 claude models。
- 框架: Web API + Swagger UI
- 技術棧
  - python 3.14
  - claude-agent-sdk 0.1.19
  - fastapi + uvicorn

### AgenticDrill_GoogleAdk (Google ADK Drill)
- 提供 Agentic AI 服務。
- 用 Google ADK 實作。其 root agent 用 gemini models 才能發揮最大效用。
- 框架: Web API + Swagger UI
- 技術棧
  - python 3.12
  - google-adk 1.15.1
  - fastapi + uvicorn
