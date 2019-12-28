import math
from bit_stream import BitStream, OpenMode
import binascii
import os
import logging
from time_perf import get_delta

def __truncated_binary_encoding(n: int, b: int) -> str:
    """Return string representing given number in truncated binary encoding.
        n:int, number to convert to truncated binary encoding.
        b:int, maximal size.
    """
    k = math.floor(math.log2(b))
    u = (1 << k+1) - b
    return f"{{0:0{k}b}}".format(n if n < u else n+u)

def encode(input, m):
    signal_bit = '0'

    if input < 0:
        input = input * -1
        signal_bit = '1'

    write_str = signal_bit + "1"*(input // m) + "0" + __truncated_binary_encoding(input % m, m)

    return write_str

def decode(m, num_of_values_to_return, input_bit_stream):
    counter = 0
    rtn_list = []
    b = math.ceil(math.log(m, 2))  # ceil ( log2 (m) )
    decode = int(math.pow(2, b) - m)

    while int(num_of_values_to_return - counter) != 0:
        num_of_ones = 0

        # if report_progress_callback:
        #     report_progress_callback(counter/self.__input_file_size*100.0)

        signal_bit = input_bit_stream.read_bit()

        # Should not happen. But, sanity.
        if signal_bit == -1:
            # self.__logger.warning('Got -1 on reading signal bit. SHOULD NOT HAPPEN.')
            break

        bit = input_bit_stream.read_bit()

        while bit == 1:
            num_of_ones = num_of_ones + 1
            bit = input_bit_stream.read_bit()

        # If this happened, we have reached the end of the stream without a unary terminating 0
        if bit == -1:
            break

        num_of_bits_to_read = b - 1

        x = input_bit_stream.read_n_bits(num_of_bits_to_read)

        if x == None or x == '':
            break

        int_x = int(x, 2)

        result = -1
        if int_x < decode:
            result = num_of_ones * m + int_x

        else:
            int_x = int_x * 2 + input_bit_stream.read_bit()
            result = num_of_ones * m + int_x - decode

        if signal_bit == 1:
            result = result * -1

        rtn_list.append(result)

        counter += 1

    return rtn_list