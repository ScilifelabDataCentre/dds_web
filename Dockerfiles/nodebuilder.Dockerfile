FROM node:25
RUN mkdir /build
WORKDIR /build
RUN npm install -g npm@10.9.2 --quiet
RUN echo "npm install --quiet && npm run watch" > /runner.sh
CMD ["sh", "/runner.sh"]
