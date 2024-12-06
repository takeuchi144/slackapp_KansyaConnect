# src/handlers/notification/Dockerfile
FROM public.ecr.aws/lambda/python:3.12

COPY handlers/interactive_handler/* ./
COPY lib ./lib

RUN python3.12 -m pip install -r requirements.txt -t .

CMD ["interactive_handler.lambda_handler"]