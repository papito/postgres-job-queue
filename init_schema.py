import asyncio
import importlib
import os
from importlib import resources

import psycopg2
from dotenv import load_dotenv

from jobq.constants import Const


async def main():
    load_dotenv("env/local.env")

    conn = psycopg2.connect(
        database=os.environ.get(Const.Config.DB.DB_NAME),
        user=os.environ.get(Const.Config.DB.DB_USER),
        password=os.environ.get(Const.Config.DB.DB_PASSWORD),
        host=os.environ.get(Const.Config.DB.DB_HOST),
        port=os.environ.get(Const.Config.DB.DB_PORT)
    )

    print()
    print("-> Connected")

    with conn.cursor() as cur:
        schema_raw = importlib.resources.files("jobq").joinpath("schema.sql").read_text()
        cur.execute(''.join(schema_raw))
        print("-> schema written")
        conn.commit()
        conn.close()
        print("-> looks like we win")
        print()
asyncio.run(main())
