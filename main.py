import logging
import os
from typing import Any
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, tool, create_sdk_mcp_server
from __init__ import SERVICE_NAME, VERSION

load_dotenv() # 這會讀取 .env 檔案

# 定義 model
class QueryRequest(BaseModel):
    query: str

# 設定 logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,      # Config.LOG_LEVEL,
    filename=None,            # Config.LOG_FILENAME,
    encoding="utf-8",
)

logger = logging.getLogger(__name__)

# 組織 Claude Agent
system_prompt="""
You are a helpful assistant that tells the current time in cities. Use the 'get_current_time' tool for this purpose.
"""

def create_general_tools_mcp():
    
    @tool("get_current_time", "Returns the current time in a specified city.", {"city": str})
    async def get_current_time(args: dict[str, Any]) -> dict[str, Any]:
        city = args["city"]
        return {
            "content": [{"type": "text", "text": f"The time in {city} is 10:30 AM"}]
        }
        
    return create_sdk_mcp_server(name="General tools", version="0.0.1", tools=[get_current_time])

options = ClaudeAgentOptions(
	system_prompt=system_prompt,  # 定義 AI 的角色與行為準則
	max_turns=None,  # 不限制對話輪次（適用於 agent 模式，單次查詢時無影響）
	model="haiku",   # 指定使用的 Claude 模型版本
    mcp_servers={
        "general_tools": create_general_tools_mcp(),
    }, 
	allowed_tools=[
        "mcp__general_tools__get_current_time"
	],
)

# 設定 FastAPI
app = FastAPI(title=SERVICE_NAME, version=VERSION)

# CORS
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)
    
@app.get("/healthz")
async def health_check():
    return {
        "status": "ok",
        "service_name": SERVICE_NAME,
        "version": VERSION,
	}    

@app.post("/query")
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
            
        return {
            "received_time": now,
			"responseText": responseText,
		}

    except Exception as e:
        return {"error":str(e)}

#def main():
#    logger.info("系統啟始")
#
#if __name__ == "__main__":
#    main()