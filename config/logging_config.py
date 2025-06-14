import logging
import logging.config
from config.settings import settings

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': settings.log_level,
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': settings.log_level,
            'formatter': 'detailed',
            'class': 'logging.FileHandler',
            'filename': settings.log_file,
            'mode': 'a',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default', 'file'],
            'level': settings.log_level,
            'propagate': False
        }
    }
}

def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)