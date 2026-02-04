# AnimTool Python Port Walkthrough

The Java `animtool` project has been converted to Python. The new code is located in `animtool/python`.

## Directory Structure

```
animtool/python/
├── main.py                # Entry point
├── anim_tool.py           # Core orchestration logic
├── common_arg.py          # Configuration and validation
├── mp4_box_tool.py        # MP4 binary manipulation
├── get_alpha_frame.py     # Image processing (RGB/Alpha separation)
├── requirements.txt       # Dependencies (Pillow)
├── data/
│   └── point_rect.py
├── utils/
│   ├── log.py
│   ├── md5_util.py
│   └── process_util.py
└── tests/                 # Verification tests
```

## Prerequisites

1.  **Python 3.x**
2.  **FFmpeg** and **MP4Edit (Bento4)** must be installed and in your system PATH (same requirement as the Java version).
3.  **Pillow** library.

## Setup

Install dependencies:

```bash
cd animtool/python
pip install -r requirements.txt
```

## Usage

You can run the tool via `main.py`.

```bash
python main.py --input /path/to/frames_dir --output /path/to/output_dir --fps 24
```

### Options

- `-i`, `--input`: (Required) Path to the directory containing frame images.
- `-f`, `--ffmpeg`: FFmpeg executable path (default: `ffmpeg`).
- `-m`, `--mp4edit`: Mp4edit executable path (default: `mp4edit`).
- `--h265`: Enable H.265 encoding (Default: True).
- `--no-h265`: Disable H.265 encoding.
- `-b`, `--bitrate`: Bitrate in kbps (default: 15000).
- `-fps`, `--fps`: Frames per second (default: 25).
- `-fkps`, `--force_key_frames`: Force key frames (default: "0.000").
- `-o`, `--output`: (Optional) Output directory. Defaults to `input_dir/output`.
