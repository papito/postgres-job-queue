from quart import Quart

import jobq.service
from jobq.db import db
from jobq.handlers.web import web as web_blueprint


class ApplicationGenerator:
    def create_app(self) -> Quart:
        app = Quart(__name__)

        app.register_blueprint(web_blueprint)

        self.set_startup_handlers(app)
        self.set_shutdown_handlers(app)

        return app

    @staticmethod
    def set_startup_handlers(app: Quart) -> None:
        @app.before_serving
        async def startup():
            await db.create_connection_pool()
            jobq.service.job_worker.start(app)

    @staticmethod
    def set_shutdown_handlers(app: Quart) -> None:
        @app.after_serving
        async def shutdown():
            await db.close_connection_pool()
            await jobq.service.job_worker.stop()


def create_app() -> Quart:
    return ApplicationGenerator().create_app()
