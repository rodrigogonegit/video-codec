import math
import os
import time
import numpy as np
from yuv_player import YuvDecoder
import argparse
import golomb 
import cv2 as cv
from bit_stream import BitStream, OpenMode
import logging
from colorama import Fore
from time_perf import set_ref_time, get_delta

parser = argparse.ArgumentParser()
parser.add_argument("action", choices=[
					'enc', 'dec'], help="set the input file")
parser.add_argument("input_file", help="set the input file")

args = parser.parse_args()

def get_pixel_value(plane, x, y):
	"""
		Returns the pixel value at coordinates X, Y from the specified plane
	Arguments:
		plane {nparray} -- [description]
		x {integer} -- [description]
		y {integer} -- [description]
	
	Returns:
		integer-- pixel value on plane
	"""
	if x < 0 or y < 0 or x > plane.shape[0] or y > plane.shape[1] - 1:
		return 0

	return plane[x, y]


class JpegLs(object):
	__output_file = None
	__m_param = 128
	__pixels_out = open('out_pixels.txt', 'w')


	def __init__(self, input_file_path):
		"""
			Initializes a JPEG-LS encoder object
		"""
		self.__input_file_path = input_file_path
		self.__output_file_path = input_file_path + "_" + args.action

		log_fmt_string = '[%(asctime)s]{}[%(levelname)s]{} (%(module)s): %(message)s'.format(
			Fore.BLUE,
			Fore.RESET
		)

		logging.basicConfig(format=log_fmt_string, datefmt='%H:%M:%S', level=logging.DEBUG)
		self.__logger = logging.getLogger(__name__)
		self.__logger.setLevel(logging.DEBUG)
		self.__logger.debug('Initialized JPEG-LS codec with {}'.format(self.__input_file_path))
		np.seterr(over='ignore')
		return

	def encode_file(self):
		"""

		:return:
		"""
		# Open yuv file
		self.__yuv_file = YuvDecoder(self.__input_file_path)

		# Open output file-object
		self.__output_file_stream = BitStream(self.__output_file_path, OpenMode.WRITE)

		# We want padding with zeros because of Golomb
		self.__output_file_stream.set_padding_mode(True)

		print('Encoded file:', self.__output_file_path)

		# Write some header information
		self.__output_file_stream.write_int(self.__yuv_file.frame_width, 4)
		self.__output_file_stream.write_int(self.__yuv_file.frame_height, 4)
		type_dict = {'4:4:4': 0, '4:2:2': 1, '4:2:0': 2}
		self.__output_file_stream.write_int(type_dict[self.__yuv_file.color_space], 4)
		self.__output_file_stream.write_int(self.__yuv_file.number_of_frames, 4)
		self.__output_file_stream.write_int(len(self.__yuv_file.raw_header), 4)
		self.__output_file_stream.write_int(self.__m_param, 4)

		# Start of actual content. Write unmodified original header to encoded file.
		self.__output_file_stream.write_bytes(self.__yuv_file.raw_header)

		counter = 1
		set_ref_time()

		while True:
			self.__logger.info(f'Processing frame: #{counter} of {self.__yuv_file.number_of_frames}')
			
			y, u, v, ret = self.__yuv_file.read_frame()
			if not ret:
				break

			get_delta()
			self.encode_frame(y, u, v)
			counter += 1

		original_file_size = os.stat(self.__input_file_path).st_size
		encoded_file_size = os.stat(self.__output_file_path).st_size

		print('Compression ratio: ', round(

			encoded_file_size / original_file_size * 100.0, 2))

		# DO NOT FORGET TO CLOSE. Otherwise the last byte might not get written.
		self.__output_file_stream.close()

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
		# self.__logger.debug('Rel time: ' + str(get_delta()))
		get_delta()

		# start = time.time()
		# self.__logger.debug(f'Avg Y: {avg_y} || U: {avg_u} || V {avg_u}')
		# self.__m_param = math.floor(math.log(avg_y, 2))
		# self.__output_file.write_int(self.__m_param)
		self.encode_plane(y_plane)
		# self.__logger.debug('Y plane processing time: {}'.format(round(time.time() - start, 2)))
		# self.__m_param = math.floor(math.log(avg_u, 2))
		# self.__output_file.write_int(self.__m_param)
		self.encode_plane(u_plane)

		# self.__m_param = math.floor(math.log(avg_v, 2))
		# self.__output_file.write_int(self.__m_param)
		self.encode_plane(v_plane)

	def encode_plane(self, plane):
		"""

		:param plane:
		:return:
		"""
		row_times = []
		# A - left pixel, B - top pixel, C - top left pixel, D - top right
		for row in range(0, plane.shape[0]):
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
				
				# self.__residual_txt_file.write(str(residual) + ' ')
				# self.__output_golomb_obj.encode_value(residual, self.__m_param)
				encoded_val = golomb.encode(residual, self.__m_param)
				self.__output_file_stream.write_n_bits(encoded_val)

			# self.__residual_txt_file.write('\n')
			
		# self.__logger.debug('Average row processing time:{}'.format(round(sum(row_times) / len(row_times) * 100, 2), " Len:", len(row_times)))

	def decode_file(self):
		# width = 352
		# height = 288
		# color_space = '4:2:0'
		self.__input_file_stream = BitStream(self.__input_file_path, OpenMode.READ)
		self.__output_file_stream = BitStream(self.__output_file_path, OpenMode.WRITE)

		# golomb_obj = GolombEncoder(self.__input_file_stream,
		# 				  self.__output_file_stream)

		self.frame_width = self.__input_file_stream.read_int(4)
		self.frame_height = self.__input_file_stream.read_int(4)
		self.color_space_int = self.__input_file_stream.read_int(4)
		self.frame_count = self.__input_file_stream.read_int(4)
		
		# This header is the unprocessed, raw YUV header
		self.size_of_header = self.__input_file_stream.read_int(4)
		self.m_param = self.__input_file_stream.read_int(4)

		self.header = self.__input_file_stream.read_bytes(self.size_of_header)

		# WRite header to output file
		self.__output_file_stream.write_bytes(bytes(self.header))
		# print('HEADER: ', bytes(header).decode('utf-8'))
		type_dict = {0: '4:4:4', 1: '4:2:2', 2: '4:2:0'}

		self.color_space = type_dict[self.color_space_int]
		self.__logger.info(f'Frame Width:\t{self.frame_width}')
		self.__logger.info(f'Frame Height:\t{self.frame_height}')
		self.__logger.info(f'Color Space:\t{self.color_space}')
		self.__logger.info(f'# of Frames:\t{self.frame_count}')
		self.__logger.info(f'Decoding. Output file:\t{self.__output_file_path}')

		# Calculate expected number of golomb values
		expected_values_per_frame = 0
		uv_planes_rows = self.frame_height
		uv_planes_cols = self.frame_width 

		if self.color_space_int == 0:
			expected_values_per_frame = self.frame_width * self.frame_height * 3
			# Do not change uv_planes_rows and counts since there is no downsampling

		elif self.color_space_int == 1:
			expected_values_per_frame = self.frame_width * self.frame_height * 2
			uv_planes_cols = int(uv_planes_cols / 2)

		elif self.color_space_int == 2:
			expected_values_per_frame = self.frame_width * self.frame_height * 3 / 2
			uv_planes_cols = int(uv_planes_cols / 2)
			uv_planes_rows = int(uv_planes_rows / 2)

		self.__logger.debug('Values per frame: {}'.format(expected_values_per_frame))
		self.__logger.debug(f'UV components size: {uv_planes_rows}x{uv_planes_cols}: {uv_planes_cols * uv_planes_rows} samples')


		for i in range(1, self.frame_count+1):
			self.__logger.info(f'Processing frame number {i} of {self.frame_count} ')

			self.__output_file_stream.write_str('FRAME\n')

			golomb_values = golomb.decode(self.m_param, self.frame_width * self.frame_height, self.__input_file_stream)
			# Y plane
			self.decode_plane(self.frame_height, self.frame_width, golomb_values)

			# U plane
			golomb_values = golomb.decode(self.m_param, uv_planes_cols * uv_planes_rows, self.__input_file_stream)
			self.decode_plane(uv_planes_rows, uv_planes_cols, golomb_values)

			# V plane
			golomb_values = golomb.decode(self.m_param, uv_planes_cols * uv_planes_rows, self.__input_file_stream)
			self.decode_plane(uv_planes_rows, uv_planes_cols, golomb_values)

		self.__logger.info('Processed all frames.')
		# with open('check_residuals.txt', 'w') as f:
		# 	for t in golomb_values:
		# 		f.write(str(t) + ' ')

		self.__pixels_out.close()

	def decode_plane(self, row_count, col_count, plane_residuals):			
		residuals_plane = np.asarray(plane_residuals, dtype=np.uint8)
		residuals_plane.shape = (row_count, col_count)

		decoded_frame = np.zeros((row_count, col_count), dtype=np.uint8)


		for row in range(0, row_count):
			for col in range(0, col_count):
				residual = get_pixel_value(residuals_plane, row, col)
				A = get_pixel_value(decoded_frame, row, col - 1)
				B = get_pixel_value(decoded_frame, row - 1, col)
				C = get_pixel_value(decoded_frame, row - 1, col - 1)
				D = get_pixel_value(decoded_frame, row - 1, col + 1)

				pred_x = -1

				if C >= max(A, B):
					pred_x = min(A, B)

				elif C <= min(A, B):
					pred_x = max(A, B)

				else:
					pred_x = A + B - C

				pixel_value = residual + pred_x
				decoded_frame[row, col] = pixel_value

				self.__output_file_stream.write_int(pixel_value.item(), 1)
		

j = JpegLs(args.input_file)

if args.action == 'enc':
	j.encode_file()

elif args.action == 'dec':
	j.decode_file()
