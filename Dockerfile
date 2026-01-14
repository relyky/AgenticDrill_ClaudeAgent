# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# 啟用 bytecode 編譯與連結模式
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# 複製相依套件定義
COPY pyproject.toml uv.lock ./

# 安裝相依套件（不含專案本身）
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# 複製專案程式碼
COPY . .

# 安裝專案
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# 設定 PATH
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
