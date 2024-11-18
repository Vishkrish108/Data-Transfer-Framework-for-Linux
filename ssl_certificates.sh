#!/bin/bash

# Define the output file names
KEY_FILE="key.pem"
CERT_FILE="cert.pem"

# Generate a private key
openssl genpkey -algorithm RSA -out $KEY_FILE -pkeyopt rsa_keygen_bits:2048

# Generate a certificate signing request (CSR)
openssl req -new -key $KEY_FILE -out csr.pem -subj "/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=example.com"

# Generate a self-signed certificate
openssl x509 -req -days 365 -in csr.pem -signkey $KEY_FILE -out $CERT_FILE

# Clean up the CSR
rm csr.pem

echo "SSL certificates generated: $KEY_FILE and $CERT_FILE"