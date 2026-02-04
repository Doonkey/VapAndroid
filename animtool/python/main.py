import sys
import os
from anim_tool import AnimTool, IToolListener
from common_arg import CommonArg


class Main:  # Helper class not really used, script runs via run()
    pass


class ConsoleToolListener(IToolListener):
    def __init__(self, common_arg):
        self.common_arg = common_arg

    def on_progress(self, progress):
        p = int(progress * 100)
        # Match Make4K output format
        print(f"onProgress: {min(p, 99)}%")

    def on_warning(self, msg):
        print(f"onWarning: {msg}", file=sys.stderr)

    def on_error(self):
        print("onError!!!!!!!!", file=sys.stderr)
        sys.exit(1)

    def on_complete(self):
        print(f"onComplete: {self.common_arg.output_path}")


def run(args_list=None):
    import argparse

    parser = argparse.ArgumentParser(description="AnimTool Python Port (Make4K)")

    parser.add_argument("-i", "--input", required=True, help="Input directory path")
    parser.add_argument(
        "-f", "--ffmpeg", default="ffmpeg", help="FFmpeg executable path"
    )
    parser.add_argument(
        "-m", "--mp4edit", default="mp4edit", help="Mp4edit executable path"
    )

    # H265 handling: default True, support --no-h265
    parser.add_argument("--h265", dest="h265", action="store_true", help="Enable H265")
    parser.add_argument(
        "--no-h265", dest="h265", action="store_false", help="Disable H265"
    )
    parser.set_defaults(h265=True)

    parser.add_argument(
        "-b", "--bitrate", type=int, default=15000, help="Bitrate (kbps)"
    )
    parser.add_argument("-fps", "--fps", type=int, default=25, help="FPS")
    parser.add_argument(
        "-fkps", "--force_key_frames", default="0.000", help="Force key frames"
    )

    # Optional output path (not in Make4K params but useful)
    parser.add_argument("-o", "--output", help="Output directory")

    args = parser.parse_args(args_list)

    # Print call params matching output
    print(f"call inputFile{args.input}")
    print(f"call ffmpegCmd{args.ffmpeg}")
    print(f"call mp4editCmd{args.mp4edit}")
    print(
        f"call enableH265{str(args.h265).lower()}"
    )  # Java prints lowercase true/false
    print(f"call bitrate{args.bitrate}")
    print(f"call fps{args.fps}")
    print(f"call forceKeyFrames{args.force_key_frames}")

    common_arg = CommonArg()
    common_arg.input_path = args.input
    common_arg.ffmpeg_cmd = args.ffmpeg
    common_arg.mp4edit_cmd = args.mp4edit
    common_arg.enable_h265 = args.h265
    common_arg.bitrate = args.bitrate
    common_arg.fps = args.fps
    common_arg.force_key_frames = args.force_key_frames

    if args.output:
        common_arg.output_path = args.output

    tool = AnimTool()
    tool.set_tool_listener(ConsoleToolListener(common_arg))
    tool.create(common_arg, True)


if __name__ == "__main__":
    run()
