import logging
import cv2 as cv
from struct import *
import re

import numpy as np


class VideoPlayer(object):
    """
    """

    __logger = None
    __input_file_path = None
    __header_string = ''
    __frame_width = 0
    __frame_height = 0
    __fps = 0
    __interlacing_mode = 0
    __pixel_aspect_ratio = 0
    __color_space = 0

    __header_params = {}

    def __init__(self, input_file_path):
        """
            Creates a video player object with the specified input file path
        """
        logging.basicConfig(format='[%(levelname)s][%(asctime)s]=> %(message)s', datefmt='%H:%M:%S')
        self.__logger = logging.getLogger(__name__)
        self.__input_file_path = input_file_path
        self.__file_object = open(self.__input_file_path, 'rb')
        self.__read_header()

    def close(self):
        """
            Attempts to gracefully close all opened resources
        :return:
        """
        self.__file_object.close()

    def __read_header(self):
        """
            Reads the header of the YUV file
        :return:
        """
        # According to YUV spec, first
        self.__header_string = self.__file_object.read(10).decode('utf-8').replace(' ', '')

        if self.__header_string == 'YUV4MPEG2':
            # self.__logger.critical('Recognized format')
            print('Header:\t\t', self.__header_string)

        else:
            self.__logger.critical(f'Unrecognized format: {self.__header_string}! Aborting...')
            self.close()
            return

        header_string = ''

        # TODO: should refactor all of this.
        char = self.__file_object.read(1).decode('utf-8')

        while True:
            header_string += char

            if 'FRAME' in header_string:
                break

            char = self.__file_object.read(1).decode('utf-8')

        # Save position of where the first FRAME raw data starts
        # Remember the format: HEADER FRAME [__first_frame_position points here] raw_data FRAME raw_data (...)
        self.__first_frame_position = self.__file_object.tell()

        # Ignore First letter
        self.__header_params['frame_width'] = int(re.findall('W\d+', header_string)[0][1:])
        self.__header_params['frame_height'] = int(re.findall('H\d+', header_string)[0][1:])
        self.__header_params['frame_rate'] = re.findall('F\d+\:\d+', header_string)[0][1:]

        # Calculate actual frame rate given the value is a ratio
        tokens = [int(d.replace(' ', '')) for d in self.__header_params['frame_rate'].split(':')]
        self.__header_params['frame_rate'] = round(tokens[0] / tokens[1], 1)

        self.__header_params['pixel_aspect_ratio'] = re.findall('A\d+\:\d+', header_string)[0][1:]

        # Calculate actual pixel aspect ratio rate given the value is a ratio
        tokens = [int(d.replace(' ', '')) for d in self.__header_params['pixel_aspect_ratio'].split(':')]
        self.__header_params['pixel_aspect_ratio'] = round(tokens[0] / tokens[1], 1)

        # Don't ignore for interlacing
        self.__header_params['interlacing'] = re.findall('I(p|t|b|m)', header_string)[0]

        try:

            self.__header_params['color_space'] = re.findall('C\d+', header_string)[0]
            self.determine_color_space_by_frame_size()

        except IndexError:
            self.__logger.critical(
                'Could not determine color from the file header! Trying to extrapolate by frame size!')
            self.determine_color_space_by_frame_size()

        # Color space parameter is missing?
        print('Input file:\t', self.__input_file_path)
        print('Frame size:\t', f'{self.__header_params["frame_width"]}x{self.__header_params["frame_height"]}')
        print('Frame rate:\t', f'{self.__header_params["frame_rate"]} FPS')
        print('Aspect Ratio:\t', self.__header_params['pixel_aspect_ratio'])
        print('Color Space:\t', self.__header_params['color_space'])

    def determine_color_space_by_frame_size(self):
        """
            Tries to extrapolate the sub-sampling method by the frame size
        :return:
        """
        possible_sub_sampling_methods = {}
        # Calculate 4:2:0 frame size
        possible_sub_sampling_methods['4:2:0'] = int(
            self.__header_params['frame_width'] * self.__header_params['frame_height'] * 3 / 2)

        # Calculate 4:2:2 frame size
        possible_sub_sampling_methods['4:2:2'] = int(
            self.__header_params['frame_width'] * self.__header_params['frame_height'] * 2)

        # Calculate 4:4:4 frame size
        possible_sub_sampling_methods['4:4:4'] = int(
            self.__header_params['frame_width'] * self.__header_params['frame_height'] * 3)

        for k, v in possible_sub_sampling_methods.items():
            # Move file pointer to beginning of first frame
            self.__file_object.seek(self.__first_frame_position)

            # Move file pointer to possible end of frame location (plus one to point to the [POSSIBLY] F in FRAME)
            self.__file_object.seek(v + 1, 1)

            try:
                # Read 5 bytes and check if it's == FRAME
                frm_header = self.__file_object.read(5)

                frm_header = frm_header.decode('utf-8')

                print(frm_header)

                if frm_header == 'FRAME':
                    self.__logger.critical(f'Color space is {k}')
                    self.__header_params['color_space'] = k
                    return v

            except:
                pass

        self.__logger.critical('Failed to extrapolate color space! Aborting...')
        return None

    def play_video(self):
        """
            Plays the video file specified in the object instantiation
        :return:
        """
        # cap = cv.VideoCapture(self.__input_file_path)

        # Determine how long we need to wait to comply with defined frame-rate
        # frame_interval = int(1000 / cap.get(cv.CAP_PROP_FPS))
        # num_of_frames = cap.get(cv.CAP_PROP_FRAME_COUNT)

        self.__logger.info(
            f'Playing video {self.__input_file_path} at {cap.get(cv.CAP_PROP_FPS)} ({frame_interval}ms between frames.')

        # width = cap.get(cv.CV_CAP_PROP_FRAME_WIDTH)   # float
        # height = cap.get(cv.CV_CAP_PROP_FRAME_HEIGHT) # float

        frame_counter = 0
        cv.namedWindow('frame', cv.WINDOW_NORMAL)

        while True:
            try:
                # Capture frame-by-frame
                # ret, frame = cap.read()

                if not ret or cv.waitKey(25) & 0xFF == ord('q'):
                    self.__logger.warning('Quitting')
                    break

                print(
                    str.format('\rPlaying: {:.1f} // Frame #: {} of {}', frame_counter / num_of_frames, frame_counter,
                               num_of_frames), end='')

                # Our operations on the frame come here
                # gray = cv.cvtColor(frame, cv.COLOR_BGRA2BGR)

                # Display the resulting frame
                cv.imshow('frame', frame)

                cv.waitKey(5)
                frame_counter += 1

            except Exception as e:
                self.__logger.critical('Exception occurred', exc_info=True)

    # input is an YUV numpy array with shape (height,width,3) can be uint,int, float or double,  values expected in the range 0..255
    # output is a double RGB numpy array with shape (height,width,3), values in the range 0..255
    def YUV2RGB(self, yuv):

        m = np.array([[1.0, 1.0, 1.0],
                      [-0.000007154783816076815, -0.3441331386566162, 1.7720025777816772],
                      [1.4019975662231445, -0.7141380310058594, 0.00001542569043522235]])

        rgb = np.dot(yuv, m)
        rgb[:, :, 0] -= 179.45477266423404
        rgb[:, :, 1] += 135.45870971679688
        rgb[:, :, 2] -= 226.8183044444304
        return rgb

# v = VideoPlayer('videos/ducks_take_off_420_720p50.y4m')
# v.close()
