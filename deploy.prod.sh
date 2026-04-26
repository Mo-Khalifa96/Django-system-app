#!/bin/bash
set -e

echo "Starting deployment..."

#Backup current config for rollback capability
cp nginx/nginx.conf nginx/nginx.conf.backup 2>/dev/null || true

#Rollback function to return to last functional state upon failure
rollback() {
    echo "Deployment failed - Rolling back nginx configuration..."
    if [ -f nginx/nginx.conf.backup ]; then
        cp nginx/nginx.conf.backup nginx/nginx.conf
        docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload 2>/dev/null || true
        echo "Rollback completed. Site should be accessible with previous configuration."
    fi
}
trap rollback ERR

#Function to switch nginx configuration
switch_nginx_config() {
    local config_type=$1
    echo "Switching to nginx $config_type configuration..."
    if [ "$config_type" = "http" ]; then
        cp nginx/http.conf nginx/nginx.conf
    elif [ "$config_type" = "https" ]; then
        cp nginx/https.conf nginx/nginx.conf
    else
        echo "Invalid config type: $config_type"
        exit 1
    fi
}


if [[ "$1" == "--rebuild" && "$2" == "--no-cache" ]]; then
    echo "Building production image with no cache..."
    docker compose -f docker-compose.prod.yml build --no-cache --build-arg ENVIRONMENT=production
elif [[ "$1" == "--rebuild" ]] || ! docker images --format "{{.Repository}}" | grep -qE "(system-app|systemapp)"; then
    echo "Building production image with production dependencies..."
    docker compose -f docker-compose.prod.yml build --build-arg ENVIRONMENT=production
else
    echo "Images already exist, skipping build..."
fi


echo "Processing CORS variables in HTTP config..."
CORS_ALLOWED_ORIGINS="$CORS_ALLOWED_ORIGINS" envsubst '$CORS_ALLOWED_ORIGINS' < nginx/http.conf > nginx/http.conf.tmp
mv nginx/http.conf.tmp nginx/http.conf


#Start with HTTP-only configuration
switch_nginx_config "http"


echo "Starting app services..."
docker compose -f docker-compose.prod.yml up -d postgres web qcluster postgres-backup


echo "Waiting for web service to be healthy..."
timeout 180 bash -c 'until docker compose -f docker-compose.prod.yml ps web | grep -q "healthy"; do 
    echo "Still waiting for web service..."; 
    sleep 5; 
done' || {
    echo "Web service failed. Stopping deployment..."
    exit 1  #exit if web isn't healthy for longer than 3 minutes 
}


echo "Now starting nginx..."
docker compose -f docker-compose.prod.yml up -d nginx

echo "Waiting for nginx to be ready..."
timeout 90 bash -c 'until docker compose -f docker-compose.prod.yml ps nginx | grep -q "Up"; do
    echo "Still waiting for nginx..."; 
    sleep 5; 
done' || {
    echo "Nginx failed to start. Stopping deployment..."
    exit 1   #exit if nginx failed to start within 90 seconds 
}

echo "Testing nginx configuration..."
docker compose -f docker-compose.prod.yml exec -T nginx nginx -t


echo "Creating ACME challenge directory..."
docker compose -f docker-compose.prod.yml exec -T nginx sh -c 'mkdir -p /var/www/certbot/.well-known/acme-challenge'


echo "Testing basic HTTP access..."
if ! curl -f --connect-timeout 10 --max-time 30 http://djsys.site/health/; then
    echo "HTTP access test failed! Stopping deployment..."
    exit 1   #exit if HTTP access fails
fi


echo "Creating ACME test file..."
docker compose -f docker-compose.prod.yml exec -T nginx sh -c 'echo "test" > /var/www/certbot/.well-known/acme-challenge/test'

echo "Testing ACME challenge path..."
if ! curl -f --connect-timeout 10 --max-time 30 http://djsys.site/.well-known/acme-challenge/test; then
    echo "ACME challenge path not accessible! Stopping deployment..."
    exit 1  #exit if ACME challenge path is not accessible 
fi


echo "Checking if certificates need renewal..."
if docker compose -f docker-compose.prod.yml run --rm certbot certificates 2>/dev/null | grep -q "INVALID\|will expire"; then
    echo "Certificates need renewal or don't exist"
    RENEWAL_FLAG="--force-renewal"
else
    echo "Certificates are valid, attempting normal renewal"
    RENEWAL_FLAG=""
fi

echo "Issuing/renewing certificates..."
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot --webroot-path=/var/www/certbot \
  --email mokhalifa96@yahoo.com \
  --agree-tos \
  --no-eff-email \
  --non-interactive \
  --keep-until-expiring \
  $RENEWAL_FLAG \
  -d djsys.site -d www.djsys.site
echo "Certificates obtained."


echo "Verifying certificates exist..."
if ! docker compose -f docker-compose.prod.yml exec -T nginx ls /etc/letsencrypt/live/djsys.site/ >/dev/null 2>&1; then
    echo "Certificates not found! Cannot switch to HTTPS. Stopping deployment..."
    exit 1
fi


echo "Processing CORS variables in HTTPS config..."
CORS_ALLOWED_ORIGINS="$CORS_ALLOWED_ORIGINS" envsubst '$CORS_ALLOWED_ORIGINS' < nginx/https.conf > nginx/https.conf.tmp
mv nginx/https.conf.tmp nginx/https.conf


#Switch to https
switch_nginx_config "https"

echo "Testing new HTTPS configuration..."
docker compose -f docker-compose.prod.yml exec -T nginx nginx -t

echo "Reloading nginx with HTTPS configuration..."
docker compose -f docker-compose.prod.yml exec -T nginx nginx -s reload
sleep 5


echo "Testing HTTPS access..."
if ! curl -f --connect-timeout 10 --max-time 30 https://djsys.site/health/; then
    echo "HTTPS access test failed! Check your certificates and nginx config. Stopping deployment..."
    exit 1  #exits if HTTPS access fails after nginx is loaded
fi


#Start certbot renewal loop
echo "Starting certbot renewal container..."
docker compose -f docker-compose.prod.yml up -d certbot


#Clean up backup file on success
rm -f nginx/nginx.conf.backup

#Declare deployment success 
echo "Deployment completed successfully!"


#To run, make sure you have permission:
    # chmod +x deploy.prod.sh
    # ./deploy.prod.sh 
    
#For force rebuild, run:
    # ./deploy.prod.sh --rebuild

#or (for building without cache):
    # ./deploy.prod.sh --rebuild --no-cache
