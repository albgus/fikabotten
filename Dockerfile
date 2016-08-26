FROM python:3

VOLUME /data
RUN useradd -u 500 -d /home/fika -m fika && chown fika /data/ && chmod 755 /data

COPY . /home/fika/
RUN pip3 install -r /home/fika/requirements.txt

USER fika
WORKDIR /home/fika
ENV FIKABOTTEN_CONFIG "/data/config.yaml"
ENTRYPOINT [ "python3", "./main.py" ]
