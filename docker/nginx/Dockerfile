FROM nginx:1.29-alpine

# openssl for certificate inspection, gettext for envsubst
RUN apk add --no-cache openssl gettext

COPY site.conf.template /etc/nginx/site.conf.template
COPY entrypoint.d/ /docker-entrypoint.d/
RUN chmod +x /docker-entrypoint.d/*.sh

# Keep the image's own command: its entrypoint runs /docker-entrypoint.d/
# scripts only when the command starts with "nginx". The periodic reload lives
# in 30-reload-loop.sh instead.
