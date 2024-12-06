FROM public.ecr.aws/lambda/python:3.12

# handlers/event_handlerからファイルをコピー
COPY handlers/event_handler/* ./

# libからファイルをコピー（srcがルートなので、直接libにアクセス可能）
COPY lib ./lib

RUN python3.12 -m pip install -r requirements.txt -t .

CMD ["event_handler.lambda_handler"]
