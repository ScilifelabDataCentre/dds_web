#!/bin/bash
if [[ $(docker images dds_web_nodebuilder -q | wc -l) -eq 0 ]] ; then
    docker build -f compile_css.Dockerfile . -t dds_web_nodebuilder
fi
docker run -it -v `pwd`/dds_web/static:/build:rw --rm dds_web_nodebuilder
