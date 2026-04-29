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
    numpy \
    pandas \
    torch \
    scanpy \
    anndata \
    scikit-learn

# Copy DeepSEM source
COPY src /DeepSEM/src
COPY runDeepSEM.py /DeepSEM/

WORKDIR /DeepSEM

RUN mkdir -p /usr/working_dir
