FROM node:24-alpine AS build
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci
COPY frontend ./
ENV VITE_API_URL=/api
RUN npm run build
FROM nginxinc/nginx-unprivileged:1.28-alpine
COPY --from=build /web/dist /usr/share/nginx/html
COPY deploy/nginx.conf.template /opt/qa-nginx.conf.template
COPY deploy/frontend-entrypoint.sh /opt/qa-entrypoint.sh
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=5s CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
ENTRYPOINT ["/bin/sh","/opt/qa-entrypoint.sh"]
