FROM python:3.9-slim

LABEL maintainer="lvilour@gmail.com"

USER root
WORKDIR /

RUN pip install numpy lassonet torch pandas

COPY runLassoNetProbNorm.py /

RUN mkdir data/

RUN apt-get update && apt-get install -y time
