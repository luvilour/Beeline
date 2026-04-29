FROM python:3.9-slim

LABEL maintainer="lvilour@gmail.com"

USER root
WORKDIR /

RUN pip install numpy torch pandas tqdm

COPY runscGeneRAI.py scGeneRAI.py dataloading_simple.py /
COPY ../../inputs/Curated/GSD/GSD-6000-1/ExpressionData.csv /data/GSD
COPY ../../inputs/Curated/HSC/HSC-6000-1/ExpressionData.csv /data/HSC

RUN mkdir data/

RUN apt-get update && apt-get install -y time
