from PySide6.QtCore import QThread, Signal
import subprocess


class ProcessThread(QThread):
    progress = Signal(int)
    finished = Signal(bool)
    status_update = Signal(str)

    def __init__(self, cmd, duration=0):
        super().__init__()
        self.cmd = cmd
        self.duration = duration
        self.process = None
        self.is_killed = False

    def run(self):
        startupinfo = None
        creationflags = 0
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            creationflags = 0x08000000
            
        self.process = subprocess.Popen(
            self.cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,  
            universal_newlines=True, 
            startupinfo=startupinfo,
            creationflags=creationflags,
            bufsize=1
        )
        
        buffer = ""
        try:
            while True:
                if self.is_killed: break
                
                char = self.process.stdout.read(1)
                if not char:
                    if self.process.poll() is not None: break
                    continue
                
                if char == '\n' or char == '\r':
                    line = buffer.strip()
                    buffer = ""
                    if not line: continue
                    
                    if "[download]" in line and "%" in line:
                        match = re.search(r"\[download\]\s+([0-9.]+)%", line)
                        if match:
                            percent = int(float(match.group(1)))
                            self.progress.emit(min(percent, 100))
                            self.status_update.emit(f"Downloading Assets... {percent}%")
                    
                    elif "time=" in line and self.duration > 0:
                        time_match = re.search(r"time=(\d+):(\d+):(\d+\.\d+)", line)
                        if time_match:
                            h, m, s = time_match.groups()
                            current_sec = int(h) * 3600 + int(m) * 60 + float(s)
                            percent = int((current_sec / self.duration) * 100)
                            self.progress.emit(min(percent, 100))
                            self.status_update.emit(f"Converting Video Layout... {percent}%")
                else:
                    buffer += char
        except Exception as e:
            print(f"Extraction monitoring thread exception: {e}")

        self.cleanup_process()
        self.finished.emit(not self.is_killed and self.process.returncode == 0)

    def cleanup_process(self):
        if self.process:
            if self.is_killed:
                try:
                    self.process.terminate()
                    self.process.kill()
                except: pass
            try:
                self.process.wait(timeout=0.5)
            except: pass
            if self.process.stdout:
                try: self.process.stdout.close()
                except: pass

    def stop(self):
        self.is_killed = True
        self.cleanup_process()