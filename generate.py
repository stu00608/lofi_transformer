import os
import pickle
import shutil
from midi2audio import FluidSynth

import torch

from collections import OrderedDict
from pydub import AudioSegment

import saver
from models import TransformerModel, network_paras
from utils import write_midi, get_random_string

DATASET_PATH = "./lofi_dataset"

def generate_song(instrument, ckpt_path, num_songs=1, out_dir="gen"):
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

    midi_synth = FluidSynth(sound_font="./soundfonts/A320U.sf2")

    songs_path = []
    gen_songs = 0
    while(gen_songs < num_songs):
        res = None
        if n_token == 8:
            res, _ = net.inference_from_scratch(dictionary, 0, n_token)
            if res is None:
                continue

        filename = get_random_string(length=10)
        out_file_path = os.path.join(out_dir, filename+f"_{instrument}"+".mid")
        wav_file_path = os.path.join(out_dir, filename+f"_{instrument}"+".wav")
        mp3_file_path = os.path.join(out_dir, filename+f"_{instrument}"+".mp3")
        # Get midi object.
        midi_obj = write_midi(res, out_file_path, word2event, dump=False)

        # Only take first tempo change.
        midi_obj.tempo_changes = midi_obj.tempo_changes[:2]
        current_bpm = midi_obj.tempo_changes[-1].tempo

        # Change the channel instrument.
        midi_obj.instruments[0].program = instrument

        # output midi.
        midi_obj.dump(out_file_path)

        # output wav.
        midi_synth.midi_to_audio(out_file_path, wav_file_path)

        # convert to mp3
        wav = AudioSegment.from_wav(wav_file_path)
        wav += 5
        wav.export(mp3_file_path, format="mp3")
        print("Exported")
        os.remove(wav_file_path)

        gen_songs += 1
        songs_path.append([out_file_path, mp3_file_path])
    return songs_path

if __name__ == "__main__":
    generate_song(
        ckpt_path="./exp/fourth_finetune_lofi/loss_8_params.pt",
        out_dir="gen/fourth_finetune_lofi"
    )