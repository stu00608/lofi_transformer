# Lofi Transformers

## Installation

```
git clone --recurse-submodules -j8 https://github.com/stu00608/lofi_transformer.git -b docker
```

```
conda create -y -n lofi_transformers python=3.8
conda activate lofi_transformers
conda install -y -c conda-forge cudatoolkit-dev
conda install -y pytorch torchvision torchaudio -c pytorch-lts -c nvidia
pip install -r requirements.txt
pip install -e fast-transformers
```

```
gdown 14vXsPerw02e7YBrxKMlgkvSB9wD48qVx
unzip processed_lofi_dataset.zip
```

```
gdown 19Seq18b2JNzOamEQMG1uarKjj27HJkHu --output exp/pretrained_transformer.zip
unzip exp/pretrained_transformer.zip -d exp/ 
```

```
# Train (finetune)
python emopia/workspace/transformer/main_cp.py --task_type ignore --data_root lofi_dataset --path_train_data train --load_dict dictionary.pkl --exp_name finetune_lofi --load_ckt pretrained_transformer --load_ckt_loss 25

# Inference
python emopia/workspace/transformer/main_cp.py --mode inference --load_dict dictionary.pkl --data_root lofi_dataset --path_train_data train --exp_name finetune_lofi --load_ckt finetune_lofi --task_type ignore --num_songs 5 --load_ckt_loss 8 --out_dir gen/finetune_lofi/8
```


* Need to manually copy `utils`, `saver`, `models` from `emopia/workspace/transformer` to make `generate.py` workable.
* You'll also need to put a `.sf2` soundfont file into `soundfonts` folder to render the midi file to audio.
    * For example [A320U.sf2 from signal](https://github.com/ryohey/signal/blob/main/public/A320U.sf2)

## Discord bot

* Set your own token.
```
token = os.environ["BOT_TOKEN"]
```

* Comment line 453 in `emopia/workspace/transformer/main_cp.py` to prevent saving .npy files.
