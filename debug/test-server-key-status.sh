#!/bin/bash
# Test Server ED25519 Key Configuration
# Checks the diagnostic endpoint to see key status

echo "=================================================="
echo "Testing Server ED25519 Key Configuration"
echo "=================================================="
echo ""

# Get your Replit URL (update this!)
REPLIT_URL="https://certified-human-made.org"

echo "Checking key status at: $REPLIT_URL/debug/key-status"
echo ""

# Make request
response=$(curl -s "$REPLIT_URL/debug/key-status")

echo "Response:"
echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
echo ""

# Parse and analyze
echo "=================================================="
echo "Analysis:"
echo "=================================================="

if echo "$response" | grep -q '"exists": true'; then
    echo "✓ ED25519_PRIVATE_KEY exists in environment"
    
    length=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('length', 'unknown'))")
    echo "  Length: $length chars"
    
    has_backslash_n=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('hasBackslashN', False))")
    echo "  Has \\n sequences: $has_backslash_n"
    
    has_newline=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('hasActualNewline', False))")
    echo "  Has actual newlines: $has_newline"
    
    starts_begin=$(echo "$response" | python3 -c "import sys, json; print(json.load(sys.stdin).get('startsWithBegin', False))")
    echo "  Starts with -----BEGIN: $starts_begin"
    
    echo ""
    
    # Determine if format is correct
    if [ "$has_backslash_n" = "True" ] && [ "$has_newline" = "False" ] && [ "$starts_begin" = "True" ]; then
        echo "✅ KEY FORMAT LOOKS CORRECT!"
        echo ""
        echo "Next step: The key format is correct, but parsing still fails."
        echo "This might be a Node.js crypto module issue."
        echo ""
        echo "Check Replit logs for the detailed diagnostic output:"
        echo "  [SIGN-3a] through [SIGN-3e]"
        echo ""
        echo "If those logs don't appear, TypeScript wasn't recompiled."
        echo "Run on Replit:"
        echo "  rm -rf dist/"
        echo "  npm run build"
    else
        echo "❌ KEY FORMAT IS WRONG!"
        echo ""
        echo "Expected:"
        echo "  - Has \\n sequences: True"
        echo "  - Has actual newlines: False"
        echo "  - Starts with -----BEGIN: True"
        echo ""
        echo "Fix: Update Replit Secret with correct format:"
        echo "  -----BEGIN PRIVATE KEY-----\\nKEY_DATA\\n-----END PRIVATE KEY-----\\n"
    fi
    
elif echo "$response" | grep -q '"exists": false'; then
    echo "❌ ED25519_PRIVATE_KEY NOT SET"
    echo ""
    echo "Fix: Add to Replit Secrets:"
    echo "  Key: ED25519_PRIVATE_KEY"
    echo "  Value: -----BEGIN PRIVATE KEY-----\\nMC4CAQAwBQYDK2VwBCIEIFtXkKfItc4mh4CowZ6l60QnGhVrGAfTcsCpwjXZA6dv\\n-----END PRIVATE KEY-----\\n"
else
    echo "❌ UNEXPECTED RESPONSE"
    echo ""
    echo "The diagnostic endpoint might not be deployed yet."
    echo "Wait for Replit to rebuild, then try again."
fi

echo ""

