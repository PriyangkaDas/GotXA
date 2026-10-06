FROM nginx:alpine

# Copy API gateway config
COPY webservers/api-gateway/nginx.conf /etc/nginx/nginx.conf

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:80/health || exit 1

EXPOSE 80
EXPOSE 443

CMD ["nginx", "-g", "daemon off;"]
