import logging
from fastapi import APIRouter
from pydantic import BaseModel
from claude_agent_sdk import ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage

from api.sdk_mcp_server import create_general_tools_mcp
from api.services.session_manager import session_manager, SessionExpiredError, InvalidSessionIdError


class ChatRequest(BaseModel):
    user_input: str = None
    session_id: str | None = None


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
async def handle_chat(request: ChatRequest) -> ChatResponse:
    """
    用戶與 AI 會話，支援跨請求記憶。

    Args:
        user_input: 使用者對話文字
        session_id: 會話 ID（可選），若提供則延續先前對話

    Returns:
        ChatResponse
    """
    try:
        logger.debug(f"handle_chat: user_input={request.user_input}, session_id={request.session_id}")

        # 取得或建立 session（共用 client）
        client, state, session_id = await session_manager.get_or_create_session(
            session_id=request.session_id,
            options=options
        )

        # 使用 session lock 防止同一 session 並發存取
        async with state.lock:
            await client.query(prompt=request.user_input, session_id=session_id)

            response = []
            usage = None
            total_cost_usd = None

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            logger.info(f"Claude: {block.text}")
                            response.append(block.text)
                elif isinstance(message, ResultMessage):
                    usage = message.usage
                    total_cost_usd = message.total_cost_usd

            responseText = "".join(response)

        return ChatResponse(
            responseText=responseText,
            session_id=session_id,
            usage=usage,
            total_cost_usd=total_cost_usd
        )
    except InvalidSessionIdError as e:
        logger.warning(f"Invalid session ID format: {e.session_id}")
        return ChatResponse(error=str(e))
    except SessionExpiredError as e:
        logger.warning(f"Session expired: {e.session_id}")
        return ChatResponse(error=str(e))
    except Exception as e:
        logger.exception(f"handle_chat exception: {e}")
        return ChatResponse(error=str(e))
