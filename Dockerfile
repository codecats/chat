FROM ubuntu:latest

ADD . /code/src
WORKDIR /code

RUN apt-get -qqy update
RUN apt-get -qqy upgrade
RUN apt-get -qqy install \
    python \
    python-dev \
    python-gtk2 \
    python-pip \
    python-wxgtk3.0 \
    winpdb

RUN pip install virtualenv

RUN bash -c "virtualenv venv && . venv/bin/activate && pip install -r src/requirements/main.txt"

EXPOSE 5001
CMD ['venv/bin/python', '-u', 'src/main.py', "1>server.log", "2>server.log"]
