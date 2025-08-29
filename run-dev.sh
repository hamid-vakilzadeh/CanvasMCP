#!/bin/bash
set -e

# macOS - load from Keychain
export UNKEY_API=$(security find-generic-password -s "UNKEY_API" -w)
export POSTHOG_API_KEY=$(security find-generic-password -s "POSTHOG_API_KEY" -w)
export ENCRYPTION_SECRET=$(security find-generic-password -s "ENCRYPTION_SECRET" -w)

# Analytics Configuration
export ANALYTICS_ENABLED="true"
export POSTHOG_HOST="https://us.i.posthog.com"


exec uv run src/index.py "$@"