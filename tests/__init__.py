import os

from dotenv import load_dotenv

from jobq.constants import Const

os.environ[Const.Config.ENV] = Const.Env.TEST
load_dotenv("env/test.env")
