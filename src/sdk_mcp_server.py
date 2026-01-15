import logging
import os
from typing import Any
from pydantic import BaseModel
from datetime import datetime
from claude_agent_sdk import tool, create_sdk_mcp_server

logger = logging.getLogger(__name__)

def create_general_tools_mcp():
    
    # @tool("get_current_time", "Returns the current time in a specified city.", {"city": str})
    # async def get_current_time(args: dict[str, Any]) -> dict[str, Any]:
    #     city = args["city"]
    #     return {
    #         "content": [{"type": "text", "text": f"The time in {city} is 10:30 AM"}]
    #     }

    @tool("get_system_time", "Returns the current system time with timezone information.", {})
    async def get_system_time(args: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now().astimezone()
        return {
            "content": [{
                "type": "text",
                "text": f"System time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')} (ISO: {now.isoformat()})"
            }]
        }        
        
    return create_sdk_mcp_server(name="General tools", version="0.0.2", tools=[get_system_time])
