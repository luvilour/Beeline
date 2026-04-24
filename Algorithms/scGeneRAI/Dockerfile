FROM python:3.9-slim

LABEL maintainer="lvilour@gmail.com"

USER root
WORKDIR /

RUN pip install numpy torch pandas

COPY runscGeneRAI.py scGeneRAI.py dataloading_simple.py /

RUN mkdir data/

RUN apt-get update && apt-get install -y time
