import argparse
from video_player import VideoPlayer

parser = argparse.ArgumentParser()
parser.add_argument("input_file", help="set the input file")

args = parser.parse_args()
#
v = VideoPlayer(args.input_file)
v.close()
# v.play_video()
