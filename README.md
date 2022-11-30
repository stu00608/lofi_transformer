# Lofi Transformers

## Installation

```
git clone https://github.com/stu00608/lofi_transformer.git -b docker
cd lofi_transformer
```


* use gdown to download model, to install: `pip install gdown`. Or download manually from 
* [Download Link](https://drive.google.com/file/d/1Gzt2UhysZzHPCz7XEDjkf-IjWh1O7fcx/view?usp=sharing)
* And then unzip in repo root folder.
```
gdown 1Gzt2UhysZzHPCz7XEDjkf-IjWh1O7fcx
unzip exp.zip
```

* use gdown to download dataset(dictionary). Or download manually from 
* [Download Link](https://drive.google.com/file/d/1UQD2oDsncw339FOUOQgAAmZx87CzZai0/view?usp=sharing)
* And then unzip in repo root folder.
```
gdown 1UQD2oDsncw339FOUOQgAAmZx87CzZai0

unzip lofi_dataset.zip
```

* Delete them to release some space.
```
rm exp.zip lofi_dataset.zip
```

* Go to Discord portal, create a bot application.
* Your bot need these permission to run properly.
    ![SCR-20221129-pz4](https://user-images.githubusercontent.com/40068587/204803016-81c18476-7d0e-4b4d-9e73-d0ffe3ea690d.png)

* Set your own discord bot token.
```
export BOT_TOKEN="put token here"
```

## Discord bot Docker Container


* Run docker build command.
```
docker build --no-cache -t lofi_transformer_bot --build-arg token=$BOT_TOKEN .
```

```
docker run --rm -it --gpus all lofi_transformer_bot

# -d for running in background.
docker run --rm -dit --gpus all lofi_transformer_bot
```

### Get generated files and stats in container to current folder
```
docker cp <container id>:/app/gen .
```
### attach container
```
docker attach <container id>
```
### detach container
* Ctrl+P -> Ctrl+Q
### Run bash in existing container
```
docker exec --user root -it <container id> /bin/bash
```

## Build Environment Base Image
* The built image is pushed to [dockerhub](https://hub.docker.com/repository/docker/stu00608/lofi_transformer_base)

```
# python 3.8.13, torch 1.8.2, fast_transformers 0.4.0, cuda 11.4, cudnn 8, ubuntu 18.04 
docker build --no-cache -t lofi_transformer_base --build-arg token=$BOT_TOKEN -f BaseDockerfile .
```
