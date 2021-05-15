import requests
import base64
import cv2
import numpy as np
import logging
import time
from os import path
import json
import threading

class DataLogger:
    def __init__(self, cfg):
        self.cfg = cfg

        self._initialised = False
        self._get_and_save_thread = None

        # Stop and exit flags
        self._exit = False
        self._stop = False

        self._current_frame_id = 0

    def start(self):
        self._stop = False
        self._get_and_save_thread = threading.Thread(target=self._get_and_save_loop, args=[])
        self._get_and_save_thread.start()

    def stop(self):
        self._stop = True
        time.sleep(self.cfg['storage']['interval'] / 1000.0)

    def _get_and_save_loop(self):

        # Set initial time point
        cycle_begin = time.time() - self.cfg['storage']['interval'] / 1000.0

        while not self._stop:

            logging.info('Loop step')

            # Calculate one cycle length
            cycle_begin = cycle_begin + self.cfg['storage']['interval'] / 1000.0

            # If last cycle lasted much longer, we need to skip the current polling cycle to catch up in the future
            if cycle_begin + 0.010 < time.time():
                logging.error('Capturing skipped (increase time interval)')
                continue

            frame_data = self._get_data_from_api()
            if frame_data is None:
                continue

            filename = self._get_filename()
            frame_saved = self._save_frame(frame_data, filename)
            if not frame_saved:
                continue

            metadata_saved = self._save_metadata(frame_data, filename)
            if not metadata_saved:
                self._remove_last_saved_frame()
                continue

            self._current_frame_id += 1

            if self._stop:
                break

            # Calculate real cycle duration
            cycle_dur = time.time() - cycle_begin

            # If the cycle duration longer than given and no connection issues, jump directly to the next cycle
            if cycle_dur > self.cfg['storage']['interval'] / 1000.0:
                logging.warning('Capturing takes longer ' + str(cycle_dur) + ' than given time intervals')
            else:
                # Calculate how long we need to wait till the begin of the next cycle
                time.sleep(max(self.cfg['storage']['interval'] / 1000.0 - (time.time() - cycle_begin), 0))

    def _get_data_from_api(self):
        api_endpoint = self.cfg['api']['endpoint'] + '/get_frame'
        try:
            response = requests.get(api_endpoint)
        except requests.exceptions.ConnectionError:
            logging.error('Cannot establish connection to ' + self.cfg['api']['endpoint'])
            return None

        resp_data = response.json()

        if resp_data['status']['code'] == 500:
            logging.warning('No frame retrieved. API returned message: ' + resp_data['status']['message'])
            return None

        if resp_data['status']['code'] == 200:
            logging.info('Frame received')

        return resp_data

    def _get_filename(self):
        return self.cfg['storage']['filename_mask'] + '%0*d' % (6, self._current_frame_id)

    def _save_frame(self, frame_data, filename):
        filepath = ''

        try:
            filepath = path.join(self.cfg['storage']['frame_folder'])
            filename += '.png'
            fullname = path.join(filepath, filename)
        except:
            logging.error('Cannot create saving path:' + filepath + ' ' + filename)
            return False

        frame = convert_str_to_frame(frame_data['frame']['frame'])

        try:
            ret = cv2.imwrite(fullname, frame)
            logging.info('Frame saved as ' + fullname)
            return True
        except:
            logging.error('Saving as ' + fullname + ' failed')
            return False

    def _remove_last_saved_frame(self):
        pass

    def _save_metadata(self, frame_data, filename):
        filepath = ''

        try:
            filepath = path.join(self.cfg['storage']['metadata_folder'])
            filename += '.json'
            fullname = path.join(filepath, filename)
        except:
            logging.error('Cannot create saving path:' + filepath + ' ' + filename)
            return False

        try:
            with open(fullname, 'w') as outfile:
                data_to_save = {'metadata': frame_data['metadata'], 'timestamp':frame_data['timestamp']}
                json.dump(data_to_save, outfile, skipkeys=True, indent=4)
                logging.info('Metadata saved as ' + fullname)
        except:
            logging.error('Saving metadata as ' + fullname + ' failed')
            return False

        return True

    def _create_folder(self):
        pass


def convert_str_to_frame(frame_str):
    # https://jdhao.github.io/2020/03/17/base64_opencv_pil_image_conversion/

    frame_bytes = base64.b64decode(frame_str)
    frame_arr = np.frombuffer(frame_bytes, dtype=np.uint8)  # im_arr is one-dim Numpy array
    frame = cv2.imdecode(frame_arr, flags=cv2.IMREAD_COLOR)
    return frame
