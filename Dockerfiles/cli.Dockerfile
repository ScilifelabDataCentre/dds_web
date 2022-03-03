FROM python:latest as base

RUN apt-get update && apt-get upgrade -y && apt-get install git
RUN git clone https://github.com/ScilifelabDataCentre/dds_cli /code
WORKDIR /code

# Install all dependencies
RUN pip3 install -r /code/requirements.txt

# Add code directory in pythonpath
ENV PYTHONPATH /code

CMD ["tail", "-f", "/dev/null"] # to keep container running
