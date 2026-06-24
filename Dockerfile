ARG BASE_IMAGE=openeuler/openeuler:24.03-lts
FROM ${BASE_IMAGE}

RUN dnf update -y && \
    dnf install -y \
        python3 python3-pip \
        gcc gcc-c++ make cmake \
        git wget curl tar gzip unzip \
        openssh-clients sshpass \
        pandoc \
    && dnf clean all

RUN pip3 install --upgrade pip setuptools wheel

COPY . /workspace
WORKDIR /workspace

RUN pip3 install -e ".[webui,pdf]" --no-build-isolation && \
    echo '' >> /root/.bashrc && \
    echo 'echo "╔══════════════════════════════════════╗"' >> /root/.bashrc && \
    echo 'echo "║   EdgeAI-DeployKit  Delivery Env   ║"' >> /root/.bashrc && \
    echo 'echo "║   edgeai --help   查看所有命令      ║"' >> /root/.bashrc && \
    echo 'echo "║   edgeai ui       启动 WebUI       ║"' >> /root/.bashrc && \
    echo 'echo "╚══════════════════════════════════════╝"' >> /root/.bashrc && \
    echo '' >> /root/.bashrc

EXPOSE 8501

CMD ["edgeai", "ui", "--host", "0.0.0.0", "--port", "8501"]
