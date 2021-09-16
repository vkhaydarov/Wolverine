from src.datalogger import DataLogger
from yaml import safe_load
import logging

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s.%(msecs)03d [%(levelname)s] %(module)s.%(funcName)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)

    # Import and validate config
    with open('config.yaml') as config_file:
        cfg = safe_load(config_file)

    data_logger = DataLogger(cfg)
    data_logger.start()
