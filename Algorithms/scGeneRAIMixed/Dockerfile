FROM python:3.9-slim

LABEL maintainer="lvilour@gmail.com"

USER root
WORKDIR /

RUN pip install numpy torch pandas tqdm

COPY runscGeneRAI.py scGeneRAI.py dataloading_simple.py /
COPY GSD-6000-1/ExpressionData.csv /dataset/GSD
COPY HSC-6000-1/ExpressionData.csv /dataset/HSC

RUN mkdir data/

RUN apt-get update && apt-get install -y time
