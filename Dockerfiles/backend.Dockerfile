#############################
## Build main API container
#############################

# Set official image -- parent image
FROM python:3.10-alpine as base

# Update and upgrade
RUN apk update && apk upgrade

# Install required dependencies...
# ...Some for build
RUN apk add g++ gcc musl-dev libffi-dev

# ...Some for requirements
RUN apk add jpeg-dev zlib-dev libjpeg

# Set time zone
RUN apk add tzdata
ENV TZ="America/New_York"

# Copy the content to a code folder in container
COPY ./requirements.txt /code/requirements.txt

# Install all dependencies
RUN pip3 install -r /code/requirements.txt

# Copy the content to a code folder in container
COPY . /code

# Add code directory in pythonpath
ENV PYTHONPATH /code

###################
## TEST CONTAINER
###################
FROM base as test
RUN pip3 install -r /code/tests/requirements-test.txt
RUN apk add mariadb-client

###################
## BUILD FRONTEND
###################
FROM node:16 as nodebuilder
COPY ./dds_web/static /build
WORKDIR /build
RUN npm install -g npm@latest --quiet
RUN npm install --quiet
RUN npm run css

#########################
## PRODUCTION CONTAINER
#########################
FROM base as production

RUN pip install gunicorn

# Add parameters for gunicorn
ENV GUNICORN_CMD_ARGS "--bind=0.0.0.0:5000 --workers=2 --thread=4 --worker-class=gthread --forwarded-allow-ips='*' --access-logfile -"

# Set working directory - 'code' dir in container, 'code' dir locally (in code)
WORKDIR /code/dds_web

# Get the built frontend
COPY --from=nodebuilder /build ./static

# Run app -- needs to be in WORKDIR
CMD ["gunicorn", "run_app:app_obj"]
