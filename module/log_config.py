# log_config.py
import logging
from module.utils import config
import os

# Set up logging
log_filename = config['production']['params_config']['log_dir']

# Check if the file exists, and create it if it doesn't
if not os.path.exists(log_filename):
    # Create the file
    print("File does not exist.")
    with open(log_filename, 'w') as file:
        file.write('')  # Create an empty fil

# Create a logger object
logger = logging.getLogger('project_logger')
logger.setLevel(logging.DEBUG)  # Adjust log level as needed

# Create a file handler to store logs in a file
file_handler = logging.FileHandler(log_filename)
file_handler.setLevel(logging.DEBUG)

# Create a formatter with time and file info
formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)
