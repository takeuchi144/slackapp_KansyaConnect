FROM public.ecr.aws/lambda/python:3.12

COPY handlers/reset_handler/reset_handler.py handlers/reset_handler/requirements.txt ./
COPY lib ./lib

RUN python3.12 -m pip install -r requirements.txt -t .

CMD ["reset_handler.lambda_handler"]