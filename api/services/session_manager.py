import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

logger = logging.getLogger(__name__)

# Session 過期時間（分鐘）
SESSION_TIMEOUT_MINUTES = 30


@dataclass
class ManagedSession:
    """管理單一會話的資料結構"""
    client: ClaudeSDKClient
    last_accessed: datetime = field(default_factory=datetime.now)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def touch(self):
        """更新最後存取時間"""
        self.last_accessed = datetime.now()

    def is_expired(self, timeout_minutes: int = SESSION_TIMEOUT_MINUTES) -> bool:
        """檢查 session 是否過期"""
        return datetime.now() - self.last_accessed > timedelta(minutes=timeout_minutes)


class SessionManager:
    """管理多個 Claude SDK 會話的單例類別"""

    def __init__(self):
        self._sessions: dict[str, ManagedSession] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    async def get_or_create_session(
        self,
        session_id: str | None,
        options: ClaudeAgentOptions
    ) -> tuple[ManagedSession, str]:
        """
        取得現有 session 或建立新的 session

        Args:
            session_id: 現有的 session ID，若為 None 則建立新 session
            options: Claude Agent 配置選項

        Returns:
            (ManagedSession, session_id) 元組
        """
        async with self._lock:
            # 嘗試取得現有 session
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                if not session.is_expired():
                    session.touch()
                    logger.debug(f"Reusing existing session: {session_id}")
                    return session, session_id
                else:
                    # Session 已過期，清理並建立新的
                    logger.info(f"Session expired, cleaning up: {session_id}")
                    await self._cleanup_session(session_id)

            # 建立新 session
            new_session_id = str(uuid.uuid4())
            client = ClaudeSDKClient(options=options)
            await client.connect()

            session = ManagedSession(client=client)
            self._sessions[new_session_id] = session

            logger.info(f"Created new session: {new_session_id}")
            return session, new_session_id

    async def _cleanup_session(self, session_id: str):
        """清理單一 session（內部使用，需在 _lock 內呼叫）"""
        if session_id in self._sessions:
            session = self._sessions.pop(session_id)
            try:
                await session.client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting session {session_id}: {e}")

    async def cleanup_expired_sessions(self):
        """清理所有過期的 sessions"""
        async with self._lock:
            expired_ids = [
                sid for sid, session in self._sessions.items()
                if session.is_expired()
            ]

            for sid in expired_ids:
                logger.info(f"Cleaning up expired session: {sid}")
                await self._cleanup_session(sid)

            if expired_ids:
                logger.info(f"Cleaned up {len(expired_ids)} expired sessions")

    async def start_cleanup_task(self, interval_minutes: int = 5):
        """啟動定期清理任務"""
        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval_minutes * 60)
                await self.cleanup_expired_sessions()

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info("Session cleanup task started")

    async def shutdown(self):
        """關閉所有 sessions 並停止清理任務"""
        # 停止清理任務
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # 清理所有 sessions
        async with self._lock:
            for sid in list(self._sessions.keys()):
                await self._cleanup_session(sid)

        logger.info("SessionManager shutdown complete")


# 模組級單例
session_manager = SessionManager()
