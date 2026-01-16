"""
Query Router - 查詢路由模組

職責：
- 定義 /query 端點，接收用戶查詢請求
- 透過 ClaudeSDKClient 與 Claude AI 互動
- 整合 MCP 工具（get_system_time, get_weather）處理查詢
- 回傳 Claude 的文字回應
"""

import logging
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage
from src.sdk_mcp_server import create_general_tools_mcp

logger = logging.getLogger(__name__)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    responseText: str
    session_id: str | None = None
    usage: dict | None = None
    total_cost_usd: float | None = None

# Claude Agent 配置
system_prompt = """
You are a helpful assistant. Your native language is Traditional Chinese (zh-TW).
"""

options = ClaudeAgentOptions(
    system_prompt=system_prompt,
    max_turns=None,
    model="haiku",
    mcp_servers={"general_tools": create_general_tools_mcp()},
    allowed_tools=[
        "mcp__general_tools__get_weather",    
        "mcp__general_tools__get_system_time"
    ],
)

router = APIRouter()

@router.post("/query", response_model=QueryResponse)
async def handle_query(request: QueryRequest) -> QueryResponse:
    try:
        logger.debug(f"handle_query: {request}")
        
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt=request.query)

            response = []
            session_id = None
            usage = None
            total_cost_usd = None

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            logging.info(f"Claude: {block.text}")
                            response.append(block.text)
                elif isinstance(message, ResultMessage):
                    session_id = message.session_id
                    usage = message.usage
                    total_cost_usd = message.total_cost_usd

            responseText = "".join(response)

        return QueryResponse(
            responseText=responseText,
            session_id=session_id,
            usage=usage,
            total_cost_usd=total_cost_usd
        )

    except Exception as e:
        return {"error": str(e)}
