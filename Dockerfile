FROM python:3.12-slim AS builder

ENV PYTHONUNBUFFERED=1

#Set working directory
WORKDIR /app

#Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    build-essential \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    postgresql-client \
    netcat-openbsd \
    dnsutils \
    awscli \
    gettext \
    locales \
    tzdata \
    bash \
    nano \
    curl \
    cron \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

#Install pipenv first
RUN pip install --upgrade pip pipenv

#Install dependencies
COPY Pipfile Pipfile.lock /app/

#Build argument to dynamically choose dev or production dependencies
ARG ENVIRONMENT

#Conditionally install dependencies based on environment
RUN if [ "$ENVIRONMENT" = "production" ] ; then \
  echo "Installing production dependencies..." && \
  pipenv install --system --deploy --ignore-pipfile; \
  else \
  echo "Installing development dependencies..." && \
  pipenv install --system --deploy --dev; \
  fi

COPY permissions.sh /usr/local/bin/permissions.sh
RUN chmod +x /usr/local/bin/permissions.sh

#Copy full app
COPY . /app/

#Create backup and logs directories
RUN mkdir -p /backups
RUN mkdir -p /logs

#Expose port
EXPOSE 8000

#Execute entrypoint.sh
ENTRYPOINT [ "permissions.sh" ]


#For development, run this:
#  ./deploy.dev.sh

#For production, run: 
#  ./deploy.prod.sh
