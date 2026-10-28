#!/bin/bash
# Dev helper: export telemetry to website's public folder for local testing
# Usage: DETOX_WEBSITE_DIR=/path/to/detoxWebsite/detox ./scripts/dev_export.sh

if [ -z "${DETOX_WEBSITE_DIR}" ]; then
    echo "❌ DETOX_WEBSITE_DIR is not set — point it at your local detoxWebsite/detox checkout" >&2
    exit 1
fi

WEBSITE_DIR="${DETOX_WEBSITE_DIR}"
OUTPUT_PATH="${WEBSITE_DIR}/public/telemetry/usage-report.json"

mkdir -p "$(dirname "$OUTPUT_PATH")"

echo "{\"period\": \"all\", \"output_path\": \"${OUTPUT_PATH}\"}" | python3 "$(dirname "$0")/export_telemetry.py"

echo "✅ Exported to: ${OUTPUT_PATH}"
echo "   Website at http://localhost:5174/dashboard will show updated data"
