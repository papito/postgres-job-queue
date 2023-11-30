import os

from dotenv import load_dotenv

from jobq.constants import Const

# force the test environment early on
os.environ[Const.Config.ENV] = Const.Env.TEST
load_dotenv("env/test.env")
