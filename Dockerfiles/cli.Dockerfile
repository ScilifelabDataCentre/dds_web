FROM python:3.10-alpine as base

RUN apk update && apk upgrade
RUN apk add g++ gcc musl-dev libffi-dev
RUN apk add --no-cache git
RUN git clone https://github.com/ScilifelabDataCentre/dds_cli /code
WORKDIR /code

# Install all dependencies
RUN pip3 install -r /code/requirements.txt

# Add code directory in pythonpath
ENV PYTHONPATH /code

CMD ["tail", "-f", "/dev/null"] # to keep container running
