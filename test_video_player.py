import argparse
from video_player import VideoPlayer
from yuv_player import YuvPlayer

parser = argparse.ArgumentParser()
parser.add_argument("input_file", help="set the input file")

args = parser.parse_args()
#
v = YuvPlayer(args.input_file, convert_to_bgr=True)
v.play_video()
