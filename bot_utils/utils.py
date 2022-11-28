import os
import pretty_midi
from pydub import AudioSegment

# Extend this to add more selection.
midi_program_to_emoji = {
    0: '🎹',
    4: '🎹',
    12: '🔔',
    16: '🎹',
    24: '🎸',
    56: '🎺',
}

def get_instrument_emoji(instrument: int):
    try:
        emoji = midi_program_to_emoji[int(instrument)]
    except Exception as e:
        emoji = pretty_midi.program_to_instrument_name(int(instrument))
    return emoji


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