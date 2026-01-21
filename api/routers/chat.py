import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from claude_agent_sdk import AssistantMessage, TextBlock, ResultMessage
from api.services.session_manager import session_manager, generate_subject

class ChatOptions(BaseModel):
    system_prompt: str = "default"
    user_input: str

class ChatInfo(BaseModel):
    conversation_no: int = -1
    subject: str
    running_total_cost_usd: float = 0
    dialogue_turn: int = 0

class ChatRequest(BaseModel):
    user_input: str

class ChatResponse(BaseModel):
    responseText: str
    conversation_no: int
    total_cost_usd: float
    running_total_cost_usd: float
    dialogue_turn: int
    usage: dict | None = None

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat/create", response_model=ChatInfo)
async def handle_chat_creation(request: ChatOptions) -> ChatInfo:
    """
    使用者與 AI 建立新會話，支援短期記憶能力。

    Args:
        user_input: 使用者對話文字

    Returns:
        ChatResponse
    """

    try:
        logger.debug(f"handle_chat_creation: `{request.system_prompt}` `{request.user_input}`")
        
        # 把使用者第一輪對話輸入轉換成 subject                        
        subject = await generate_subject(request.user_input)
        
        # 建立新會話
        _, state = await session_manager.create_session(
            system_prompt=request.system_prompt, 
            subject=subject
        )
        
        return ChatInfo(
            conversation_no=state.conversation_no,
            subject=state.subject,
            running_total_cost_usd=state.running_total_cost_usd,
            dialogue_turn=state.dialogue_turn
        )
        
    except Exception as e:
        logger.exception(f"handle_chat_create exception: {e}")
        raise HTTPException(status_code=422, detail=str(e))

@router.post("/chat/{conversation_no}", response_model=ChatResponse)
async def handle_chat(conversation_no: int, request: ChatRequest) -> ChatResponse:
    """
    使用者與 AI 接續會話，支援短期記憶能力。

    Args:
        user_input: 使用者對話文字
        conversation_no: 會話識別編號（必填

    Returns:
        ChatResponse

    Raises:
        HTTPException 404: 若 conversation_no 不存在
    """
    try:
        logger.debug(f"handle_chat: user_input={request.user_input}, conversation_no={conversation_no}")

        client, state = await session_manager.get_session(
            conversation_no=conversation_no
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"handle_chat exception: {e}")
        raise HTTPException(status_code=422, detail=str(e))

    try:

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


@router.get("/chat/sessions", response_model=list[ChatInfo])
async def handle_list_chat_sessions():
    """列出現在會話(session)清單"""
    sessions = await session_manager.list_sessions()
    return sessions
