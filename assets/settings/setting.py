import logging
from logging.config import dictConfig

LOGGING_CONFIG = {
    "version": 1, 
    "disabled_existing_loggers": False, 
    "formatters":{
        "verbose":{
            "format": "%(levelname)-6s - %(asctime)s - %(module)-15s : %(message)s"
        },
        "standard":{
            "format": "%(levelname)-6s - %(name)-20s : %(message)s"
        }
    }, 
    "handlers":{
        "console": {
            'level': "DEBUG", 
            'class': "logging.StreamHandler",
            'formatter': "standard"
        }, 
        "console2": {
            'level': "INFO", 
            'class': "logging.StreamHandler",
            'formatter': "standard"
        }, 
        "file": {
            'level': "INFO", 
            'class': "logging.FileHandler",
            'filename': "logs/infos.log",
            'mode': "w", 
            'formatter': "verbose"
        }, 
    }, 
    "loggers":{
        "bot": {
            'handlers': ['console', "file"],
            "level": "INFO", 
            "propagate": False
        }, 
        "lofi_transformer": {
            'handlers': ['console', "file"],
            "level": "DEBUG", 
            "propagate": False
        }, 
        "discord": {
            'handlers': ['console2', "file"],
            "level": "INFO", 
            "propagate": False
        }
    }
}

dictConfig(LOGGING_CONFIG)