#!/bin/bash
# Wrapper script - redirects to Task1/test-pkce.sh

echo "Redirecting to Task1/test-pkce.sh..."
echo ""

cd "$(dirname "$0")/Task1" && ./test-pkce.sh
