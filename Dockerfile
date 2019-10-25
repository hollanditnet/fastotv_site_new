FROM python:3

LABEL maintainer="Alexandr Topilski <support@fastogt.com>"

COPY . /app
COPY docker/db_config.py /app/app/config/
WORKDIR /app

RUN pip install -r requirements.txt

EXPOSE 8081
CMD [ "python", "server.py" ]
