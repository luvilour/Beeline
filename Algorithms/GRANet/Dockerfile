FROM python:3.9-slim

LABEL maintainer="you@example.com"

USER root
WORKDIR /

# System deps (scanpy needs these)
RUN apt-get update && apt-get install -y \
    build-essential \
    libhdf5-dev \
    libgl1 \
    time

# Python deps
RUN pip install \
    torch==2.0.1 \
    pandas==2.2.2 \
    numpy==1.23.5 \
    scikit-learn==0.22.0 \
    scipy==1.10.1 \
    tqdm==4.66.4

# Copy DeepSEM source
COPY src /GRANet/src
COPY runGRANet.py /GRANet/

WORKDIR /GRANet

RUN mkdir -p /usr/working_dir
