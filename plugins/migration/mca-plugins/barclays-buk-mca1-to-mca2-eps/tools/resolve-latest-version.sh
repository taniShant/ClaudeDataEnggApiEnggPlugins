#!/bin/bash
# Resolves latest patch version from Nexus Maven metadata
# Usage: ./resolve-latest-version.sh <group_path> <artifact_id> <version_prefix>
# Example: ./resolve-latest-version.sh com/barclays/global/mca mca-dependencies 2.3
# Output: 2.3.026 (just the version string, no newline noise)

NEXUS_BASE="https://nexus.barcapint.com/nexus/content/groups/barclays"
GROUP_PATH="$1"
ARTIFACT_ID="$2"
VERSION_PREFIX="$3"

if [ -z "$GROUP_PATH" ] || [ -z "$ARTIFACT_ID" ] || [ -z "$VERSION_PREFIX" ]; then
  echo "ERROR: Usage: $0 <group_path> <artifact_id> <version_prefix>" >&2
  exit 1
fi

URL="${NEXUS_BASE}/${GROUP_PATH}/${ARTIFACT_ID}/maven-metadata.xml"
METADATA=$(curl -sf --connect-timeout 10 --max-time 30 "$URL" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$METADATA" ]; then
  echo "ERROR: Failed to fetch metadata from ${URL}" >&2
  exit 2
fi

# Extract <version> tags, filter by prefix, sort numerically, take last
LATEST=$(echo "$METADATA" \
  | grep -oE "<version>[^<]+</version>" \
  | sed 's/<[^>]*>//g' \
  | grep -E "^${VERSION_PREFIX}\.[0-9]+$" \
  | sort -t. -k1,1n -k2,2n -k3,3n \
  | tail -1)

if [ -z "$LATEST" ]; then
  echo "ERROR: No version matching prefix '${VERSION_PREFIX}' found for ${ARTIFACT_ID}" >&2
  exit 3
fi

echo "$LATEST"
