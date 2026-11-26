FROM docker.m.daocloud.io/library/node:22-alpine AS web-build
WORKDIR /app
COPY web/package.json web/package-lock.json* ./
RUN npm install
COPY web/ ./
RUN npm run build

FROM docker.m.daocloud.io/nginxinc/nginx-unprivileged:1.27-alpine AS web
COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=web-build /app/dist /usr/share/nginx/html
EXPOSE 8080
