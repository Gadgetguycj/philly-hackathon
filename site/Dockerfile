# Build context is the repository root, so GUIDE.md is in it:
#   docker build -f site/Dockerfile -t runpodtrack-site .
FROM python:3.12-alpine AS render
RUN pip install --no-cache-dir "markdown==3.10.3"
WORKDIR /src
COPY GUIDE.md ./GUIDE.md
COPY site/build.py site/style.css site/app.js ./site/
RUN python3 site/build.py --selftest && python3 site/build.py

FROM nginx:1.29-alpine
COPY site/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=render /src/site/dist/index.html /usr/share/nginx/html/index.html
EXPOSE 8080
