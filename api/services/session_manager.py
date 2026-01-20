import asyncio
import logging
from dataclasses import dataclass, field

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

logger = logging.getLogger(__name__)


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
        conversation_no: int,
        options: ClaudeAgentOptions
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
            if conversation_no in self._sessions:
                raise ValueError(f"Session {conversation_no} already exists")

            client = ClaudeSDKClient(options=options)
            await client.connect()
            state = SessionState(conversation_no=conversation_no, client=client)
            self._sessions[conversation_no] = state

            logger.info(f"Created new session: {conversation_no}")
            return client, state

    async def get_or_create_session(
        self,
        conversation_no: int,
        options: ClaudeAgentOptions
    ) -> tuple[ClaudeSDKClient, SessionState]:
        """
        取得現有 session 或建立新的 session（相容性方法）

        Args:
            conversation_no: 會話編號
            options: Claude Agent 配置選項

        Returns:
            (client, session_state) 元組
        """
        async with self._sessions_lock:
            if conversation_no in self._sessions:
                state = self._sessions[conversation_no]
                logger.debug(f"Reusing existing session: {conversation_no}")
                return state.client, state

            # 建立新 client 和 session
            client = ClaudeSDKClient(options=options)
            await client.connect()
            state = SessionState(conversation_no=conversation_no, client=client)
            self._sessions[conversation_no] = state

            logger.info(f"Created new session: {conversation_no}")
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
