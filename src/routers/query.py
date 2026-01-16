"""
Query Router - 查詢路由模組

職責：
- 定義 /query 端點，接收用戶查詢請求
- 可以上傳附件檔案
- 透過 ClaudeSDKClient 與 Claude AI 互動
- 整合 MCP 工具（get_system_time, get_weather）處理查詢
- 回傳 AI 回應、session_id、token 使用量與費用資訊
"""

import logging
import base64
import json
from typing import Any, AsyncGenerator, AsyncIterable, List, Optional
from fastapi import APIRouter, UploadFile, File, Form
from pydantic import BaseModel
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage
from src.sdk_mcp_server import create_general_tools_mcp

logger = logging.getLogger(__name__)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    responseText: str = ""
    session_id: str | None = None
    usage: dict | None = None
    total_cost_usd: float | None = None
    error: str | None = None

# 文字格式
_text_formats = {".csv", ".json", ".md", ".txt", ".xml", ".yaml", ".yml"}

# 二進位格式
_binary_formats = {".pdf", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}

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

async def process_uploaded_text_files(files: Optional[List[UploadFile]]) -> AsyncGenerator[dict, None]:
    """讀取上傳文字類檔案，逐一 yield 格式化的訊息物件。"""
    if files:  # 只在有檔案時才處理
        for file in files:
            content = await file.read()
            text = content.decode('utf-8')
            size = len(content)

            yield {
                "type": "text",
                "text": f"""=== **file**: {file.filename} ===
**MIME type**: {file.content_type}
**file size**: {size} bytes

{text}"""
            }

@router.post("/query", response_model=QueryResponse)
async def handle_query(
    # 文字欄位使用 Form() 接收
    userInput: str = Form(...), 
    # 檔案欄位使用 File() 接收，List[UploadFile] 支援多檔上傳
    files: Optional[List[UploadFile]] = File(None)
) -> QueryResponse:
    """
    處理用戶查詢請求，透過 Claude AI 生成回應。

    接收 multipart/form-data 格式的請求，將上傳檔案內容與用戶問題組合後傳送給 ClaudeSDKClient 處理。

    Args:
        userInput: 用戶查詢文字
        files: 上傳檔案列表

    Returns:
        QueryResponse
    """
    try:
        logger.debug(f"handle_query: userInput={userInput}, files={len(files) if files else 0}")

        # 組合 prompt 的 async generator：先檔案內容，後使用者提問
        async def build_prompt() -> AsyncIterable[dict[str, Any]]:
            # 收集所有 content blocks
            content_blocks = []
            async for file_block in process_uploaded_text_files(files):
                content_blocks.append(file_block)
            content_blocks.append({"type": "text", "text": userInput})

            # yield 符合 SDK 預期格式的訊息
            yield {
                "type": "user",
                "message": {"role": "user", "content": content_blocks},
                "parent_tool_use_id": None,
            }
            
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt=build_prompt())

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
        raise e
        #return QueryResponse(error=str(e))
