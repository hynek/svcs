import logging.config

from datetime import datetime

import svcs


logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(name)s: %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "standard",
            },
        },
        "loggers": {
            "svcs": {
                "handlers": ["console"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "INFO",
        },
    }
)


reg = svcs.Registry()

reg.register_factory(datetime, datetime.now)
reg.register_value(str, "Hello World")
