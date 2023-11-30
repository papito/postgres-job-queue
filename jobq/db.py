import os
from typing import Optional

import asyncpg  # type: ignore
from asyncpg import Connection, Pool  # type: ignore
from asyncpg.pool import PoolAcquireContext  # type: ignore
from quart import Quart, g, has_request_context, request

from jobq.constants import Const
from jobq.logger import logger


class DbConnectionManager:
    config_app: Quart
    conn_pool: Optional[Pool]

    @property
    def request_connection_name(self) -> str:
        # get unique connection name for a request, so we can refer to it later
        index: int
        if has_request_context():
            index = getattr(request, "index", 0)
        else:
            index = 0

        return f"connection-{index}"

    def get_connection(self) -> Connection:
        return getattr(g, self.request_connection_name, None)

    async def create_connection_pool(self) -> None:
        self.conn_pool = await asyncpg.create_pool(
            database=os.environ.get(Const.Config.DB.DB_NAME),
            user=os.environ.get(Const.Config.DB.DB_USER),
            password=os.environ.get(Const.Config.DB.DB_PASSWORD),
            host=os.environ.get(Const.Config.DB.DB_HOST),
            port=os.environ.get(Const.Config.DB.DB_PORT),
            server_settings={"jit": "off", "application_name": "Postgres Queue Example"},
        )
        logger.info("CREATED connection pool...")

    async def close_connection_pool(self) -> None:
        assert self.conn_pool
        await self.conn_pool.close()
        logger.warning("CLOSED connection pool...")

    def get_connection_ctx(self) -> Optional[PoolAcquireContext]:
        assert self.conn_pool
        return self.conn_pool.acquire()

    async def close_connection(self) -> None:
        raise NotImplementedError

    async def release_connection(self) -> None:
        conn: Connection = getattr(g, self.request_connection_name, None)
        if not conn:
            return

        pool: Optional[Pool] = getattr(g, "pool", None)
        if not pool:
            return

        logger.trace(f"Releasing connection {id(conn)} from {pool}")
        await pool.release(conn)
        setattr(g, self.request_connection_name, None)

    # saves the connection in the global request context, so we can use it throughout the request
    def set_connection(self, conn_from_context: Connection, pool: Optional[Pool] = None) -> None:
        logger.trace(f"Setting connection {id(conn_from_context)} from {pool}")
        setattr(g, self.request_connection_name, conn_from_context)

        if pool:
            setattr(g, "pool", pool)

    async def commit(self) -> None:
        conn: Connection = getattr(g, self.request_connection_name, None)
        logger.debug(f"*COMMIT* DB connection ID {id(conn)}")
        await conn.transaction().commit()

    async def rollback(self) -> None:
        conn: Connection = getattr(g, self.request_connection_name, None)

        if not conn:
            return

        logger.warning(f"*ROLLBACK* DB connection {id(conn)}")
        await conn.transaction().rollback()


class Database:
    connection_manager: DbConnectionManager

    def __init__(self):
        self.connection_manager = DbConnectionManager()

    def get_connection(self) -> Connection:
        return self.connection_manager.get_connection()

    async def create_connection_pool(self):
        await self.connection_manager.create_connection_pool()

    async def close_connection_pool(self):
        await self.connection_manager.close_connection_pool()


db = Database()
