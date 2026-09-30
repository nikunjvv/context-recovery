#!/usr/bin/env bash

set -u

APP_HOME="${APP_HOME:-/opt/northstar/billing}"
LOG_DIR="${LOG_DIR:-${APP_HOME}/logs}"
BUSINESS_DATE="${1:-$(date +%Y-%m-%d)}"
RERATE_PROGRAM="${APP_HOME}/bin/rerate_usage"
LOG_FILE="${LOG_DIR}/rerate_${BUSINESS_DATE}.log"

mkdir -p "${LOG_DIR}"

echo "Starting nightly rerating for ${BUSINESS_DATE}" >> "${LOG_FILE}"

if [[ ! -x "${RERATE_PROGRAM}" ]]; then
    echo "ERROR: ${RERATE_PROGRAM} is unavailable" >> "${LOG_FILE}"
    exit 1
fi

if "${RERATE_PROGRAM}" "${BUSINESS_DATE}" >> "${LOG_FILE}" 2>&1; then
    echo "Nightly rerating completed successfully" >> "${LOG_FILE}"
    exit 0
else
    return_code=$?
    echo "ERROR: rerating failed with code ${return_code}" >> "${LOG_FILE}"
    exit "${return_code}"
fi
