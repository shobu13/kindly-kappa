FROM node:16.17

WORKDIR /usr/src/app

ARG NODE_ENV
ENV NODE_ENV $NODE_ENV

COPY package.json /usr/src/app/
RUN npm install

COPY . /usr/src/app

EXPOSE 5173
CMD [ "npm", "run", "dev" ]
