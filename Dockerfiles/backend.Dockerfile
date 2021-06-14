##############################
## Compile dist CSS
##############################
FROM node:15-alpine AS compile_css
COPY ./dds_web/static /code/
WORKDIR /code/
RUN npm install -g npm@latest --quiet
RUN npm install --quiet
RUN npm run css

#############################
## Build main container
#############################

# Set official image -- parent image
FROM python:latest

# Install some necessary systems packages
RUN apt-get update && apt-get install -y gfortran libopenblas-dev liblapack-dev

# Copy the content to a code folder in container
COPY ./requirements.txt /code/requirements.txt

# Copy the compiled CSS from the first build step
COPY --from=compile_css /code/ /code/dds_web/static

# Install all dependencies
RUN pip3 install -r /code/requirements.txt && pip3 install gunicorn

# Install DDS CLI for web upload
### TODO - Replace this with `dds_cli` when published to PyPI
### TODO - NOT FOR USE IN PRODUCTION! CURRENTLY USING DEV BRANCH
RUN pip3 install git+https://github.com/ScilifelabDataCentre/dds_cli.git@dev

# Copy the content to a code folder in container
COPY . /code

# Add code directory in pythonpath
ENV PYTHONPATH /code

# Add parameters for gunicorn
ENV GUNICORN_CMD_ARGS "--bind=0.0.0.0:5000 --workers=2 --thread=4 --worker-class=gthread --forwarded-allow-ips='*' --access-logfile -"

# Set working directory - 'code' dir in container, 'code' dir locally (in code)
WORKDIR /code/dds_web

# Run app -- needs to be in WORKDIR
CMD ["gunicorn", "app:app"]
