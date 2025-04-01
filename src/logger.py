import logging
from datetime import datetime
import os
import zipfile

# -------------- CONFIG ----------------
LOG_FOLDER = "logs"
CURRENT_LOG_FILE = "currentlog.txt"
MAX_FILE_SIZE_MB = 10 # Max size before archivation in MB
LINES_TO_KEEP = 10   # How many lines of the old log is stored in the new log prior to archivation
MAX_ARCHIVES = 10   # Change to set max num of archived files

os.makedirs(LOG_FOLDER, exist_ok=True) # Creates log folder if there isnt one

class CustomFormatter(logging.Formatter):
    def format(self, record):
        timestamp = datetime.now().strftime('%d:%m  %H:%M:%S:%f')[:-3] # Timestamp format (dd:mm  HH:MM:SS:ms)
        level = f"({record.levelname})".ljust(10)
        message = record.getMessage() 
        return f"{timestamp}    {level}  {message}"  # The message format

def archive_log():
    current_log_path = os.path.join(LOG_FOLDER, CURRENT_LOG_FILE) 
    if not os.path.exists(current_log_path): 
        return 

    if os.path.getsize(current_log_path) < MAX_FILE_SIZE_MB * 1024 * 1024:  # Check if file is less than 10mb. Remove one *1024 if you want kb instead
        return

    with open(current_log_path, "r") as log_file: 
        lines = log_file.readlines() 
    last_lines = lines[-LINES_TO_KEEP:] # Keeps last x lines (set in config, its 10 rn)

    start_date = lines[0].split()[0].replace(":", ".")  # Gets the date from the first line for filename
    end_date = datetime.now().strftime('%d.%m-%H_%M_%S') # Gets the time and date from the last line for filename 
    archive_name = f"log_{start_date}-{end_date}.zip"  # Creates the archive name in log_dd.mm-dd.mm-hh_mm_ms format, e.g "log_01.01-12_00_00.zip" 
    archive_path = os.path.join(LOG_FOLDER, archive_name) 

    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(current_log_path, CURRENT_LOG_FILE)

    os.remove(current_log_path) # Deletes log after archiving to make new one

    with open(current_log_path, "w") as new_log_file:
        new_log_file.writelines(last_lines) # Writes the last x lines to the new log file

    archives = sorted(
        [f for f in os.listdir(LOG_FOLDER) if f.endswith(".zip")],
        key=lambda x: os.path.getctime(os.path.join(LOG_FOLDER, x))
    )
    while len(archives) > MAX_ARCHIVES:
        os.remove(os.path.join(LOG_FOLDER, archives.pop(0))) # Deletes the oldest archive if there are more than MAX_ARCHIVES

logger = logging.getLogger()
logger.setLevel(logging.INFO)

current_log_path = os.path.join(LOG_FOLDER, CURRENT_LOG_FILE)
file_handler = logging.FileHandler(current_log_path)
file_handler.setFormatter(CustomFormatter())
logger.addHandler(file_handler)

def log_event(message: str, level: str = 'info'): # Log levels
    archive_log()
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