# pull official base image
FROM python:3.10-slim

# set work directory
WORKDIR /occi

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# copy project
# we use volume mounting for now
# COPY . .