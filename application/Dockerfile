# build frontend
FROM node:22-alpine as build

WORKDIR /usr/src/app

COPY frontend/package.json ./
# install all dependencies (including devDependencies) so that the
# Angular CLI (`ng`) is available for the build step.
RUN npm install

COPY frontend/ .
ARG configuration=production
RUN npm run build -- --output-path=./dist/out --configuration $configuration

# build backend
FROM node:22-alpine

WORKDIR /usr/src/app

COPY backend/package*.json ./
RUN npm install

COPY backend/ .
RUN npm run build

# copy frontend static content
COPY --from=build /usr/src/app/dist/out/ /usr/src/app/public/

EXPOSE 8080
CMD [ "node", "server.js" ]
