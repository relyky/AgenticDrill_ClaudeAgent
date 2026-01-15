import logging
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock
from src.sdk_mcp_server import create_general_tools_mcp

logger = logging.getLogger(__name__)

class QueryRequest(BaseModel):
    query: str

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
        "mcp__general_tools__get_system_time",
        "mcp__general_tools__get_weather"
    ],
)

router = APIRouter()

@router.post("/query")
async def handle_query(request: QueryRequest):
    try:
        logger.debug("entry handle_query")
        now = datetime.now()

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt=request.query)

            response = []
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            logging.info(f"Claude: {block.text}")
                            response.append(block.text)

            responseText = "".join(response)

        return {"received_time": now, "responseText": responseText}

    except Exception as e:
        return {"error": str(e)}
