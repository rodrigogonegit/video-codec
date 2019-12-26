import math
from bit_stream import BitStream, OpenMode
import binascii
import os
import logging


class GolombEncoder(object):
    """
        Implements the Golomb encoder
    """
    __input_file = None
    __output_file = None
    __input_file_size = -1

    def __init__(self, input_file, output_file):
        """Initializes the GolombEncoder object
        
        Arguments:
            input_file {BitStream} -- BitStream object representing the intput file
            output_file {BitStream} -- BitStream object representing the output file
        """
        if input_file != None:
            self.__input_file = input_file

        self.__output_file = output_file

        self.__logger = logging.getLogger(__name__)
        self.__logger.debug('TESTE GOLOMB HUEHUEHU')
        # Open file handlers
        # if input_file_path != None:
        #     self.__input_file = BitStream(input_file_path, OpenMode.READ)

        # self.__output_file = BitStream(output_file_path, OpenMode.WRITE)

        # if input_file_path != None:
            # self.__input_file_size = os.stat(input_file_path).st_size

    def close(self):
        """

        :return:
        """
        # Open file handlers
        if self.__input_file != None:
            self.__input_file.close()

        self.__output_file.close()

    def encode_input_file(self, m, report_progress_callback=None):
        """
        :return:
        """
        self.__output_file.set_padding_mode(False)
        # Write header to output file. TODO: write header specification
        # self.__output_file.write_int(m, 4)
        self.write_int(m)

        i = self.__input_file.read_int(1)
        counter = 0.0

        while i != None:

            if report_progress_callback:
                report_progress_callback(counter/self.__input_file_size*100.0)
            # ...
            self.golomb_encode(i, m)
            i = self.__input_file.read_int(1)
            counter = counter + 1

        self.__input_file.close()
        self.__output_file.close()

    def encode_value(self, input, m):
        if input >= 0:
            self.__output_file.write_bit(0)

        else:
            self.__output_file.write_bit(1)
            input = input * -1
        
        b = int(math.ceil(math.log(m, 2)))
        q = int(math.floor(input / m))
        r = input - q * m

        # Calculate the fist bits with the use o q parameter, with unitary code
        # example: q = 3 -> first = 1110
        str_repr = ''

        for i in range(q):
            self.__output_file.write_bit(1)
            str_repr += '1'

        self.__output_file.write_bit(0)
        str_repr += '0'
        encode = int(math.pow(2, b) - m)

        binary_representation_with_fixed_len = None

        # Caso o valor de r seja menor que (2^b)-m vamos usar b-1 bits para representar esses valores
        if (r < encode):
            using_bits = b - 1
            binary_representation_with_fixed_len = ("{0:0" + str(using_bits) + "b}").format(r)

            for c in binary_representation_with_fixed_len:
                self.__output_file.write_bit(int(c))

        # Caso o contrario utiliza-se b bits de r+(2^b)-m para representar os restantes
        else:

            using_bits = b
            x = int(r + math.pow(2, b) - m)

            binary_representation_with_fixed_len = ("{0:0" + str(using_bits) + "b}").format(x)

            for c in binary_representation_with_fixed_len:
                self.__output_file.write_bit(int(c))

        return str_repr + binary_representation_with_fixed_len

    def decode(self, m, values_count,report_progress_callback=None, returnList=False):
        """Decodes the input file and returns or writes the values
        
        Arguments:
            m {int} -- Golomb Coder parameter
            values_count {int} -- how many values you want to decode. If you fedd it -1, everything will be read.
        
        Keyword Arguments:
            report_progress_callback {lambda} -- callback reporting progress (default: {None})
            returnList {bool} -- if set, the result will not be written to file, but instead return as a list (default: {False})
        
        Returns:
            [Boolean or List] -- returns Boolean in file writing mode and list otherwise
        """
        if self.__input_file.has_reached_eof():
            print('EOF REACHED!')
            return False
        
        # Open file handlers
        # self.__output_file.set_padding_mode(True)
        b = math.ceil(math.log(m, 2))  # ceil ( log2 (m) )
        decode = int(math.pow(2, b) - m)

        counter = 0.0

        rtn_list = []
        expected_num_of_values = 0

        while int(values_count - counter) != 0:
            num_of_ones = 0

            if report_progress_callback:
                report_progress_callback(counter/self.__input_file_size*100.0)

            signal_bit = self.__input_file.read_bit()

            # Should not happen. But, sanity.
            if signal_bit == -1:
                self.__logger.warning('Got -1 on reading signal bit. SHOULD NOT HAPPEN.')
                break

            bit = self.__input_file.read_bit()

            while bit == 1:
                num_of_ones = num_of_ones + 1
                bit = self.__input_file.read_bit()

            # If this happened, we have reached the end of the stream without a unary terminating 0
            if bit == -1:
                break

            num_of_bits_to_read = b - 1

            x = self.__input_file.read_n_bits(num_of_bits_to_read)

            if x == None or x == '':
                break

            int_x = int(x, 2)

            result = -1
            if int_x < decode:
                result = num_of_ones * m + int_x

            else:
                int_x = int_x * 2 + self.__input_file.read_bit()
                result = num_of_ones * m + int_x - decode

            if signal_bit == 1:
                result = result * -1

            if not returnList:
                self.__output_file.write_int(result, 1)

            else:
                rtn_list.append(result)

            counter += 1

        if returnList:
            return rtn_list
        
        else:
            return True
