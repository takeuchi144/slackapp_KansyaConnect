# src/handlers/notification/Dockerfile
FROM public.ecr.aws/lambda/python:3.12

COPY handlers/auth_handler/* ./
COPY lib ./lib

RUN python3.12 -m pip install -r requirements.txt -t .

CMD ["auth_handler.lambda_handler"]