import os
from pydub import AudioSegment

midi_program_to_emoji = {
    0: '🎹',
    4: '🎹',
    24: '🎸',
}

def getfiles(out_dir):
    """Get playable audio source and midi in generate folder."""    
    os.makedirs(out_dir, exist_ok=True)
    filenames = os.listdir(out_dir)
    codes = [filename.split(".")[0] for filename in filenames if filename.endswith(".mid")]
    filedict = {}
    for c in codes:
        audios = [filename for filename in filenames if filename.startswith(c) and filename.endswith(".mp3")]
        for a in audios:
            filename = a.split(".")[0]
            mid_path = os.path.join(out_dir, c+".mid")
            mp3_path = os.path.join(out_dir, a)
            filedict[filename] = [mid_path, mp3_path]
    return filedict

def get_audio_time(file_path):
    """Get mp3 audio length in %m:%s format."""
    duration = AudioSegment.from_mp3(file_path).duration_seconds
    minute = int(duration // 60)
    second = int(duration % 60)
    return f"{minute:02d}:{second:02d}"