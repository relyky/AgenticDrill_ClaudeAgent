import logging
import os
import asyncio
import aiohttp
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
    
    @tool("get_weather", "Get current temperature for a location using coordinates.", {"latitude": float, "longitude": float})
    async def get_weather(args: dict[str, Any]) -> dict[str, Any]:
        latitude = args["latitude"]
        longitude = args["longitude"]

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m&temperature_unit=fahrenheit"
                async with session.get(url) as response:
                    if response.status != 200:
                        return {"content": [{"type": "text", "text": f"Error: HTTP {response.status}"}]}

                    data = await response.json()
                    temperature = data.get('current', {}).get('temperature_2m')

                    if temperature is None:
                        return {"content": [{"type": "text", "text": "Error: Temperature data not available"}]}

                    return {"content": [{"type": "text", "text": f"Temperature at ({latitude}, {longitude}): {temperature}°F"}]}

        except aiohttp.ClientError as e:
            return {"content": [{"type": "text", "text": f"Error: Network request failed: {e}"}]}
        except asyncio.TimeoutError:
            return {"content": [{"type": "text", "text": "Error: Request timed out"}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}]}
        
    return create_sdk_mcp_server(name="General tools", version="0.0.3", tools=[get_weather, get_system_time])
