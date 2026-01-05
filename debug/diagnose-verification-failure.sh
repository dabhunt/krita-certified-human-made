#!/bin/bash

# Bug#009 Verification Failure Diagnostic Script
# Run this after a failed verification to gather debug information

echo "🔍 Bug#009 Verification Failure Diagnostics"
echo "==========================================="
echo ""

# Get the file hash from user
echo "Enter the file hash from browser console (sha256:... format):"
read -r FILE_HASH

# Remove sha256: prefix for searching
NORMALIZED_HASH="${FILE_HASH#sha256:}"

echo ""
echo "📋 1. Checking Krita Plugin Logs"
echo "================================="
echo ""

if [ -f ~/.local/share/chm/plugin_debug.log ]; then
    echo "Recent gist creation attempts:"
    echo ""
    tail -100 ~/.local/share/chm/plugin_debug.log | grep -A 5 "GITHUB.*Gist created" | tail -20
    echo ""
    
    echo "Recent file hash values stored:"
    echo ""
    tail -100 ~/.local/share/chm/plugin_debug.log | grep "GITHUB-DEBUG.*File hash" | tail -5
    echo ""
else
    echo "❌ Plugin debug log not found at ~/.local/share/chm/plugin_debug.log"
    echo ""
fi

echo "📋 2. Checking GitHub Gists"
echo "============================"
echo ""

# Check if GitHub CLI is installed
if command -v gh &> /dev/null; then
    echo "Searching your gists for this file hash..."
    echo ""
    gh gist list --limit 10
    echo ""
else
    echo "⚠️  GitHub CLI (gh) not installed. Manual check needed:"
    echo "   1. Go to https://gist.github.com/[your-username]"
    echo "   2. Look for recent gist with title starting with 'CHM Proof:'"
    echo "   3. Check if file_hash matches: ${NORMALIZED_HASH:0:40}..."
    echo ""
fi

echo "📋 3. Checking GitHub Token Configuration"
echo "=========================================="
echo ""

# Check plugin token
if [ -f ~/.config/chm/github_token.txt ]; then
    TOKEN_LENGTH=$(wc -c < ~/.config/chm/github_token.txt | tr -d ' ')
    echo "✅ Plugin GitHub token found (${TOKEN_LENGTH} chars)"
else
    echo "❌ Plugin GitHub token NOT found at ~/.config/chm/github_token.txt"
fi

# Check website token (for website repo)
WEBSITE_DIR="/Users/david/Documents/GitHub/certified-human-made"
if [ -d "$WEBSITE_DIR" ]; then
    cd "$WEBSITE_DIR" || exit
    
    # Check if .env or config has token
    if [ -f .env ]; then
        if grep -q "GITHUB_TOKEN" .env; then
            echo "✅ Website GitHub token found in .env"
        else
            echo "❌ Website GITHUB_TOKEN not in .env"
        fi
    else
        echo "⚠️  Website .env file not found"
    fi
fi

echo ""
echo "📋 4. Testing GitHub API Access"
echo "================================"
echo ""

# Test if we can search GitHub
if [ -f ~/.config/chm/github_token.txt ]; then
    TOKEN=$(cat ~/.config/chm/github_token.txt)
    
    echo "Testing GitHub API rate limit..."
    RATE_LIMIT=$(curl -s -H "Authorization: token $TOKEN" https://api.github.com/rate_limit)
    
    CORE_REMAINING=$(echo "$RATE_LIMIT" | grep -A 3 '"core"' | grep "remaining" | grep -o '[0-9]*')
    SEARCH_REMAINING=$(echo "$RATE_LIMIT" | grep -A 3 '"search"' | grep "remaining" | grep -o '[0-9]*' | head -1)
    
    echo "   Core API remaining: ${CORE_REMAINING:-unknown}"
    echo "   Search API remaining: ${SEARCH_REMAINING:-unknown}"
    echo ""
    
    if [ "${SEARCH_REMAINING:-0}" -lt 5 ]; then
        echo "⚠️  WARNING: Low search API quota! May be rate limited."
    fi
    
    echo "Testing GitHub Code Search for your file hash..."
    SEARCH_QUERY="\"${NORMALIZED_HASH:0:40}\" in:file filename:chm_proof_timestamp.json"
    ENCODED_QUERY=$(echo "$SEARCH_QUERY" | jq -sRr @uri)
    
    echo "   Query: $SEARCH_QUERY"
    echo ""
    
    SEARCH_RESULT=$(curl -s -H "Authorization: token $TOKEN" \
        "https://api.github.com/search/code?q=${ENCODED_QUERY}")
    
    TOTAL_COUNT=$(echo "$SEARCH_RESULT" | grep -o '"total_count":[0-9]*' | grep -o '[0-9]*')
    
    if [ "${TOTAL_COUNT:-0}" -gt 0 ]; then
        echo "✅ FOUND! GitHub search returned ${TOTAL_COUNT} result(s)"
        echo ""
        echo "Gist URL:"
        echo "$SEARCH_RESULT" | grep -o '"html_url":"https://gist.github.com/[^"]*"' | head -1 | cut -d'"' -f4
        echo ""
    else
        echo "❌ NOT FOUND! GitHub search returned 0 results"
        echo ""
        echo "Possible causes:"
        echo "   1. Gist wasn't created (check plugin logs above)"
        echo "   2. GitHub indexing delay (wait 10 minutes, try again)"
        echo "   3. File hash mismatch between plugin and website"
        echo ""
        
        # Show raw response for debugging
        if echo "$SEARCH_RESULT" | grep -q "message"; then
            echo "Error message from GitHub:"
            echo "$SEARCH_RESULT" | grep -o '"message":"[^"]*"'
            echo ""
        fi
    fi
else
    echo "⚠️  Cannot test GitHub API - no token configured"
    echo ""
fi

echo "📋 5. Hash Comparison"
echo "====================="
echo ""

echo "File hash from browser:  $FILE_HASH"
echo "Normalized for search:   $NORMALIZED_HASH"
echo ""

if [ -f ~/.local/share/chm/plugin_debug.log ]; then
    echo "Recent file hashes from plugin logs:"
    tail -100 ~/.local/share/chm/plugin_debug.log | grep "File hash" | tail -3
    echo ""
fi

echo ""
echo "🔍 DIAGNOSTIC SUMMARY"
echo "====================="
echo ""
echo "Next steps:"
echo "1. ✅ Verify gist was created (check section 1 above)"
echo "2. ✅ Verify file_hash in gist matches normalized hash"
echo "3. ✅ Ensure GitHub tokens configured (check section 3)"
echo "4. ✅ Check GitHub search found the gist (section 4)"
echo "5. ⏰ If not found, wait 10 minutes for GitHub indexing"
echo "6. 🔄 Try verification again"
echo ""
echo "If gist exists but still not found:"
echo "   → Check website server logs for [VERIFY-*] messages"
echo "   → Ensure website code updated and server restarted"
echo "   → Manually verify gist structure matches expected format"
echo ""

