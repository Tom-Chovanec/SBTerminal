import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': datetime.now().strftime('%d/%m_%H:%M:%S'),
            'level': record.levelname,
            'message': record.getMessage()
        }
        return json.dumps(log_record)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler('app.json')
file_handler.setFormatter(JSONFormatter())

logger.addHandler(file_handler)

def log_event(message: str, level: str = 'info'):
    if level == 'info':
        logger.info(message)
    elif level == 'warning':
        logger.warning(message)
    elif level == 'error':
        logger.error(message)
    elif level == 'debug':
        logger.debug(message)
    else:
        logger.info(message)