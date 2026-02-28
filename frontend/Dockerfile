FROM node:20-alpine AS builder

WORKDIR /web
COPY package.json tsconfig.json tsconfig.app.json tsconfig.node.json vite.config.ts index.html /web/
COPY src /web/src
RUN npm install && npm run build

FROM nginx:1.27-alpine
COPY --from=builder /web/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
