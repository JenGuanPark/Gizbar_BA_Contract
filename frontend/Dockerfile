FROM nginx:alpine
# 这一步假设你已经在本地用 git 传了 dist，或者用 scp 传了 dist
# 如果你是走的 git push dist 方案，那么 dist 文件夹就在当前目录下
COPY dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
