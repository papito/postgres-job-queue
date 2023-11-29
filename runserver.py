import logging
import os
from dotenv import load_dotenv

from jobq import create_app
from jobq.constants import Const

from jobq.logger import logger

logging.getLogger('hypercorn.access').disabled = True

env = os.environ.get(Const.Config.ENV)

if env == Const.Env.LOCAL:
    load_dotenv("env/local.env")
else:
    raise RuntimeError("Not running in LOCAL environment")

application = create_app()

host: str = os.environ.get(Const.Config.SERVER_HOST)
port: int = int(os.environ.get(Const.Config.SERVER_PORT))

logger.info(f"Starting server on port {[port]}")

application.run(debug=True, host=host, port=port,
)
