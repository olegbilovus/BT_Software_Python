from logtail import LogtailHandler
import logging
import sys
import time


class STDtoLogger:
    def __init__(self, level):
        self.level = level
        self.buf = []

    def write(self, msg):
        if msg.endswith('\n'):
            self.buf.append(msg.removesuffix('\n'))
            self.level(''.join(self.buf))
            self.buf = []
        else:
            self.buf.append(msg)

    def flush(self):
        """Required for compatibility"""
        pass


def get_logger(name, token=None, logtail=True, file=False, stdout=True, stdout_r=False, stderr=False, stderr_r=False,
               other_loggers=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.handlers = []

    if logtail:
        handler = LogtailHandler(source_token=token)
        logger.addHandler(handler)
        if other_loggers is not None:
            for other_logger in other_loggers:
                other = logging.getLogger(other_logger)
                other.addHandler(handler)
                logger.info(f'Other logger {other_logger} added')
    if stdout:
        handler = logging.StreamHandler(sys.stdout)
        logger.addHandler(handler)
    if stdout_r:
        sys.stdout = STDtoLogger(logger.debug)
    if stderr:
        handler = logging.StreamHandler(sys.stderr)
        logger.addHandler(handler)
    if stderr_r:
        sys.stderr = STDtoLogger(logger.error)
    if file:
        handler = logging.FileHandler(f'{name}.log')
        logger.addHandler(handler)

    formatter = logging.Formatter('%(levelname)s %(asctime)s - %(message)s')
    for handler in logger.handlers:
        handler.setFormatter(formatter)
    logging.Formatter.converter = time.gmtime

    return logger
