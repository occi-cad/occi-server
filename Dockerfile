FROM tiangolo/uvicorn-gunicorn:python3.10

LABEL maintainer="Sebastian Ramirez <tiangolo@gmail.com>"

RUN apt-get update
RUN apt-get install -y libmagic1 libgeos-dev # for magic lib in python 

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
