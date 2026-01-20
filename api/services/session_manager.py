import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

logger = logging.getLogger(__name__)

# Session 過期時間（分鐘）
SESSION_TIMEOUT_MINUTES = 30


class SessionExpiredError(Exception):
    """Session 已過期例外"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session '{session_id}' 已過期，請建立新的對話")


class InvalidSessionIdError(Exception):
    """Session ID 格式無效例外"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        super().__init__(f"Session ID '{session_id}' 格式無效，必須為有效的 GUID 格式")


@dataclass
class SessionState:
    """單一會話的狀態（不含 client）"""
    session_id: str
    last_accessed: datetime = field(default_factory=datetime.now)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def touch(self):
        """更新最後存取時間"""
        self.last_accessed = datetime.now()

    def is_expired(self, timeout_minutes: int = SESSION_TIMEOUT_MINUTES) -> bool:
        """檢查 session 是否過期"""
        return datetime.now() - self.last_accessed > timedelta(minutes=timeout_minutes)


class SessionManager:
    """管理多個 Claude SDK 會話的單例類別（共用單一 client）"""

    def __init__(self):
        self._client: ClaudeSDKClient | None = None
        self._client_lock = asyncio.Lock()
        self._sessions: dict[str, SessionState] = {}
        self._sessions_lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None
        self._options: ClaudeAgentOptions | None = None

    async def _ensure_client(self, options: ClaudeAgentOptions) -> ClaudeSDKClient:
        """確保 client 已連線（內部使用）"""
        async with self._client_lock:
            if self._client is None:
                self._options = options
                self._client = ClaudeSDKClient(options=options)
                await self._client.connect()
                logger.info("Shared ClaudeSDKClient connected")
            return self._client

    @staticmethod
    def _validate_guid(session_id: str) -> bool:
        """驗證 session_id 是否為有效的 GUID 格式"""
        try:
            uuid.UUID(session_id)
            return True
        except (ValueError, AttributeError):
            return False

    async def get_or_create_session(
        self,
        session_id: str,
        options: ClaudeAgentOptions
    ) -> tuple[ClaudeSDKClient, SessionState, str]:
        """
        取得現有 session 或建立新的 session

        Args:
            session_id: Session ID，必須為有效的 GUID 格式
            options: Claude Agent 配置選項

        Returns:
            (client, session_state, session_id) 元組

        Raises:
            InvalidSessionIdError: 當 session_id 格式不符合 GUID 格式時
            SessionExpiredError: 當 session 已過期時
        """
        # 驗證 GUID 格式
        if not self._validate_guid(session_id):
            raise InvalidSessionIdError(session_id)

        client = await self._ensure_client(options)

        async with self._sessions_lock:
            # 嘗試取得現有 session
            if session_id in self._sessions:
                state = self._sessions[session_id]
                if state.is_expired():
                    # Session 已過期，移除並拋出例外
                    logger.info(f"Session expired, removing: {session_id}")
                    del self._sessions[session_id]
                    raise SessionExpiredError(session_id)
                state.touch()
                logger.debug(f"Reusing existing session: {session_id}")
                return client, state, session_id

            # 建立新 session 狀態（使用外部傳入的 session_id）
            state = SessionState(session_id=session_id)
            self._sessions[session_id] = state

            logger.info(f"Created new session: {session_id}")
            return client, state, session_id

    def get_session_lock(self, session_id: str) -> asyncio.Lock | None:
        """取得特定 session 的鎖（用於並發控制）"""
        state = self._sessions.get(session_id)
        return state.lock if state else None

    async def list_sessions(self) -> list[dict]:
        """取得所有 session 清單"""
        async with self._sessions_lock:
            return [
                {
                    "session_id": state.session_id,
                    "last_accessed": state.last_accessed,
                    "is_expired": state.is_expired()
                }
                for state in self._sessions.values()
            ]

    async def cleanup_expired_sessions(self):
        """清理所有過期的 sessions"""
        async with self._sessions_lock:
            expired_ids = [
                sid for sid, state in self._sessions.items()
                if state.is_expired()
            ]

            for sid in expired_ids:
                logger.info(f"Cleaning up expired session: {sid}")
                del self._sessions[sid]

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
        """關閉 client 並停止清理任務"""
        # 停止清理任務
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # 斷開共用 client
        async with self._client_lock:
            if self._client:
                try:
                    await self._client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting client: {e}")
                self._client = None

        # 清空 sessions
        async with self._sessions_lock:
            self._sessions.clear()

        logger.info("SessionManager shutdown complete")


# 模組級單例
session_manager = SessionManager()
