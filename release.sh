#!/bin/bash
# Quick release script - wrapper for scripts/create-release.sh
# Place in project root for easy access

# Forward all arguments to the actual release script
./scripts/create-release.sh "$@"

