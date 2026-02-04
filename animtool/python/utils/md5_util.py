import hashlib
import os
from utils.log import TLog

class Md5Util:
    MD5_FILE = "md5.txt"

    @staticmethod
    def get_file_md5(file_path: str, output_path: str) -> str:
        if not os.path.exists(file_path) or not os.path.isfile(file_path) or os.path.getsize(file_path) <= 0:
            return None
        
        md5_hash = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    md5_hash.update(byte_block)
            
            md5_txt = md5_hash.hexdigest()
            
            try:
                with open(os.path.join(output_path, Md5Util.MD5_FILE), "w") as f:
                    f.write(md5_txt)
            except Exception as e:
                TLog.e("Md5Util", str(e))
                raise RuntimeError(e)
                
            return md5_txt
        except Exception as e:
            TLog.e("Md5Util", str(e))
        
        return None
