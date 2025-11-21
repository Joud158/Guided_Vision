# Guided_Vision/frontend/Dockerfile

FROM nginx:alpine

# Copy your dashboard to Nginx web root
COPY index.html /usr/share/nginx/html/index.html

# If later you add css/js, you can instead do:
# COPY . /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
