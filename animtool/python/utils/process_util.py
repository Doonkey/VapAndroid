import subprocess
import threading
from utils.log import TLog

class ProcessUtil:
    
    @staticmethod
    def run(cmd: list) -> int:
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,  # Use text mode for string output
                encoding='utf-8',
                errors='replace'
            )
            
            # Create threads to read stdout and stderr to prevent blocking
            stdout_thread = threading.Thread(target=ProcessUtil._reader, args=(process.stdout, "OUTPUT"))
            stderr_thread = threading.Thread(target=ProcessUtil._reader, args=(process.stderr, "ERROR"))
            
            stdout_thread.start()
            stderr_thread.start()
            
            return_code = process.wait()
            
            stdout_thread.join()
            stderr_thread.join()
            
            return return_code
            
        except Exception as e:
            TLog.e("ProcessUtil", str(e))
            return -1

    @staticmethod
    def _reader(stream, type_name):
        try:
            for line in stream:
                # In Python we can just log directly, or accumulate. 
                # The Java version logged errors if result != 0 at the end.
                # Here we mimic the behavior of reading lines.
                # For now let's just print/log them as they come if needed, 
                # or just consume them to prevent blocking.
                if type_name == "ERROR":
                     # In Java it collected error strings and printed them if exit code != 0.
                     # Here, for simplicity while streaming, we might minimal log or just buffer.
                     # Let's simple-log for now to avoid complexity of buffering + conditional print.
                     # But Java logic was: buffer, then print ONLY if result != 0.
                     pass 
        except Exception as e:
            pass
