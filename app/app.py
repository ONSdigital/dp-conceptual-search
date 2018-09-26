"""
Code for creating HTTP api app
"""
import asyncio
import uvloop

from sanic.log import logger

from config.config_core import SEARCH_CONFIG
from api.search.routes import search_blueprint
from api.suggest.routes import suggest_blueprint
from app.log_config import log_config
from app.sanic_search import SanicSearch


def create_app() -> SanicSearch:
    """
    Creates the Sanic APP and registers all blueprints
    :return:
    """
    # First, set the ioloop event policy to use uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

    # Now initialise the APP config, logger and ONSRequest handler
    app = SanicSearch(log_config=log_config)

    logger.info("Using config '%s'" % SEARCH_CONFIG)
    app.config.from_pyfile('config/config_%s.py' % SEARCH_CONFIG)

    # Register blueprints
    app.blueprint(search_blueprint)
    app.blueprint(suggest_blueprint)

    return app
