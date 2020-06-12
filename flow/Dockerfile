FROM ubuntu:18.04
RUN apt-get update && apt-get install -y docker.io
RUN apt-get install -y python3 python3-pip
COPY ./src/requirements.txt /src/requirements.txt
RUN pip3 install -r /src/requirements.txt
COPY ./src /src
WORKDIR /src
CMD ["python3", "job.py"]