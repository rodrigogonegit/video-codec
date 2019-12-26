import logging
import math
import re
import time
from threading import Thread

import cv2 as cv
import numpy as np


class YuvDecoder(Thread):
    frame_width = 0
    frame_height = 0
    frame_rate = 0
    number_of_frames = 0
    __pixel_aspect_ratio = 0
    color_space = 0
    __first_frame_raw_data_position = 0
    __frame_raw_data_size = 0
    __convert_to_bgr = False
    y_values = []
    u_values = []
    v_values = []

    def __init__(self, input_file_path, convert_to_bgr=False):
        """
            Initializes all the needed resources for the YUV decoder
        :param input_file_path:
        :param convert_to_bgr:
        """
        Thread.__init__(self)
        self.__logger = logging.getLogger(__name__)
        # self.__logger.setLevel(logging.DEBUG)
        self.__input_file_path = input_file_path
        self.__convert_to_bgr = convert_to_bgr
        self.__file_object = open(self.__input_file_path, 'rb')
        self.raw_header = self.__read_header()
        self.__calculate_number_of_frames()

        self.__stopped = False

        # Calculate number of frames

    def __calculate_number_of_frames(self):
        """
            Calculates the number of frames o file
        :return:
        """
        # Save current position
        current_pos = self.__file_object.tell()

        # Go to start of first frame
        self.__file_object.seek(self.__first_frame_raw_data_position)
        self.number_of_frames = 0

        while True:
            if not self.__file_object.read(self.__frame_raw_data_size):
                break

            self.__file_object.readline()
            self.number_of_frames += 1

        # Restore file pointer
        self.__file_object.seek(current_pos)
        print('Number of frames:', self.number_of_frames)

    def __read_header(self):
        """
            Interprets the header of the YUV file
        :return:
        """
        header = self.__file_object.readline()
        header_string = header.decode('utf-8')
        print(header_string)
        # Ignore first letter
        self.frame_width = int(re.findall('W\d+', header_string)[0][1:])
        self.frame_height = int(re.findall('H\d+', header_string)[0][1:])
        self.frame_rate = re.findall('F\d+\:\d+', header_string)[0][1:]

        # Calculate actual frame rate given the value is a ratio
        tokens = [int(d.replace(' ', '')) for d in self.frame_rate.split(':')]
        self.frame_rate = round(tokens[0] / tokens[1], 1)

        self.__pixel_aspect_ratio = re.findall('A\d+\:\d+', header_string)[0][1:]

        # Calculate actual pixel aspect ratio rate given the value is a ratio
        tokens = [int(d.replace(' ', '')) for d in self.__pixel_aspect_ratio.split(':')]
        self.__pixel_aspect_ratio = round(tokens[0] / tokens[1], 1)

        # Don't ignore for interlacing
        self.__interlacing_mode = re.findall('I(p|t|b|m)', header_string)[0]

        # Ignore first 'FRAME\n' terminator so the file object points to the first byte of raw data of the first frame
        self.__file_object.readline()

        self.__first_frame_raw_data_position = self.__file_object.tell()

        self.determine_color_space_by_frame_size()

        # Restore
        self.__file_object.seek(self.__first_frame_raw_data_position)

        return header

        # Color space parameter is missing?
        print('FourCC:\t\t', header_string[:4])
        print('Input file:\t', self.__input_file_path)
        print('Frame size:\t', f'{self.frame_width}x{self.frame_height}')
        print('Frame rate:\t', f'{self.frame_rate} FPS')
        print('Aspect Ratio:\t', self.__pixel_aspect_ratio)
        print('Color space\t', self.color_space)
        print('Frame size (raw data):', self.__frame_raw_data_size)
        print('Position of first raw:', self.__first_frame_raw_data_position)

    def determine_color_space_by_frame_size(self):
        """
            Tries to extrapolate the sub-sampling method by the frame size
        :return:
        """
        possible_sub_sampling_methods = {}
        # Calculate 4:2:0 frame size
        possible_sub_sampling_methods['4:2:0'] = int(
            self.frame_width * self.frame_height * 3 / 2)

        # Calculate 4:2:2 frame size
        possible_sub_sampling_methods['4:2:2'] = int(
            self.frame_width * self.frame_height * 2)

        # Calculate 4:4:4 frame size
        possible_sub_sampling_methods['4:4:4'] = int(
            self.frame_width * self.frame_height * 3)

        for k, v in possible_sub_sampling_methods.items():
            self.__logger.debug(f'Checking {k}')
            # Move file pointer to beginning of first frame
            self.__file_object.seek(self.__first_frame_raw_data_position)

            # Move file pointer to possible end of frame location
            self.__file_object.seek(v, 1)

            try:
                # Read 5 bytes and check if it's == FRAME
                frm_header = self.__file_object.read(5)

                frm_header = frm_header.decode('utf-8')

                self.__logger.debug(f'Read possible header string: {frm_header}')

                if frm_header.replace(' ', '') == 'FRAME':
                    self.__logger.info(f'Color space is {k}')
                    self.__logger.debug(f'Current file position is: {self.__file_object.tell()}')
                    self.color_space = k
                    self.__frame_raw_data_size = v
                    return v

            except UnicodeDecodeError:
                pass
                # self.__logger.debug('Exception on attempt to convert to UTF-8 data:', exc_info=True)

            # finally:
            # Reset file pointer to first byte of first frame raw data
            # self.__file_object.seek(self.__first_frame_raw_data_position)

        self.__logger.critical('Failed to extrapolate color space! Aborting...')
        return False

    def __get_next_yuv_frame(self):
        """
            Returns a buffer containing the next frame in the file
        :return:
        """
        raw_frame_buffer = self.__file_object.read(self.__frame_raw_data_size)

        # Ignore FRAME header
        self.__file_object.readline()
        return raw_frame_buffer

    def read_frame(self):
        """
            Reads the frame and returns NON-Converted (to 4:4:4) YUV planes
        :return: returns the reshaped Y, U, V planes. Shape depends on file sampling method.
        """
        buffer = self.__get_next_yuv_frame()
        if len(buffer) != self.__frame_raw_data_size:
            return None, None, None, False

        buf = np.frombuffer(buffer, dtype=np.uint8)

        plane_size = self.frame_height * self.frame_width

        uv_sizes_dict = {
            "4:4:4": plane_size,
            "4:2:2": int(plane_size / 2),
            "4:2:0": int(plane_size / 4),
        }

        y_plane = buf[0:plane_size]
        u_plane = buf[plane_size:plane_size + uv_sizes_dict[self.color_space]]
        v_plane = buf[plane_size + uv_sizes_dict[self.color_space]:plane_size + uv_sizes_dict[self.color_space] * 2]

        # Reshape planes
        y_plane.shape = (self.frame_height, self.frame_width)

        if self.color_space == '4:2:2':
            # Half the columns
            columns = math.ceil(self.frame_width / 2)

            u_plane.shape = (self.frame_height, columns)
            v_plane.shape = (self.frame_height, columns)

        elif self.color_space == '4:2:0':
            # Half the columns and half the rows
            columns = math.ceil(self.frame_width / 2)
            rows = math.ceil(self.frame_height / 2)

            u_plane.shape = (rows, columns)
            v_plane.shape = (rows, columns)

        elif self.color_space == '4:4:4':
            u_plane.shape = (self.frame_height, self.frame_width)
            v_plane.shape = (self.frame_height, self.frame_width)

        return y_plane, u_plane, v_plane, True

    def __concatenate_planes_to_444yuv_frame(self, y_plane, u_plane, v_plane):
        """
            Builds a YUV frame from the 3 planes
        :return: numpy array representing RGB image
        """
        np.set_printoptions(formatter={'int': hex})

        y_plane.shape = (self.frame_height, self.frame_width, 1)
        u_plane.shape = (self.frame_height, self.frame_width, 1)
        v_plane.shape = (self.frame_height, self.frame_width, 1)

        yuv = np.concatenate((y_plane, u_plane, v_plane), axis=2)

        # Use OpenCV to convert color since the implementation is MUCH faster
        if self.__convert_to_bgr:
            yuv = cv.cvtColor(yuv, cv.COLOR_YUV2BGR)

        return yuv

    def __extract_yuv_planes(self, frame_buffer):
        """
            Splits incoming frame buffer into YUV planes, converting the input to 4:4:4 format
        :return:
        """
        buf = np.frombuffer(frame_buffer, dtype=np.uint8)

        plane_size = self.frame_height * self.frame_width

        uv_sizes_dict = {
            "4:4:4": plane_size,
            "4:2:2": int(plane_size / 2),
            "4:2:0": int(plane_size / 4),
        }

        y_plane = buf[0:plane_size]
        u_plane = buf[plane_size:plane_size + uv_sizes_dict[self.color_space]]
        v_plane = buf[plane_size + uv_sizes_dict[self.color_space]:plane_size + uv_sizes_dict[self.color_space] * 2]

        if self.color_space == '4:2:2':
            u_plane = np.repeat(u_plane, 2)
            v_plane = np.repeat(v_plane, 2)

        elif self.color_space == '4:2:0':
            u_plane.shape = (int(self.frame_height / 2), int(self.frame_width / 2))
            v_plane.shape = (int(self.frame_height / 2), int(self.frame_width / 2))

            u_plane = np.repeat(u_plane, 2, axis=0).repeat(2, axis=1)
            v_plane = np.repeat(v_plane, 2, axis=0).repeat(2, axis=1)

        return y_plane, u_plane, v_plane

    def next_frame(self):
        """
            Gets the next frame from the stream as RGB. Returns (False, None) if EOF.
        :return:
        """
        while True:
            if self.grabbed:
                buffer = self.__get_next_yuv_frame()
                if len(buffer) != self.__frame_raw_data_size:
                    self.frame = False, False
                    self.stopped = True
                    break

                y, u, v = self.__extract_yuv_planes(buffer)

                # Save YUV planes now because they will be reshaped from (height, width) to (height, width, 1)

                converted_frame = self.__concatenate_planes_to_444yuv_frame(y, u, v)

                self.frame = True, converted_frame
                self.grabbed = False

            if self.stopped:
                break

            time.sleep(1/1000)

    def get_frame(self):
        self.grabbed = True
        return self.frame

    def run(self):
        self.stopped = False
        self.grabbed = True
        self.next_frame()

    def close(self):
        """
            Gracefully closes the resources
        :return:
        """
        self.__file_object.close()


class YuvPlayer(object):
    def __init__(self, input_file_path, convert_to_bgr=False):
        """
            Creates a video player object with the specified input file path
        """
        self.__yuv_video = YuvDecoder(input_file_path, convert_to_bgr=True)
        print('After INSTANTIATION')
        self.__yuv_video.start()

    def play_video(self):
        """
            Plays the specified stream
        :return:
        """
        cv.namedWindow('Planes', cv.WINDOW_NORMAL)
        cv.resizeWindow('Planes', self.__yuv_video.frame_width, self.__yuv_video.frame_height)

        inter_frame_delay = int(1000 / self.__yuv_video.frame_rate)

        while True:
            (ret, frame) = self.__yuv_video.get_frame()

            if not ret:
                break

            cv.imshow('Planes', frame)
            cv.waitKey(0)

        self.__yuv_video.join()

    def avg_list(self, lst):
        return round(sum(lst) / len(lst) * 1000, 2)

# v = YuvPlayer('videos/ducks_take_off_444_720p50.y4m', convert_to_bgr=True)
# v.play_video()
