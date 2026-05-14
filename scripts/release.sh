#!/bin/bash
# Usage: ./scripts/release.sh "Release notes here"
set -e

VERSION=$(grep '"version"' custom_components/dhl_parcels/manifest.json | grep -oP '[\d.]+')
NOTES=${1:-"See CHANGELOG.md"}
TOKEN=$(cat ~/.github_token)

# Check if release already exists
EXISTING=$(curl -s -H "Authorization: token $TOKEN" \
  https://api.github.com/repos/vinceke44/home-assistant-dhl-parcels/releases/tags/v$VERSION \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null)

if [ -n "$EXISTING" ]; then
  echo "Release v$VERSION already exists (id: $EXISTING), skipping."
  exit 0
fi

git tag "v$VERSION" 2>/dev/null || true
git push origin "v$VERSION" 2>/dev/null || true

curl -s -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/vinceke44/home-assistant-dhl-parcels/releases \
  -d "{\"tag_name\":\"v$VERSION\",\"name\":\"v$VERSION\",\"body\":\"$NOTES\",\"draft\":false,\"prerelease\":false}" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('Release:', d.get('html_url')) if 'html_url' in d else print('Error:', d)"
