FROM node:15-alpine
RUN mkdir /build
WORKDIR /build
RUN npm install -g npm@latest --quiet
RUN echo "npm install --quiet && npm run watch" > /runner.sh
CMD ["sh", "/runner.sh"]
