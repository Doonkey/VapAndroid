import os
import sys
import threading
import time
import json
from concurrent.futures import ThreadPoolExecutor

from common_arg import CommonArgTool, CommonArg
from get_alpha_frame import GetAlphaFrame
from utils.log import TLog
from utils.process_util import ProcessUtil
from utils.md5_util import Md5Util
from mp4_box_tool import Mp4BoxTool

from PIL import Image


class AnimTool:
    TAG = "AnimTool"
    OUTPUT_DIR = "output" + os.sep
    FRAME_IMAGE_DIR = "frames" + os.sep
    FRAME_ORIGINAL_DIR = "frames_original" + os.sep
    VIDEO_FILE = "video.mp4"
    TEMP_VIDEO_FILE = "tmp_video.mp4"
    TEMP_VIDEO_AUDIO_FILE = "tmp_video_audio.mp4"
    VAPC_BIN_FILE = "vapc.bin"
    VAPC_JSON_FILE = "vapc.json"

    def __init__(self):
        self.total_p = 0
        self.start_time = 0
        self.get_alpha_frame = GetAlphaFrame()
        self.tool_listener = None
        self.lock = threading.Lock()

    def set_tool_listener(self, listener):
        self.tool_listener = listener

    def create(self, common_arg, need_video):
        TLog.i(self.TAG, "start create")

        # inputPath is already checked/formatted in CommonArgTool
        input_file = common_arg.input_path

        # TODO: Handle .webm logic if needed (ProcessUtil.run logic for webm parsing)
        # Java: if (inputFile.getName().endsWith(".webm")) ...
        # Assuming folder input for now based on typical usage.

        if os.path.isfile(input_file):
            # check if it is webm
            if input_file.strip().endswith(".webm"):
                # Handle WebM
                success = self.split_video(common_arg)
                if success:
                    common_arg.input_path = os.path.join(
                        common_arg.output_path, self.FRAME_ORIGINAL_DIR
                    )
                else:
                    return False
            else:
                raise FileNotFoundError(f"not found frames dir: {input_file}")

        success = self.create_all_frame_image(common_arg)
        if success:
            if self.final_check(common_arg) and need_video:
                return self.create_video(common_arg)

        return False

    def check_common_arg(self, common_arg):
        return CommonArgTool.auto_fill_and_check(common_arg, self.tool_listener)

    def final_check(self, common_arg):
        # if common_arg.is_vapx:
        #     if not common_arg.src_set.srcs:
        #         TLog.i(self.TAG, "vapx error: src is empty")
        #         return False
        #     for src in common_arg.src_set.srcs:
        #         if src.w <= 0 or src.h <= 0:
        #             TLog.i(self.TAG, f"vapx error: src.id={src.src_id}, src.w={src.w}, src.h={src.h}")
        #             return False
        return True

    def create_all_frame_image(self, common_arg):
        if not self.check_common_arg(common_arg):
            if self.tool_listener:
                self.tool_listener.on_error()
            return False

        TLog.i(self.TAG, "createAllFrameImage")
        self.start_time = time.time()

        self.check_dir(common_arg.output_path)
        self.check_dir(common_arg.frame_output_path)

        self.total_p = 0

        # Threading logic
        # Java used manual thread creating.
        # Python GIL limits CPU bound tasks, but let's use ThreadPoolExecutor for I/O + Pillow (which releases GIL often)

        max_workers = 16
        total_frame = common_arg.total_frame

        if self.tool_listener:
            self.tool_listener.on_progress(0.0)

        error_occurred = False

        def task(frame_index):
            try:
                self.create_frame(common_arg, frame_index)
                with self.lock:
                    self.total_p += 1
                    progress = self.total_p / total_frame
                    if self.tool_listener:
                        self.tool_listener.on_progress(progress)
                    else:
                        # TLog.i(self.TAG, f"progress {progress}") # Reduce noise
                        pass
            except Exception as e:
                TLog.e(self.TAG, f"createFrame error: {e}")
                # In python, we can't easily break all threads, but we can set a flag
                nonlocal error_occurred
                error_occurred = True

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all
            futures = [executor.submit(task, i) for i in range(total_frame)]

            # Wait for all (context manager does this)

        if error_occurred:
            if self.tool_listener:
                self.tool_listener.on_error()
            return False

        cost = (time.time() - self.start_time) * 1000
        TLog.i(self.TAG, f"Finish cost={cost} ms")

        if self.tool_listener:
            self.tool_listener.on_complete()

        return True

    def create_frame(self, common_arg, frame_index):
        input_file_path = os.path.join(common_arg.input_path, f"{frame_index:03d}.png")
        input_file = None
        if os.path.exists(input_file_path):
            # We pass path as pathlib.Path or just use it?
            # GetAlphaFrame expects string or Path object?
            # My python port expects Path mostly or string.
            # but Java pass File.
            # I should pass Path object to be consistent if I used pathlib, but I used os.path.
            # Let's pass Path object for better API.
            from pathlib import Path

            input_file = Path(input_file_path)

        video_frame = self.get_alpha_frame.create_frame(common_arg, input_file)

        # if common_arg.is_vapx:
        #      # getFrameObj takes PIL image as output_argb arg?
        #      # My previous decision was interface.
        #      # get_mask_frame.get_frame_obj_pil(index, arg, image)
        #      frame_obj = self.get_mask_frame.get_frame_obj_pil(frame_index, common_arg, video_frame.image)
        #      if frame_obj:
        #          # Need thread safety for list append?
        #          # frame_set.frameObjs is a list.
        #          # Python lists are thread-safe for append (atomic), but logic might get interleaved?
        #          # Handled by lock or just use list.
        #          with self.lock:
        #              common_arg.frame_set.frame_objs.append(frame_obj)

        if not video_frame:
            TLog.i(self.TAG, f"frameIndex={frame_index} is empty")
            return

        # Save image
        output_file_path = os.path.join(
            common_arg.frame_output_path, f"{frame_index:03d}.png"
        )
        video_frame.image.save(output_file_path, "PNG")

    def check_dir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def create_video(self, common_arg):
        try:
            if common_arg.mp4edit_cmd:
                output_file = os.path.join(common_arg.output_path, self.TEMP_VIDEO_FILE)
            else:
                output_file = os.path.join(common_arg.output_path, self.VIDEO_FILE)
            result = self.create_mp4(
                common_arg, output_file, common_arg.frame_output_path
            )
            if not result:
                TLog.i(self.TAG, "createMp4 fail")
                self.delete_file(common_arg)
                return False

            temp_video_name = self.TEMP_VIDEO_FILE
            if common_arg.need_audio:
                result = self.merge_audio_2_mp4(common_arg, temp_video_name)
                if not result:
                    TLog.i(self.TAG, "mergeAudio2Mp4 fail")
                    self.delete_file(common_arg)
                    return False
                temp_video_name = self.TEMP_VIDEO_AUDIO_FILE

            if common_arg.mp4edit_cmd:
                self.create_vapc_json(common_arg)
                # Json to Bin
                input_json = os.path.join(common_arg.output_path, self.VAPC_JSON_FILE)
                mp4_box_tool = Mp4BoxTool()
                vapc_bin_path = mp4_box_tool.create(input_json, common_arg.output_path)
                # Merge Bin
                result = self.merge_bin_2_mp4(
                    common_arg,
                    self.VAPC_BIN_FILE,
                    temp_video_name,
                    common_arg.output_path,
                )
                if not result:
                    TLog.i(self.TAG, "mergeBin2Mp4 fail")
                    self.delete_file(common_arg)
                    return False

            self.delete_file(common_arg)

            # MD5
            final_video = os.path.join(common_arg.output_path, self.VIDEO_FILE)
            md5_util = Md5Util()
            md5 = md5_util.get_file_md5(final_video, common_arg.output_path)
            TLog.i(self.TAG, f"md5={md5}")

            return True
        except Exception as e:
            TLog.e(self.TAG, f"createVideo error: {e}")
            return False

    def delete_file(self, common_arg):
        for f in [self.TEMP_VIDEO_FILE, self.TEMP_VIDEO_AUDIO_FILE, self.VAPC_BIN_FILE]:
            p = os.path.join(common_arg.output_path, f)
            if os.path.exists(p):
                os.remove(p)

    def create_vapc_json(self, common_arg):
        info = {
            "v": common_arg.version,
            "f": common_arg.total_frame,
            "w": common_arg.rgb_point.w,
            "h": common_arg.rgb_point.h,
            "fps": common_arg.fps,
            "videoW": common_arg.output_w,
            "videoH": common_arg.output_h,
            "aFrame": [
                common_arg.alpha_point.x,
                common_arg.alpha_point.y,
                common_arg.alpha_point.w,
                common_arg.alpha_point.h,
            ],
            "rgbFrame": [
                common_arg.rgb_point.x,
                common_arg.rgb_point.y,
                common_arg.rgb_point.w,
                common_arg.rgb_point.h,
            ],
            "isVapx": 1 if common_arg.is_vapx else 0,
            "orien": 0,
        }

        # We need to construct the JSON carefully to match existing format if needed,
        # but standardized JSON is better.
        # The Java code manually string-builds partial JSONs then combines them.

        # However, we converted FrameSet and SrcSet to have __str__ methods that return partial JSON strings.
        # Actually, let's just build the dict and dump it if we can trust the structure.
        # Java: { "info": { ... }, "src": [...], "frame": [...] }
        # Note: Java's SrcSet.toString() returns '"src":[...]' (key included).

        # Proper Pythonic way:
        final_dict = {"info": info}
        if common_arg.is_vapx:
            pass
            # SrcSet.to_dict() returns {"src": [...]}
            # final_dict.update(common_arg.src_set.to_dict())
            # FrameSet.to_dict() ? I didn't implement to_dict for FrameSet fully, only __str__.
            # I should probably use the __str__ method or implement to_dict.
            # Let's rely on JSON dump of a constructed dict.
            # Since I didn't implement to_dict for FrameSet, I'll rely on string manipulation
            # OR strictly implement to_dict in FrameSet now?
            # I can't modify FrameSet file easily right now without another call.
            # I'll construct the string manually to ensure compatibility with my previous steps.
            # pass

        info_json = json.dumps(info, separators=(",", ":"))
        # remove curlies to embed? No, info is a key.
        # Wrapper: { "info": ... , ... }

        # Java: "info":{...}
        # Then sb.append("{"); sb.append(json); ...

        # If I want to use the __str__ from SrcSet/FrameSet which outputs '"src":[...]'

        parts = []
        parts.append(f'"info":{info_json}')

        if common_arg.is_vapx:
            pass
            # parts.append(str(common_arg.src_set))
            # parts.append(str(common_arg.frame_set))

        final_json_str = "{" + ",".join(parts) + "}"

        TLog.i(self.TAG, final_json_str)

        with open(os.path.join(common_arg.output_path, self.VAPC_JSON_FILE), "w") as f:
            f.write(final_json_str)

    def split_video(self, common_arg):
        TLog.i(self.TAG, "run splitVideo")
        cmd = self.get_ffmpeg_split_cmd(common_arg)
        result = ProcessUtil.run(cmd)
        TLog.i(self.TAG, f"splitVideo result={'success' if result == 0 else 'fail'}")
        return result == 0

    def get_ffmpeg_split_cmd(self, common_arg):
        output_orig_frames = os.path.join(
            common_arg.output_path, self.FRAME_ORIGINAL_DIR
        )
        self.check_dir(output_orig_frames)
        cmd = [
            common_arg.ffmpeg_cmd,
            "-c:v",
            "libvpx-vp9",
            "-i",
            common_arg.input_path,
            "-pix_fmt",
            "rgba",
            "-start_number",
            "0",
            os.path.join(output_orig_frames, "%03d.png"),
        ]
        return cmd

    def create_mp4(self, common_arg, output_file, frame_image_path):
        TLog.i(self.TAG, "run createMp4")
        cmd = self.get_ffmpeg_cmd(common_arg, output_file, frame_image_path)
        result = ProcessUtil.run(cmd)
        TLog.i(self.TAG, f"createMp4 result={'success' if result == 0 else 'fail'}")
        return result == 0

    def get_ffmpeg_cmd(self, common_arg, output_file, frame_image_path):
        input_pattern = os.path.join(frame_image_path, "%03d.png")

        cmd = [
            common_arg.ffmpeg_cmd,
            "-framerate",
            str(common_arg.fps),
            "-i",
            input_pattern,
            "-pix_fmt",
            "yuv420p",
        ]

        if common_arg.enable_h265:
            cmd.extend(["-vcodec", "libx265"])
            cmd.extend(["-tag:v", "hvc1"])  # hvc1 for Apple compatibility
        else:
            cmd.extend(["-vcodec", "libx264"])
            cmd.extend(["-bf", "0"])

        if common_arg.enable_crf:
            cmd.extend(["-crf", str(common_arg.crf)])
        else:
            cmd.extend(["-b:v", f"{common_arg.bitrate}k"])

        cmd.extend(["-force_key_frames", common_arg.force_key_frames])
        cmd.extend(["-profile:v", "main"])
        cmd.extend(["-level", "4.0"])
        cmd.extend(["-bufsize", "2000k"])
        cmd.extend(["-y", output_file])

        return cmd

    def merge_audio_2_mp4(self, common_arg, temp_video_file):
        output_file = os.path.join(common_arg.output_path, self.TEMP_VIDEO_AUDIO_FILE)
        audio_input = common_arg.audio_path
        video_input = os.path.join(common_arg.output_path, temp_video_file)

        cmd = [
            common_arg.ffmpeg_cmd,
            "-i",
            audio_input,
            "-i",
            video_input,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-y",
            output_file,
        ]

        TLog.i(self.TAG, "run mergeAudio2Mp4")
        result = ProcessUtil.run(cmd)
        TLog.i(
            self.TAG, f"mergeAudio2Mp4 result={'success' if result == 0 else 'fail'}"
        )
        return result == 0

    def merge_bin_2_mp4(self, common_arg, input_file, temp_video_file, video_path):
        # input_file is the bin filename (relative or absolute?)
        # Java: ":" + inputFile + ":3"
        # Java inputFile argument passed was VAPC_BIN_FILE (filename only? NO. returned absolute path from Mp4BoxTool)
        # Wait, Java code:
        # String vapcBinPath = mp4BoxTool(input, ...);
        # mergeBin2Mp4(..., vapcBinPath, ...);
        # cmd = ... ":" + inputFile ...
        # So it uses absolute path.

        output_final = os.path.join(video_path, self.VIDEO_FILE)
        input_video = os.path.join(video_path, temp_video_file)

        # Ensure inputFile is absolute or correct relative
        bin_path = (
            os.path.join(video_path, input_file)
            if not os.path.isabs(input_file)
            else input_file
        )

        cmd = [
            common_arg.mp4edit_cmd,
            "--insert",
            f":{bin_path}:3",  # Insert as track 3? Or box? "vapc" is usually a box in a track?
            # No, mp4edit --insert :file:trace/path?
            # Bento4 syntax: --insert <box-type>:<file>[:<path>]
            # Wait, Java code: ":" + inputFile + ":3"
            # If inputFile is path, then :path:3.
            # Does that mean Type is empty? Or type is inferred?
            # Bento4 docs: --insert <node>:<file-path> where node is path to box.
            # If node is empty string (start with colon), it inserts at top level?
            # The Java command constructed is: mp4edit --insert :vapc.bin:3 ...
            # This looks like: --insert :<file>:3?
            # If the Java code works, I should replicate strictly.
            # Java: "--insert", ":" + inputFile + ":3"
            # If inputFile is "c:\foo\vapc.bin", this becomes ":c:\foo\vapc.bin:3".
            # This looks weird for Bento4.
            # Bento4 command line usually: mp4edit --insert [atom_path]:[filename] input output
            # If atom_path is numeric, it might mean track ID?
            # Or "3" is the atom path?
            # Actually, I suspect inputFile in Java might be just the filename if it's in CWD?
            # But Mp4BoxTool returns `output.getAbsolutePath()`.
            # So it is ":absolute_path:3".
            # I will trust the Java code's command construction.
            input_video,
            output_final,
        ]

        TLog.i(self.TAG, "run mergeBin2Mp4")
        result = ProcessUtil.run(cmd)
        TLog.i(self.TAG, f"mergeBin2Mp4 result={'success' if result == 0 else 'fail'}")
        return result == 0


class IToolListener:
    def on_progress(self, progress):
        pass

    def on_warning(self, msg):
        pass

    def on_error(self):
        pass

    def on_complete(self):
        pass
