FROM python:3.8
COPY ./src/requirements.txt /src/requirements.txt
RUN pip3 install -r /src/requirements.txt
ADD /src /src
CMD kopf run /src/server.py