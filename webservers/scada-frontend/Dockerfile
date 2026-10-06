FROM nginx:alpine

# Copy nginx config
COPY webservers/scada-frontend/nginx.conf /etc/nginx/nginx.conf

# Serve the prebuilt dashboard. Place its generated assets directly in
# frontend/scada_dashboard/dist/ before building this image.
COPY frontend/scada_dashboard/dist/ /usr/share/nginx/html/

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
