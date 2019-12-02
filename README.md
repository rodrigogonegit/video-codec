**What is this?**

YUV files handler and video-player. An attempt at partially implementing the JPEG-LS standard.

**How to install:**

1 - Clone or download the repository and cd into it

2 - Run: `pipenv sync`

3 - Run: `pipenv shell`

**How to run JPEG-LS module:**

`python3 jpeg_ls.py [enc/dec] [input_file]`

The resulting encoded or decoded files will have the input_file name with the action appended to it (eg: flowers.yuv_enc)

**How to run the video_player:**

`python3 video_player.py [input_file] `