import logging

# enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO)

LOGGER = logging.getLogger(__name__)

from server.config import Development as Config

ES_HOST = Config.ES_HOST
ES_PORT = Config.ES_PORT

WEB_HOST = Config.WEB_HOST
WEB_PORT = Config.WEB_PORT

from server.utils.vectorizer import Vectorizer

vectorizer = Vectorizer()