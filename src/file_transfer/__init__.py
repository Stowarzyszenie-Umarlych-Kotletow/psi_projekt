import logging
import logging.config

logging.config.dictConfig({
    'version': 1,
    'formatters': {
        'simple': {
            'format': '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        },
        'request': {
            'format': '%(asctime)s | %(name)s | %(id).6s | %(levelname)s | %(method)s %(urn)s: %(message)s'
        },
    },
    'handlers': {
        'request-console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'request',
            'stream': 'ext://sys.stdout'
        }
    },
    'loggers': {
        'ClientHandler': {
            'level': 'DEBUG',
            'handlers': ['request-console']
        },
        'ServerHandler': {
            'level': 'DEBUG',
            'handlers': ['request-console']
        }
    }

})
