##########
# Compile
##########
# First - compile the SCSS into static CSS
FROM node:latest AS compile_css
COPY . /code
WORKDIR /code/dds_web/static
RUN npm install
RUN npm run css

#########
# Run
#########

# Set official image -- parent image
FROM python:latest

# Copy the content to a code folder in container
COPY . /code

# Copy the compiled CSS from the first build step
COPY --from=compile_css /code/dds_web/static /code/dds_web/static

# Install some necessary systems packages
RUN apt-get update
RUN apt-get install -y gfortran libopenblas-dev liblapack-dev

# Install all dependencies
RUN pip3 install -r /code/requirements.txt

# Install DDS CLI for web upload
### TODO - Replace this with `dds_cli` when published to PyPI
RUN pip3 install git+https://github.com/ScilifelabDataCentre/dds_cli.git@master

# Install gnuicorn
RUN pip3 install gunicorn

# Add code directory in pythonpath
ENV PYTHONPATH /code

# Add parameters for gunicorn
ENV GUNICORN_CMD_ARGS "--bind=0.0.0.0:5000 --workers=2 --thread=4 --worker-class=gthread --forwarded-allow-ips='*' --access-logfile -"

# Set working directory - 'code' dir in container, 'code' dir locally (in code)
WORKDIR /code/dds_web

# Run app -- needs to be in WORKDIR
CMD ["gunicorn", "app:app"]
