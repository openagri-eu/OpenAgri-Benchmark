import logging
import logzero


def setup_logging(name, logging_level):
    log_format = (
        '%(color)s[%(levelname)1.1s %(name)s %(asctime)s:%(msecs)d '
        '%(module)s:%(funcName)s:%(lineno)d]%(end_color)s %(message)s'
    )
    formatter = logzero.LogFormatter(fmt=log_format)
    return logzero.setup_logger(name=name, level=logging.getLevelName(logging_level), formatter=formatter)
