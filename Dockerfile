FROM python:2.7

ADD . /code
WORKDIR /code

RUN bash -c "virtualenv venv && . venv/bin/activate && pip install -r requirements.txt"
