# pull official base image
FROM python:3.10-slim

# set work directory
WORKDIR /occi

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# copy project
# volumes can be mounted inside the working directory too for on runtime file syncing
# otherwise the scripts are uploaded to the image on built time
COPY . .