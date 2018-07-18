FROM python:2-alpine

RUN addgroup -g 1000 -S appuser && \
    adduser -u 1000 -S appuser -G appuser

ENV ES_HOST http://elasticsearch:9200/
ENV GH_AUTH_TOKEN gh_auth_token
ENV GH_ORG gh_org
ENV GH_USER gh_user
ENV GHE_AUTH_TOKEN ghe_auth_token
ENV GHE_HOST http://ghe/
ENV GHE_USER ghe_user
ENV JIRA_HOST https://jira/

RUN apk update && apk upgrade
RUN apk add \
    ca-certificates \
    curl \
    g++ \
    gcc \
    git \
    libffi-dev \
    libxml2 \
    libxml2-dev \
    libxslt-dev \
    make \
    zlib-dev && \
    rm -rf /var/cache/apk

ADD . /app/server

WORKDIR /app

RUN pip install -r server/requirements.txt

RUN curl -o /usr/local/bin/mantra -L \
    https://github.com/acrewdson/mantra/releases/download/0.0.2/mantra && \
    chmod +x /usr/local/bin/mantra

ENV PYTHONPATH=$PYTHONPATH:/app

USER appuser
# note that the cron line below is UTC
CMD ["/usr/local/bin/mantra", "01 01 09 * * *", "python", "/app/server/index.py"]
