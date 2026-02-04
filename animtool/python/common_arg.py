# from vapx.src_set import SrcSet # Removed
# from vapx.frame_set import FrameSet # Removed
from data.point_rect import PointRect
from utils.log import TLog
# from anim_tool import AnimTool  # Removed to avoid circular import
import os
import math
from PIL import Image
import anim_tool

class CommonArg:
    def __init__(self):
        self.ffmpeg_cmd = "ffmpeg"
        self.mp4edit_cmd = "mp4edit"
        self.enable_h265 = True
        self.fps = 25
        self.force_key_frames = "0.000"
        self.input_path = ""
        self.scale = 1.0
        self.enable_crf = False
        self.bitrate = 15000
        self.crf = 29
        self.is_vapx = False
        
        self.output_path = ""
        self.frame_output_path = ""
        self.version = 2
        self.gap = 0
        self.total_frame = 0
        self.rgb_point = PointRect()
        self.alpha_point = PointRect()
        self.is_v_layout = False
        self.output_w = 0
        self.output_h = 0
        self.need_audio = False
        self.audio_path = ""


    def __str__(self):
        return (f"CommonArg{{ffmpegCmd='{self.ffmpeg_cmd}', mp4editCmd='{self.mp4edit_cmd}', "
                f"enableH265={self.enable_h265}, fps={self.fps}, enableCrf={self.enable_crf}, "
                f"bitrate={self.bitrate}, crf={self.crf}, scale={self.scale}, "
                f"inputPath='{self.input_path}', needAudio={self.need_audio}, "
                f"audioPath='{self.audio_path}'}}")

class CommonArgTool:
    TAG = "CommonArgTool"
    MIN_GAP = 0

    @staticmethod
    def auto_fill_and_check(common_arg, tool_listener=None):
        try:
            return CommonArgTool._auto_fill_and_check_logic(common_arg, tool_listener)
        except Exception as e:
            TLog.e(CommonArgTool.TAG, str(e))
            if tool_listener:
                tool_listener.on_error()
            return False

    @staticmethod
    def _auto_fill_and_check_logic(common_arg, tool_listener):
        os_name = os.name
        TLog.i(CommonArgTool.TAG, f"OS: {os_name}")

        if not common_arg.input_path:
            TLog.e(CommonArgTool.TAG, "input path invalid")
            return False

        if not os.path.exists(common_arg.input_path):
            TLog.e(CommonArgTool.TAG, f"input path invalid {common_arg.input_path}")
            return False

        if not common_arg.input_path.endswith(os.sep):
            common_arg.input_path += os.sep

        if common_arg.need_audio:
            if not common_arg.audio_path or not os.path.exists(common_arg.audio_path) or len(common_arg.audio_path) < 3:
                TLog.e(CommonArgTool.TAG, f"audio file not exists {common_arg.audio_path}")
                return False
            
            if not common_arg.audio_path.lower().endswith("mp3"):
                TLog.e(CommonArgTool.TAG, f"audio file must be mp3 file {common_arg.audio_path}")
                return False

        if not common_arg.output_path:
            common_arg.output_path = os.path.join(common_arg.input_path, anim_tool.AnimTool.OUTPUT_DIR)

        common_arg.frame_output_path = os.path.join(common_arg.output_path, anim_tool.AnimTool.FRAME_IMAGE_DIR)

        common_arg.scale = max(0.5, min(1.0, common_arg.scale))

        first_frame_path = os.path.join(common_arg.input_path, "000.png")
        if not os.path.exists(first_frame_path):
            TLog.e(CommonArgTool.TAG, "first frame 000.png does not exist")
            return False
            
        try:
            with Image.open(first_frame_path) as img:
                common_arg.rgb_point.w, common_arg.rgb_point.h = img.size
        except Exception as e:
            TLog.e(CommonArgTool.TAG, f"read image error: {e}")
            return False

        if common_arg.rgb_point.w <= 0 or common_arg.rgb_point.h <= 0:
            TLog.e(CommonArgTool.TAG, f"video size {common_arg.rgb_point.w}x{common_arg.rgb_point.h}")
            return False

        common_arg.gap = CommonArgTool.MIN_GAP

        common_arg.alpha_point.w = int(common_arg.rgb_point.w * common_arg.scale)
        common_arg.alpha_point.h = int(common_arg.rgb_point.h * common_arg.scale)

        h_w = common_arg.rgb_point.w + common_arg.gap + common_arg.alpha_point.w
        h_h = common_arg.rgb_point.h
        h_max = max(h_w, h_h)

        v_w = common_arg.rgb_point.w
        v_h = common_arg.rgb_point.h + common_arg.gap + common_arg.alpha_point.h
        v_max = max(v_w, v_h)

        if h_max > v_max: # Vertical layout
            common_arg.is_v_layout = True
            common_arg.alpha_point.x = 0
            common_arg.alpha_point.y = common_arg.rgb_point.h + common_arg.gap
            common_arg.output_w = common_arg.rgb_point.w
            common_arg.output_h = common_arg.rgb_point.h + common_arg.gap + common_arg.alpha_point.h
        else: # Horizontal layout
            common_arg.is_v_layout = False
            common_arg.alpha_point.x = common_arg.rgb_point.w + common_arg.gap
            common_arg.alpha_point.y = 0
            common_arg.output_w = common_arg.rgb_point.w + common_arg.gap + common_arg.alpha_point.w
            common_arg.output_h = common_arg.rgb_point.h

        w_fill, h_fill = CommonArgTool.cal_size_fill(common_arg.output_w, common_arg.output_h)
        common_arg.output_w += w_fill
        common_arg.output_h += h_fill

        if common_arg.output_w > 1504 or common_arg.output_h > 1504:
            msg = (f"[Warning] Output video width:{common_arg.output_w} or "
                   f"height:{common_arg.output_h} is over 1504. Some devices will "
                   "display exception. For example green screen!")
            TLog.w(CommonArgTool.TAG, msg)
            if tool_listener:
                tool_listener.on_warning(msg)

        common_arg.total_frame = 0
        i = 0
        while i <= 10000:
            frame_file = os.path.join(common_arg.input_path, f"{i:03d}.png")
            if not os.path.exists(frame_file):
                break
            common_arg.total_frame += 1
            i += 1

        if common_arg.total_frame <= 0:
            TLog.e(CommonArgTool.TAG, f"totalFrame={common_arg.total_frame}")
            return False

        if not common_arg.enable_crf and common_arg.bitrate <= 0:
            TLog.e(CommonArgTool.TAG, f"bitrate={common_arg.bitrate}")
            return False
            
        if common_arg.enable_crf and (common_arg.crf < 0 or common_arg.crf > 51):
            TLog.e(CommonArgTool.TAG, f"crf={common_arg.crf}, no in [0, 51]")
            return False

        return True

    @staticmethod
    def cal_size_fill(out_w, out_h):
        w_fill = 0
        if out_w % 16 != 0:
            w_fill = ((out_w // 16) + 1) * 16 - out_w
            
        h_fill = 0
        if out_h % 16 != 0:
            h_fill = ((out_h // 16) + 1) * 16 - out_h
            
        return w_fill, h_fill
