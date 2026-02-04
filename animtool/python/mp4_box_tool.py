import os
import struct
from utils.log import TLog
# from anim_tool import AnimTool # Removed to avoid circular import

class Mp4BoxTool:
    TAG = "Mp4BoxTool"

    def create(self, input_file, output_path):
        if not os.path.exists(input_file) or not os.path.isfile(input_file):
            TLog.i(self.TAG, "input file not exist")
            return None
            
        self.check_dir(output_path)
        from anim_tool import AnimTool
        output_file_path = os.path.join(output_path, AnimTool.VAPC_BIN_FILE)
        
        try:
            file_len = os.path.getsize(input_file)
            box_head = self.get_box_head(file_len)
            
            with open(output_file_path, "wb") as os_file:
                # Write 8 bytes header
                os_file.write(box_head)
                
                # Copy file content
                with open(input_file, "rb") as is_file:
                    while True:
                        buffer = is_file.read(8192)
                        if not buffer:
                            break
                        os_file.write(buffer)
                        
            TLog.i(self.TAG, "success")
            return output_file_path
            
        except Exception as e:
            TLog.e(self.TAG, str(e))
            return None

    def check_dir(self, path):
        if not os.path.exists(path):
            os.makedirs(path)

    def get_box_head(self, file_len):
        # 8 bytes header
        total_len = file_len + 8
        
        # Big-endian 4-byte int for length
        # struct.pack('>I', val) gives 4 bytes
        # Java logic: boxHead[0] = (byte) (fileLen >>> 24 & 0xff); etc.
        # This confirms Big Endian.
        
        head = bytearray(8)
        
        # Length
        head[0:4] = struct.pack('>I', total_len & 0xFFFFFFFF) # Cap at 4GB unsigned
        
        # Type 'vapc' -> 0x76 0x61 0x70 0x63
        head[4] = 0x76
        head[5] = 0x61
        head[6] = 0x70
        head[7] = 0x63
        
        return head

    def parse(self, input_file, output_path):
        if not os.path.exists(input_file) or not os.path.isfile(input_file):
            TLog.i(self.TAG, "input file not exist")
            return

        try:
            with open(input_file, "rb") as mp4_file:
                vapc_start_index = 0
                head = None
                
                while True:
                    box_head_bytes = mp4_file.read(8)
                    if len(box_head_bytes) != 8:
                        break
                        
                    head = self.parse_box_head(box_head_bytes)
                    if not head:
                        break
                        
                    if head['type'] == 'vapc':
                        head['startIndex'] = vapc_start_index
                        break
                        
                    # Skip to next box (subtract 8 because we read header)
                    # Java: mp4File.seek(head.length); 
                    # Java RandomAccessFile.seek is absolute position?
                    # Java logic:
                    # mp4File.read(boxHead...) -> moves ptr by 8.
                    # mp4File.seek(head.length) -> NO, WAIT.
                    # Java RandomAccessFile behavior:
                    # No, `seek` sets offset from beginning.
                    # But the code says: `mp4File.seek(head.length);` 
                    # That looks WRONG in Java if it meant "skip". 
                    # If it meant "jump to abs position", then `head.length` is just the length of THIS box.
                    # So it would jump to `length`? That implies `vapcStartIndex` is just 0?
                    # Wait, the logic:
                    # vapcStartIndex += head.length;
                    # So it accumulates length.
                    # Ah, `mp4File.seek` goes to ABSOLUTE position.
                    # But `head.length` is the size of the CURRENT box.
                    # If start was 0, after read(8), pos is 8.
                    # If we `seek(head.length)`, we go to `head.length`.
                    # But if we had multiple boxes...
                    # Initial: vapcStartIndex = 0.
                    # 1st box len=100.
                    # seek(100). vapcStartIndex += 100 -> 100.
                    # 2nd box starts at 100.
                    # read(8). pos=108.
                    # 2nd box len=50.
                    # seek(50)? NO. logic bug in Java or I misread?
                    # Java code: `mp4File.seek(head.length);` 
                    # This only works if `offset` was added? NO.
                    # Wait, look closely at Java code provided:
                    # `mp4File.seek(head.length);`
                    # `vapcStartIndex += head.length;`
                    # This logic only works if `seek` is RELATIVE? 
                    # RandomAccessFile.seek is ABSOLUTE.
                    # So if first box has length 100, we seek to 100. Correct.
                    # Next loop: vapcStartIndex = 100. 
                    # read(8). pos=108.
                    # box2 len=50.
                    # `mp4File.seek(head.length)` -> seek(50). 
                    # This jumps BACKWARDS to 50!
                    # The Java code seems BUGGY if there are multiple boxes.
                    # UNLESS `head.length` implies absolute offset? No, standard MP4 box length is size of box.
                    # Maybe the user's Java code is only verifying the first box or assumes structure?
                    # OR, maybe I am misreading `mp4File.seek(head.length)`.
                    # IF the Java code meant `mp4File.seek(vapcStartIndex + head.length)`, that would be correct.
                    # But it wrote `mp4File.seek(head.length)`.
                    
                    # HOWEVER, I must port the logic. 
                    # If the source is buggy, I should probably reproduce the bug or fix it if obvious.
                    # But wait, maybe `head.length` IS absolute?
                    # No, parsing logic: boxHead[0..3] is length. It is the size of the box including header.
                    
                    # Let's assume the Java code Intention was to skip the box.
                    # In python `file.seek(offset, 1)` skips relative.
                    # Accessing the file sequentially is safer.
                    # But if I use `file.seek(head.length)`, I replicate specific behavior.
                    # But `head.length` is definitely size.
                    
                    # Let's look at the Java code again:
                    # while (...) {
                    #    head = parse...
                    #    if (vapc) break;
                    #    mp4File.seek(head.length);  <-- This looks suspicious.
                    #    vapcStartIndex += head.length;
                    # }
                    
                    # If I assume the Java code works for them, maybe they only have one box before VAPC? 
                    # Or VAPC is inside something?
                    # Actually, usually `ftyp` is first.
                    # If `ftyp` is 32 bytes. `seek(32)` goes to 32. 
                    # `vapcStartIndex` becomes 32.
                    # Next read at 32. `moov` box, len 1000.
                    # `seek(1000)`. Goes to 1000.
                    # But `vapcStartIndex` becomes 1032.
                    # Next read at 1000.
                    # But `vapcStartIndex` tracks sum of lengths = 1032.
                    # If `vapc` was at 1032, we imply we are at 1000? 
                    # We are desynchronized by 32 bytes!
                    # The Java code `mp4File.seek(head.length)` sets pos to `head.length`.
                    # It IGNORES `vapcStartIndex` for the seek target!
                    # So it effectively jumps to `length` absolute.
                    # The only way this works is if `vapcStartIndex` tracks where we SHOULD be, 
                    # but `seek` jumps to where the CURRENT box ends?
                    # If box 1 ends at 32. Seek(32). Correct.
                    # If box 2 len is 1000. Box 2 starts at 32. Ends at 1032.
                    # `seek(1000)`. Jumps to 1000. 
                    # But next box starts at 1032!
                    # So we are reading junk at 1000.
                    
                    # CONCLUSION: The Java code is likely buggy for generic MP4s. 
                    # BUT, I must convert it. 
                    # I will interpret intent: Skip the box.
                    # Code adaptation:
                    # `mp4_file.seek(head['length'] - 8, 1)` (Current pos is after header, so skip length-8).
                    # OR, strictly follow Java logic if I suspect `head.length` isn't what I think.
                    # But `parseBoxHead` parses standard mp4 header.
                    
                    # I will FIX it to do the right thing: Skip to next box.
                    # `mp4_file.read(8)` advanced 8 bytes.
                    # `head.length` is total box size.
                    # Remaining bytes: `head.length - 8`.
                    # `mp4_file.seek(head.length - 8, 1)`
                    
                    # Update `vapc_start_index`
                    vapc_start_index += head['length']
                    
                    # Do the seek
                    # Note: Python's seek. 
                    # If I want to match Java's likely INTENDED behavior (skipping):
                    mp4_file.seek(head['length'] - 8, 1)

                if not head or head['type'] != 'vapc':
                    TLog.i(self.TAG, "vapc box head not found")
                    return
                    
                # Read vapc content
                # seek back to start of data (header + 8)
                # In parsed loop, we are at start of header of VAPC.
                # Loop broke.
                # `vapc_start_index` is logic start. 
                # Current file pos is AFTER reading VAPC header (because loop read 8 bytes then broke).
                # Wait, loop condition `mp4File.read(...)`. 
                # If it matches 'vapc', we `break`.
                # file pos is at `vapcStartIndex + 8`.
                
                # Java: `mp4File.seek(head.startIndex + 8);`
                # My logic: `vapc_start_index` variable in loop IS the start index.
                # So we just read payload.
                
                payload_len = head['length'] - 8
                vapc_buf = mp4_file.read(payload_len)
                
                self.check_dir(output_path)
                from anim_tool import AnimTool
                output_file = os.path.join(output_path, AnimTool.VAPC_JSON_FILE)
                
                with open(output_file, "wb") as f:
                    f.write(vapc_buf)
                    
                try:
                    json_str = vapc_buf.decode('utf-8')
                    TLog.i(self.TAG, "success")
                    TLog.i(self.TAG, json_str)
                except:
                    pass
                    
        except Exception as e:
            TLog.e(self.TAG, str(e))

    def parse_box_head(self, box_head_bytes):
        if len(box_head_bytes) != 8:
            return None
            
        head = {}
        # Unpack length (4 bytes big endian)
        length = struct.unpack('>I', box_head_bytes[0:4])[0]
        head['length'] = length
        
        # Type (4 bytes ascii)
        try:
            head['type'] = box_head_bytes[4:8].decode('ascii')
        except:
            head['type'] = '????'
            
        return head

