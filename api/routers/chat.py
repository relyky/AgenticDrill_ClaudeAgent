import logging
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage
from api.sdk_mcp_server import create_general_tools_mcp

class ChatRequest(BaseModel):
    userInput: str = None

class ChatResponse(BaseModel):
    responseText: str = ""
    session_id: str | None = None
    usage: dict | None = None
    total_cost_usd: float | None = None
    error: str | None = None
    
logger = logging.getLogger(__name__)
router = APIRouter()

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

@router.post("/chat", response_model=ChatResponse)
async def handle_chat(
    request: ChatRequest
) -> ChatResponse:
    """
    用戶與 AI 會話。

    Args:
        userInput: 使用者對話文字

    Returns:
        ChatResponse
    """    
    try:
        logger.debug(f"handle_chat: userInput={request.userInput}")        
        now = datetime.now()
        
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt=request.userInput)

            response = []
            session_id = None
            usage = None
            total_cost_usd = None

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            logger.info(f"Claude: {block.text}")
                            response.append(block.text)
                elif isinstance(message, ResultMessage):
                    session_id = message.session_id
                    usage = message.usage
                    total_cost_usd = message.total_cost_usd

            responseText = "".join(response)
        
        return ChatResponse(
            responseText=responseText,
            session_id=session_id,
            usage=usage,
            total_cost_usd=total_cost_usd
        )
    except Exception as e:
        logger.exception(f"handle_chat exception: {e}")
        return ChatResponse(error=str(e))
