#!/bin/bash

# Setup script for local HTTPS development

echo "Setting up local HTTPS development environment..."

# Check if mkcert is installed
if ! command -v mkcert &> /dev/null; then
    echo "mkcert is not installed. Please install it first:"
    echo "  macOS: brew install mkcert"
    echo "  Linux: Check https://github.com/FiloSottile/mkcert#installation"
    exit 1
fi

# Create certs directory
mkdir -p certs

# Install local CA (if not already done)
echo "Installing local CA..."
mkcert -install

# Generate certificate for localhost
echo "Generating certificate for localhost..."
cd certs
mkcert localhost 127.0.0.1 ::1
cd ..

echo "HTTPS setup complete!"
echo ""
echo "To run with HTTPS:"
echo "  docker-compose -f docker-compose.https.yml up"
echo ""
echo "Access the server at:"
echo "  https://localhost"