class Const:
    LOG_NAME = "jobq"

    class Config:
        ENV = "ENV"
        SERVER_PORT = "SERVER_PORT"
        SERVER_HOST = "SERVER_HOST"
        DEBUG = "DEBUG"
        WORKER_COUNT = "WORKERS"
        POLLING_INTERVAL = "POLLING_INTERVAL"

        class DB:
            DB_NAME = "DB_NAME"
            DB_USER = "DB_USER"
            DB_HOST = "DB_HOST"
            DB_PASSWORD = "DB_PASSWORD"
            DB_PORT = "DB_PORT"

    class Env:
        LOCAL = "LOCAL"
        TEST = "TEST"

    class Jobs:
        MAX_RETRIES = 3
        BASE_RETRY_MINUTES = 20
