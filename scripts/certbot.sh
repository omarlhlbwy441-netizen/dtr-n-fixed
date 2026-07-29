#!/bin/bash
# Rafeeq Kernel v2.3.0 — SSL Certificate Generation

DOMAIN="${1:-rafeeq.ai}"
EMAIL="${2:-admin@rafeeq.ai}"

echo "🔐 Generating SSL certificate for $DOMAIN"

# Using certbot with standalone mode
docker run -it --rm   -p 80:80   -v $(pwd)/nginx/ssl:/etc/letsencrypt   certbot/certbot certonly   --standalone   --preferred-challenges http   -d $DOMAIN   -d www.$DOMAIN   --agree-tos   --no-eff-email   -m $EMAIL

echo "✅ Certificate generated at nginx/ssl/"
echo "   Fullchain: nginx/ssl/live/$DOMAIN/fullchain.pem"
echo "   Privkey:   nginx/ssl/live/$DOMAIN/privkey.pem"
