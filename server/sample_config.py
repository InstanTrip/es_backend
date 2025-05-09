

class Config(object):
    # ElasticSearch
    ES_HOST = 'localhost'
    ES_PORT = 9200

    # Setting
    WEB_HOST = 'localhost'
    WEB_PORT = 5000

class Production(Config):
    LOGGER = False

class Development(Config):
    LOGGER = True