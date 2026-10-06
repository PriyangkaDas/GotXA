FROM nginx:alpine

# Copy nginx config
COPY webservers/corp-portal-frontend/nginx.conf /etc/nginx/nginx.conf

# Serve the prebuilt portal. Build the frontend outside Docker and place the
# resulting assets in frontend/corp_portal/dist/ before building this image.
COPY frontend/corp_portal/dist/ /usr/share/nginx/html/
COPY webservers/corp-portal-frontend/light-theme-overrides.css /usr/share/nginx/html/light-theme-overrides.css

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
