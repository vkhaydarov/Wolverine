import requests
import base64
import cv2
import numpy as np
import logging
from time import time, sleep
from os import path, makedirs
import json
import threading


class DataLogger:
    def __init__(self, cfg: dict):
        """
        This class represents a data logger that requests images from PlantEye-Vision REST API endpoint and
        stores them locally.
        :param cfg:dict: Set of parameters of the data logger.
        """
        self.cfg = cfg

        self.__initialised = False
        self.__get_and_save_thread = None

        # Stop and exit flags
        self.__exit = False
        self.__stop = False

        self.__current_frame_id = 0

    def start(self):
        """
        Runs instance of the data logger.
        :return:
        """
        self.__stop = False
        self.__get_and_save_thread = threading.Thread(target=self.__get_and_save_loop, args=[])
        self.__get_and_save_thread.start()

    def stop(self):
        """
        Stops instance of the data logger.
        :return:
        """
        self.__stop = True
        sleep(self.cfg['storage']['interval'] / 1000.0)

    def __get_and_save_loop(self):
        """
        Method that requests, receives, formats and saves data.
        :return:
        """

        # Set initial time point
        cycle_begin = time() - self.cfg['storage']['interval'] / 1000.0

        while not self.__stop:

            logging.info('Loop step')

            # Calculate one cycle length
            cycle_begin = cycle_begin + self.cfg['storage']['interval'] / 1000.0

            # If last cycle lasted much longer, we need to skip the current polling cycle to catch up in the future
            if cycle_begin + 0.010 < time():
                logging.error('Capturing skipped (consider increasing interval)')
                continue

            begin_time = time()
            frame_data = self.__get_data_from_api()
            read_time = int((time() - begin_time)*1000)

            if frame_data is not None:
                begin_time = time()
                frame = convert_str_to_frame(frame_data['frame']['frame'])
                conversion_time = int((time() - begin_time) * 1000)

                filename = self.__get_filename(frame_data['timestamp'])

                begin_time = time()
                frame_saved = self.__save_frame(frame, filename)
                frame_save_time = int((time() - begin_time) * 1000)

                if frame_saved:
                    begin_time = time()
                    metadata_saved = self.__save_metadata(frame_data, filename)
                    if not metadata_saved:
                        self.__remove_last_saved_frame()
                    else:
                        self.__current_frame_id += 1
                    metadata_save_time = int((time() - begin_time) * 1000)
                else:
                    frame_save_time = 0
                    metadata_save_time = 0
            else:
                conversion_time = 0
                frame_save_time = 0
                metadata_save_time = 0

            total_time = int((time() - cycle_begin) * 1000)
            debug_str = 'Total execution time of receiving and saving frame %i ms (data receiving %i, conversion %i, image saving %i, metadata saving %i)' \
                        % (total_time, read_time, conversion_time, frame_save_time, metadata_save_time)
            logging.debug(debug_str)

            # Calculate real cycle duration
            cycle_dur = time() - cycle_begin

            # If the cycle duration longer than given and no connection issues, jump directly to the next cycle
            if cycle_dur > self.cfg['storage']['interval'] / 1000.0:
                logging.warning('Capturing takes longer ' + str(cycle_dur) + ' than given time intervals')
            else:
                # Calculate how long we need to wait till the begin of the next cycle
                sleep(max(self.cfg['storage']['interval'] / 1000.0 - (time() - cycle_begin), 0))

    def __get_data_from_api(self):
        """
        Method to get request data from an instance of PlantEye/Vision over REST API
        :return: Response of the PlantEye/Vision endpoint; None - if no data returned or the endpoint unavailable
        """
        api_endpoint = self.cfg['api']['endpoint'] + 'get_frame'
        try:
            resp = requests.get(api_endpoint)
        except requests.exceptions.ConnectionError:
            logging.error('Cannot establish connection to ' + self.cfg['api']['endpoint'])
            return None

        try:
            resp_data = resp.json()
        except Exception:
            logging.warning('Cannot deserialise received json %s' % resp)
            return None

        if resp_data['status']['code'] == 200:
            logging.info('Frame received')
            return resp_data
        else:
            logging.warning('No frame retrieved. Error %s API returned message %s'
                            % (resp_data['status']['code'], resp_data['status']['message']))
            return None

    def __get_filename(self, timestamp: int) -> str:
        """
        Generates a filename out of the timestamp value or out of the frame id if the filename mask specified.
        :param timestamp: int: Timestamp
        :return: str: Filename
        """
        if self.cfg['storage']['filename_mask'] == 'timestamp':
            return str(timestamp)
        else:
            return self.cfg['storage']['filename_mask'] + '%0*d' % (6, self.__current_frame_id)

    def __save_frame(self, frame, filename: str) -> bool:
        """
        Saves frame onto disk.
        :param frame:
        :param filename: str: Filename
        :return: bool: Status: True - if file is saved successfully; False - otherwise
        """

        filepath = ''

        try:
            filepath = path.join(self.cfg['storage']['frame_folder'])
            filename += '.png'
            fullname = path.join(filepath, filename)
        except:
            logging.error('Cannot concatenate saving path:' + filepath + ' ' + filename)
            return False

        if not path.isdir(filepath):
            logging.info('Saving directory %s does not exist' % filepath)
            try:
                makedirs(filepath)
                logging.info('Directory %s created' % filepath)
            except Exception:
                logging.info('Directory %s cannot be created, consider granting necessary rights' % filepath)
                return False

        try:
            ret = cv2.imwrite(fullname, frame)
            logging.info('Frame saved as ' + fullname)
            return True
        except:
            logging.error('Saving as ' + fullname + ' failed')
            return False

    def __remove_last_saved_frame(self):
        pass

    def __save_metadata(self, frame_data: dict, filename: str) -> bool:
        """
        Saves metadata in a json file
        :param frame_data: dict: Dictonary with metadata to the image file.
        :param filename: str: Filename for the metadata file.
        :return: bool: Status: True - if file is saved successfully; False - otherwise
        """
        begin_time = time()
        filepath = ''

        try:
            filepath = path.join(self.cfg['storage']['metadata_folder'])
            filename += '.json'
            fullname = path.join(filepath, filename)
        except:
            logging.error('Cannot concatenate saving path:' + filepath + ' ' + filename)
            return False

        if not path.isdir(filepath):
            logging.info('Saving directory %s does not exist' % filepath)
            try:
                makedirs(filepath)
                logging.info('Directory %s created' % filepath)
            except Exception:
                logging.info('Directory %s cannot be created, consider granting necessary rights' % filepath)
                return False

        try:
            with open(fullname, 'w') as outfile:
                data_to_save = {'metadata': frame_data['metadata'],
                                'labels': frame_data['labels'],
                                'timestamp': frame_data['timestamp']}
                json.dump(data_to_save, outfile, skipkeys=True, indent=4)
                logging.info('Metadata saved as ' + fullname)
        except:
            logging.error('Saving metadata as ' + fullname + ' failed')
            return False
        logging.debug('Execution time of metadata file writing ' + str(int((time() - begin_time) * 1000)) + ' ms')
        return True


def convert_str_to_frame(frame_str):
    # https://jdhao.github.io/2020/03/17/base64_opencv_pil_image_conversion/
    begin_time = time()
    frame_bytes = base64.b64decode(frame_str)
    frame_arr = np.frombuffer(frame_bytes, dtype=np.uint8)  # im_arr is one-dim Numpy array
    frame = cv2.imdecode(frame_arr, flags=cv2.IMREAD_COLOR)
    logging.debug('Execution time of string to frame conversion ' + str(int((time() - begin_time) * 1000)) + ' ms')
    return frame
