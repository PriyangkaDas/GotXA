FROM nginx:alpine

# Copy nginx config
COPY webservers/siem-soar-frontend/nginx.conf /etc/nginx/nginx.conf

# Serve the prebuilt SIEM dashboard. Place its generated assets directly in
# frontend/siem_dashboard/dist/ before building this image.
COPY frontend/siem_dashboard/dist/ /usr/share/nginx/html/

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
