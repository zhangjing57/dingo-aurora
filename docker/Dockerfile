FROM python:3.9 AS builder

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

RUN apt-get update -y && apt-get install -y --no-install-recommends apt-utils \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    gcc make nginx traceroute lsof iputils-ping vim git wget curl locales-all ssl-cert \
    python3 python3-pip python3-dev python3-venv python-dev-is-python3

COPY . /opt/dingoops

RUN pip install -r /opt/dingoops/requirements.txt

RUN apt-get clean \
    && rm -rf ~/.cache/pip \
    && mkdir -p /etc/dingoops /var/log/dingoops /var/lib/dingoops

COPY ./etc/gunicorn.py /etc/dingoops/gunicorn.py
COPY ./docker/start_service.sh /usr/local/bin/start_service.sh
RUN chmod +x /usr/local/bin/start_service.sh
WORKDIR /opt/dingoops
EXPOSE 8889

CMD ["start_service.sh"]
