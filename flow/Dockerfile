FROM ubuntu:18.04
RUN apt-get update && apt-get install -y docker.io
RUN DEBIAN_FRONTEND=noninteractive apt-get install  -y dnsutils file ftp iproute2 iputils-ping jq libcurl3 libgbm-dev  libunwind8 locales netcat
RUN DEBIAN_FRONTEND=noninteractive apt-get install  -y openssh-client parallel rsync shellcheck telnet unzip upx wget zip time zstd gnupg2 lib32z1 awscli


RUN DEBIAN_FRONTEND=noninteractive apt-get install -y apt-transport-https gnupg2 curl
COPY --from=lachlanevenson/k8s-kubectl:v1.18.3 /usr/local/bin/kubectl /usr/local/bin/kubectl


RUN apt-get install -y python3 python3-pip python3-venv
RUN curl -sL https://deb.nodesource.com/setup_12.x |  bash -
RUN apt-get install -y nodejs build-essential

COPY ./src/requirements.txt /src/requirements.txt
RUN pip3 install -r /src/requirements.txt
COPY ./src /src
WORKDIR /src
CMD ["python3", "job.py"]