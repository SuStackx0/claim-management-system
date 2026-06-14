# React UI — built with Node, served by nginx (which also reverse-proxies the
# API, so the browser uses one origin and needs no CORS / API host config).
#
# Build context is this service's own directory (frontend/, set in
# docker-compose.yml), so every COPY path is relative to frontend/. The sibling
# frontend/.dockerignore keeps host node_modules/dist out of the context — host
# node_modules MUST never be copied in, or macOS-native esbuild/rollup binaries
# clobber the container's Linux ones and the build fails.

# --- build stage -----------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci 2>/dev/null || npm install
COPY . ./
RUN npm run build

# --- serve stage -----------------------------------------------------------
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
