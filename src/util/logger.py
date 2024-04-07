import logging

logger = logging.getLogger('kinda-p4')
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '\r%(levelname)s: %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.propagate = False

logging.basicConfig(level=logging.WARNING)
