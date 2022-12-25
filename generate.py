import os
import argparse
import pickle
import shutil
import miditoolkit
import numpy as np
from midi2audio import FluidSynth

import torch
import torch.multiprocessing as mp

from collections import OrderedDict
from pydub import AudioSegment

import saver
from models import TransformerModel, network_paras
from utils import make_midi, get_random_string

DATASET_PATH = "./lofi_dataset"

def generate_mid(ckpt_path, out_dir="gen", verbose=True):
    """Inference one song and output the midi file using random name."""
    os.makedirs(out_dir, exist_ok=True)

    dictionary = pickle.load(open(os.path.join(DATASET_PATH, "dictionary.pkl"), 'rb'))
    event2word, word2event = dictionary

    # config
    n_class = []   # num of classes for each token
    for key in event2word.keys():
        n_class.append(len(event2word[key]))
    n_token = len(n_class)

    # init model
    net = TransformerModel(n_class, is_training=False)
    net.cuda()
    net.eval()

    # load weight
    try:
        net.load_state_dict(torch.load(ckpt_path))
    except:
        state_dict = torch.load(ckpt_path)
        new_state_dict = OrderedDict()
        for k, v in state_dict.items():
            name = k[7:] 
            new_state_dict[name] = v
        net.load_state_dict(new_state_dict)

    res = None
    while not isinstance(res, np.ndarray):
        if n_token == 8:
            res, _ = net.inference_from_scratch(dictionary, 0, n_token, display=verbose)

    filename = get_random_string(length=10)
    mid_file_path = os.path.join(out_dir, filename+".mid")
    # Get midi object.
    midi_obj = make_midi(res, mid_file_path, word2event)

    # Only take first tempo change.
    # midi_obj.tempo_changes = midi_obj.tempo_changes[:2]

    # output midi.
    # midi_obj.dump(mid_file_path)

    return mid_file_path

def render_midi_to_mp3(mid_file_path, out_dir=".", instrument=0, mp3_file_path="./out.mp3", soundfont="./soundfonts/A320U.sf2"):
    """render midi to mp3 with specified instrument and soundfont.
    
    Parameters
    ----------
    midi_obj : miditoolkit.midi.parser.MidiFile
        The source midi obj.
    out_dir : str
        The audio output path.
    instrument : int
        MIDI instrument program number, default is 0, which means Acoustic Grand Piano.
    mp3_file_path : str
        The output audio file name.
    soundfont : str
        Soundfont file path for FluidSynth to render.
    
    Return
    ------
    str, str
        Return midi file path and mp3 file path.
    """
    midi_synth = FluidSynth(sound_font=soundfont)

    temp_file_name = f"/tmp/{get_random_string(length=10)}"
    wav_file_path = temp_file_name+".wav" 
    
    # NOTE: Duplicate code, refer to make_midi() in utils
    midi_obj = miditoolkit.midi.parser.MidiFile(mid_file_path)
    midi_obj.instruments[0].program = instrument
    midi_obj.dump(mid_file_path)

    midi_synth.midi_to_audio(mid_file_path, wav_file_path)

    # convert to mp3
    wav = AudioSegment.from_wav(wav_file_path)
    wav += 20
    wav.export(mp3_file_path, format="mp3")
    print(f"{mp3_file_path} exported!")

    os.remove(wav_file_path)

    return mp3_file_path

def generate(ckpt, out, instrument, display=True):
    """Inference a song and return its mid and mp3 path"""
    mid_file_path = generate_mid(
        ckpt_path=ckpt,
        out_dir=out,
        verbose=display
    )
    song_id = os.path.basename(mid_file_path).split(".")[0]
    mp3_file_path = os.path.join(os.path.dirname(mid_file_path), song_id+f"_{instrument}.mp3")
    render_midi_to_mp3(
        mid_file_path=mid_file_path,
        out_dir=out,
        mp3_file_path=mp3_file_path,
        instrument=instrument,
    )
    return mid_file_path, mp3_file_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--ckpt', help='The checkpoint path that model should load.', type=str)
    parser.add_argument('-o', '--out', help='The folder that save the generated song.', type=str)
    parser.add_argument('-i', '--instrument', help='The instrument program number to render generated song.', type=int)
    args = parser.parse_args()

    mid_file_path = generate_mid(
        ckpt_path=args.ckpt,
        out_dir=args.out,
        verbose=False
    )
    mp3_file_path = render_midi_to_mp3(
        mid_file_path,
        out_dir=args.out,
        instrument=args.instrument,
    )
    print(mid_file_path, mp3_file_path)
