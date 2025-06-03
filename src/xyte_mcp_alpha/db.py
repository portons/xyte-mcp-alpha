from __future__ import annotations

import os
from typing import AsyncIterator
from contextlib import asynccontextmanager

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://mcp:pass@127.0.0.1/mcp"
)

_engine = create_async_engine(DATABASE_URL, future=True)
_SessionLocal = async_sessionmaker(
    _engine, expire_on_commit=False
)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with _SessionLocal() as session:
        yield session


async def init_db() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
