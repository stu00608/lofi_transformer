import os
from pydub import AudioSegment

def getfiles(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    filenames = os.listdir(out_dir)
    filenames = [filename.split(".")[0] for filename in filenames if filename.endswith(".mid")]
    filedict = {}
    for filename in filenames:
        mid_path = os.path.join(out_dir, filename+".mid")
        mp3_path = os.path.join(out_dir, filename+".mp3")
        filedict[filename] = [mid_path, mp3_path]
    return filedict

def get_audio_time(file_path):
    """Get mp3 audio length in %m:%s format."""
    duration = AudioSegment.from_mp3(file_path).duration_seconds
    minute = int(duration // 60)
    second = int(duration % 60)
    return f"{minute:02d}:{second:02d}"