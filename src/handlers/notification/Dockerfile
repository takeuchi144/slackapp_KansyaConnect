# src/handlers/notification/Dockerfile
FROM public.ecr.aws/lambda/python:3.12

COPY handlers/notification/* ./
COPY lib ./lib

RUN python3.12 -m pip install -r requirements.txt -t .

CMD ["main.lambda_handler"]