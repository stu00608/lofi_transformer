FROM stu00608/lofi_transformer_base

WORKDIR /app
COPY . /app
RUN python3.8 -m pip install -r requirements.txt

ARG token
ENV BOT_TOKEN=${token}

ENTRYPOINT [ "python3.8", "bot.py" ] 