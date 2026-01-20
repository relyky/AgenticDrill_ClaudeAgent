import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from claude_agent_sdk import ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage

from api.sdk_mcp_server import create_general_tools_mcp
from api.services.session_manager import session_manager


class ChatRequest(BaseModel):
    user_input: str = None
    conversation_no: int = None

class ChatResponse(BaseModel):
    responseText: str
    conversation_no: int
    usage: dict | None = None
    total_cost_usd: float
    running_total_cost_usd: float
    dialogue_turn: int

class SessionInfo(BaseModel):
    conversation_no: int = -1
    running_total_cost_usd: float = 0
    dialogue_turn: int = 0

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

_conversation_counter = 0 # 會話編號

@router.post("/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest) -> ChatResponse:
    """
    用戶與 AI 會話，支援跨請求記憶。

    Args:
        user_input: 使用者對話文字
        conversation_no: 會話編號，若相同則延續先前對話

    Returns:
        ChatResponse
    """
    try:
        logger.debug(f"handle_chat: user_input={request.user_input}, conversation_no={request.conversation_no}")

        # 取得或建立 session
        conversation_no = request.conversation_no
        if request.conversation_no == -1:
            global _conversation_counter
            _conversation_counter = _conversation_counter + 1
            conversation_no = _conversation_counter
                    
        client, state = await session_manager.get_or_create_session(
            conversation_no=conversation_no,
            options=options
        )

        # 使用 session lock 防止同一 session 並發存取
        async with state.lock:
            await client.query(prompt=request.user_input)

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
                    state.running_total_cost_usd = state.running_total_cost_usd + total_cost_usd
                    state.dialogue_turn = state.dialogue_turn + 1

            responseText = "".join(response)

        return ChatResponse(
            responseText=responseText,
            conversation_no=state.conversation_no,
            usage=usage,
            total_cost_usd=total_cost_usd,
            running_total_cost_usd=state.running_total_cost_usd,
            dialogue_turn=state.dialogue_turn
        )
    except Exception as e:
        logger.exception(f"handle_chat exception: {e}")
        raise HTTPException(status_code=422, detail=str(e))

@router.get("/chat/sessions", response_model=list[SessionInfo])
async def handle_list_chat_sessions():
    """列出現在會話(session)清單"""
    sessions = await session_manager.list_sessions()
    return sessions
