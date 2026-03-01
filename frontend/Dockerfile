# Stage 1: Serve the pre-built application with Nginx
# We assume the `dist` folder is already built locally and copied here
FROM nginx:alpine

# Copy the pre-built dist folder from the build context (which will be ./dist)
COPY dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
