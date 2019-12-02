import math
import os
import time
import numpy as np
from yuv_player import YuvDecoder
import argparse
from golomb import GolombEncoder
import cv2 as cv

parser = argparse.ArgumentParser()
parser.add_argument("input_file", help="set the input file")

args = parser.parse_args()


def get_pixel_value(plane, x, y):
    if x < 0 or y < 0 or x > plane.shape[0] or y > plane.shape[1] - 1:
        return 0

    return plane[x, y]


class JpegLs(object):
    __output_file = None

    def __init__(self, input_file_path):
        """
            Initializes a JPEG-LS encoder object
        """
        self.__input_file_path = input_file_path
        self.__encoded_file_path = input_file_path + '_encoded'

    def encode_file(self):
        """

        :return:
        """
        self.__yuv_file = YuvDecoder(self.__input_file_path)
        self.__output_file = GolombEncoder(None, self.__encoded_file_path)
        print('Encoded file:', self.__encoded_file_path)
        self.__output_file.write_int(self.__yuv_file.frame_width)
        self.__output_file.write_int(self.__yuv_file.frame_height)
        # 0 = 4:4:4, 1 = 4:2:2, 2 = 4:2:0
        type_dict = {'4:4:4': 0, '4:2:2': 1, '4:2:0': 2}
        self.__output_file.write_int(type_dict[self.__yuv_file.color_space])
        # self.__output_file.write_header(128)

        counter = 0
        while True:
            y, u, v, ret = self.__yuv_file.read_frame()
            # print(y.shape)
            if not ret:
                break

            print('\rProgress:', round(counter / self.__yuv_file.number_of_frames * 100, 2), end='')
            self.encode_frame(y, u, v)
            counter += 1

        original_file_size = os.stat(self.__input_file_path).st_size
        encoded_file_size = os.stat(self.__encoded_file_path).st_size

        print('Compression ratio: ', round(encoded_file_size / original_file_size * 100.0, 2))
    __m_param = 0
    def encode_frame(self, y_plane, u_plane, v_plane):
        """

        :param y_plane:
        :param u_plane:
        :param v_plane:
        :return:
        """
        avg_y = np.average(y_plane)
        avg_u = np.average(u_plane)
        avg_v = np.average(v_plane)

        self.__m_param = math.floor(math.log(avg_y, 2))
        self.__output_file.write_int(self.__m_param)
        self.encode_plane(y_plane)

        self.__m_param = math.floor(math.log(avg_u, 2))
        self.__output_file.write_int(self.__m_param)
        self.encode_plane(u_plane)

        self.__m_param = math.floor(math.log(avg_v, 2))
        self.__output_file.write_int(self.__m_param)
        self.encode_plane(v_plane)

    def encode_plane(self, plane):
        """

        :param plane:
        :return:
        """
        row_times = []
        # A - left pixel, B - top pixel, C - top left pixel, D - top right
        for row in range(0, plane.shape[0]):
            start = time.time()
            for col in range(0, plane.shape[1]):
                x = get_pixel_value(plane, row, col)
                A = get_pixel_value(plane, row, col - 1)
                B = get_pixel_value(plane, row - 1, col)
                C = get_pixel_value(plane, row - 1, col - 1)
                D = get_pixel_value(plane, row - 1, col + 1)

                pred_x = -1

                if C >= max(A, B):
                    pred_x = min(A, B)

                elif C <= min(A, B):
                    pred_x = max(A, B)

                else:
                    pred_x = A + B - C

                residual = x - pred_x

                self.__output_file.golomb_encode(residual, self.__m_param)

            t = time.time() - start
            row_times.append(t)
            # print(t * 1000)
            # print(residual)
            # cv.waitKey(0)

        print(round(sum(row_times) / len(row_times) * 100, 2))

    def decode_file(self):
        # width = 352
        # height = 288
        # color_space = '4:2:0'

        g = GolombEncoder(self.__input_file_path, self.__input_file_path + '_decoded')
        frame_width = g.read_int()
        frame_height = g.read_int()
        color_space_int = g.read_int()
        type_dict = {0: '4:4:4', 1: '4:2:2', 2: '4:2:0'}

        color_space = type_dict[color_space_int]
        print('Frame Width:\t', frame_width)
        print('Frame Height:\t', frame_height)
        print('Color Space:\t', color_space)
        golomb_values = g.decode(returnList=True)

        print(len(golomb_values))
        g.close()


j = JpegLs(args.input_file)
j.encode_file()
# j.decode_file()
