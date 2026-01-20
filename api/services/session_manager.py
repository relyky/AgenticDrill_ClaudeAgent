import asyncio
import logging
from dataclasses import dataclass, field
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from api.sdk_mcp_server import create_general_tools_mcp

logger = logging.getLogger(__name__)

# Claude Agent 配置
default_system_prompt = """
You are a helpful assistant. Your native language is Traditional Chinese (zh-TW).
"""

@dataclass
class SessionState:
    """單一會話的狀態（含獨立 client）"""
    conversation_no: int
    client: ClaudeSDKClient
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    running_total_cost_usd: float = 0  # 累計會話總成本
    dialogue_turn: int = 0       # 對話回合數

class SessionManager:
    """管理多個 Claude SDK 會話（每個 session 獨立 client）"""

    def __init__(self):
        self._sessions: dict[int, SessionState] = {}
        self._sessions_lock = asyncio.Lock()

    async def get_session(self, conversation_no: int) -> tuple[ClaudeSDKClient, SessionState]:
        """
        取得現有 session（不存在則拋出例外）

        Args:
            conversation_no: 會話編號

        Returns:
            (client, session_state) 元組

        Raises:
            KeyError: 若 session 不存在
        """
        async with self._sessions_lock:
            if conversation_no not in self._sessions:
                raise KeyError(f"Session {conversation_no} not found")
            state = self._sessions[conversation_no]
            logger.debug(f"Reusing existing session: {conversation_no}")
            return state.client, state

    async def create_session(
        self,
        system_prompt: str
    ) -> tuple[ClaudeSDKClient, SessionState]:
        """
        建立新 session（已存在則拋出例外）

        Args:
            conversation_no: 會話編號
            options: Claude Agent 配置選項

        Returns:
            (client, session_state) 元組

        Raises:
            ValueError: 若 session 已存在
        """
        async with self._sessions_lock:
            # new_conversation_no 依現在 sessions 中最大值再加 + 1
            new_conversation_no = max(self._sessions.keys(), default=0) + 1

            # 建立該 Session 專屬的配置，避免修改全域 options
            options = ClaudeAgentOptions(
                system_prompt=system_prompt if system_prompt is not None and system_prompt.strip() else default_system_prompt,
                max_turns=None,
                model="haiku",
                mcp_servers={"general_tools": create_general_tools_mcp()},
                allowed_tools=[
                    "mcp__general_tools__get_weather",
                    "mcp__general_tools__get_system_time"
                ],
            )

            # 建立該 Session 專屬的 client
            logger.debug(f"Creating new session no[{new_conversation_no}], system_prompt: {options.system_prompt}")
            client = ClaudeSDKClient(options=options)
            await client.connect()

            state = SessionState(conversation_no=new_conversation_no, client=client)
            self._sessions[new_conversation_no] = state

            logger.info(f"Created new session no[{new_conversation_no}]")
            return client, state

    def get_session_lock(self, conversation_no: int) -> asyncio.Lock | None:
        """取得特定 session 的鎖（用於並發控制）"""
        state = self._sessions.get(conversation_no)
        return state.lock if state else None

    async def list_sessions(self) -> list[dict]:
        """取得所有 session 清單"""
        async with self._sessions_lock:
            return [
                {
                    "conversation_no": state.conversation_no,
                    "dialogue_turn": state.dialogue_turn,
                    "running_total_cost_usd": state.running_total_cost_usd
                }
                for state in self._sessions.values()
            ]

    async def shutdown(self):
        """關閉所有 client"""
        async with self._sessions_lock:
            for state in self._sessions.values():
                try:
                    await state.client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting client: {e}")
            self._sessions.clear()

        logger.info("SessionManager shutdown complete")


# 模組級單例
session_manager = SessionManager()
