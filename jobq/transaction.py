from functools import wraps
from typing import Any, Optional

from asyncpg import Connection  # type: ignore

from jobq.db import db
from jobq.logger import logger


def write_transaction(f):
    """
    A method decorated with this will be within a DB write transaction.
    All methods called downstream  will reuse the top level transaction.

    If there is an error, the transaction will be rolled back at the top level method.
    """

    @wraps(f)
    async def decorated_function(*args, **kwargs):
        logger.trace("In RW transaction")
        conn: Connection = db.connection_manager.get_connection()

        # already a connection, proceed
        if conn:
            return await f(*args, **kwargs)

        # top-level call: get a new connection context, save connection
        conn_ctx = db.connection_manager.get_connection_ctx()
        if not conn_ctx:
            raise Exception("Could not acquire connection context")

        async with conn_ctx as conn:
            async with conn.transaction():
                db.connection_manager.set_connection(conn, db.connection_manager.conn_pool)
                result = await f(*args, **kwargs)

        await db.connection_manager.release_connection()
        return result

    return decorated_function


def read_transaction(f):
    """
    A method decorated with this will be within a DB read transaction.
    All methods called downstream  will reuse the top level transaction.

    An SQL statement that attempts to write within this context is going to jail.
    """

    @wraps(f)
    async def decorated_function(*args, **kwargs):
        logger.trace("In RO transaction")
        conn: Connection = db.connection_manager.get_connection()

        # already a connection, proceed
        if conn:
            return await f(*args, **kwargs)

        # top-level call: get a new connection context, save connection
        conn_ctx = db.connection_manager.get_connection_ctx()
        if not conn_ctx:
            raise Exception("Could not acquire connection context")

        result: Optional[Any]

        async with conn_ctx as conn:
            async with conn.transaction(readonly=True):  # <-- mhmmm
                db.connection_manager.set_connection(conn, db.connection_manager.conn_pool)
                result = await f(*args, **kwargs)

        await db.connection_manager.release_connection()
        return result

    return decorated_function
