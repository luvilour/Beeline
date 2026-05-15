FROM python:3.9-slim

LABEL maintainer="lvilour@gmail.com"

USER root
WORKDIR /

RUN pip install numpy pytorch-tabnet torch pandas scikit-learn

COPY runTabNet.py /

RUN mkdir data/

RUN apt-get update && apt-get install -y time
