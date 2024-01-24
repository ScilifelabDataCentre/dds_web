#############################
## Build main API container
#############################

# Set official image -- parent image
FROM python:3.10-alpine as base

ARG USERNAME=dds-user
ARG USER_UID=10600
ARG GROUPNAME=$USERNAME
ARG USER_GID=$USER_UID

# Create the user
RUN addgroup -g $USER_GID $GROUPNAME \
    && adduser -D -u $USER_UID -G $GROUPNAME $USERNAME \
    && chown -R $USERNAME:$GROUPNAME /usr/local/lib/python3.10/site-packages

# Update and upgrade
RUN apk update && apk upgrade

# Install required dependencies...
# ...Some for build
RUN apk add g++ gcc musl-dev libffi-dev

# ...Some for requirements
RUN apk add jpeg-dev zlib-dev libjpeg

# Set time zone
RUN apk add tzdata
ENV TZ="UCT"

# Extract version from Github during build
ARG version
ENV DDS_VERSION=$version

# Copy the content to a code folder in container
COPY ./requirements.txt /code/requirements.txt

# Install all dependencies
RUN pip3 install -r /code/requirements.txt

# Copy the content to a code folder in container - The owner is the dds user created
COPY --chown=$USER_UID:$USER_GID . /code

# Add code directory in pythonpath
ENV PYTHONPATH /code

###################
## TEST CONTAINER
###################
FROM base as test
RUN pip3 install -r /code/tests/requirements-test.txt
RUN apk add mariadb-client

# Switch to the user
USER $USERNAME
# Declare coverage file
RUN COVERAGE_FILE=/code/coverage/.coverage

###################
## BUILD FRONTEND
###################
FROM node:18 as nodebuilder
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

# Switch to the user
USER $USERNAME

# Run app -- needs to be in WORKDIR
CMD ["gunicorn", "run_app:app_obj"]
