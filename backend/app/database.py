"""Async SQLAlchemy database engine supporting both Cloud PostGIS (Neon/Supabase SSL) and local Postgres."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()


def build_asyncpg_url_and_args(raw_url: str) -> tuple[str, dict]:
    """Normalize Neon/Supabase/Render postgres:// URLs for asyncpg + SSL.

    Safely URL-encodes passwords containing special characters like '@', '#', '$', etc.
    """
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://") :]
    elif url.startswith("postgresql://") and "+asyncpg" not in url:
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]

    connect_args: dict = {}
    if url.startswith("postgresql+asyncpg://"):
        scheme, rest = url.split("://", 1)
        # Split authority from path/query
        if "/" in rest:
            authority, tail = rest.split("/", 1)
            tail = "/" + tail
        else:
            authority, tail = rest, ""

        # Split userinfo from host:port on the LAST '@' so '@' inside password is preserved
        if "@" in authority:
            userinfo, hostport = authority.rsplit("@", 1)
            if ":" in userinfo:
                user, pwd = userinfo.split(":", 1)
                safe_pwd = quote(unquote(pwd), safe="")
                authority = f"{user}:{safe_pwd}@{hostport}"

        url = f"{scheme}://{authority}{tail}"
        parts = urlsplit(url)
        query_items = dict(parse_qsl(parts.query))
        sslmode = query_items.pop("sslmode", None)
        query_items.pop("channel_binding", None)

        is_remote = parts.hostname not in {"localhost", "127.0.0.1", None, ""}
        if sslmode in {"require", "verify-ca", "verify-full"} or is_remote:
            connect_args["ssl"] = "require"
        if parts.port == 6543:
            connect_args["statement_cache_size"] = 0

        clean_query = urlencode(query_items)
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, clean_query, parts.fragment))

    return url, connect_args


ASYNC_DB_URL, CONNECT_ARGS = build_asyncpg_url_and_args(settings.DATABASE_URL)

engine = create_async_engine(
    ASYNC_DB_URL,
    echo=False,
    pool_pre_ping=True,
    connect_args=CONNECT_ARGS,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
