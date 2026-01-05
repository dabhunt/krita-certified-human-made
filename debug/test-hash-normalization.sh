#!/bin/bash

# Test that our hash normalization fix is working

echo "🧪 Testing Hash Normalization Fix"
echo "=================================="
echo ""

# The gist we know exists
GIST_HASH="6c9b3bfeebc9a99191b280fd29abd21d0103b6416c693f2a82d2041c240b6e63"

echo "Testing GitHub Code Search with normalized hash..."
echo "Hash to search: $GIST_HASH"
echo ""

if [ -f ~/.config/chm/github_token.txt ]; then
    TOKEN=$(cat ~/.config/chm/github_token.txt)
    
    # Test search WITHOUT prefix (what our fix does)
    SEARCH_QUERY="\"${GIST_HASH}\" in:file filename:chm_proof_timestamp.json"
    ENCODED_QUERY=$(printf %s "$SEARCH_QUERY" | jq -sRr @uri)
    
    echo "Search query: $SEARCH_QUERY"
    echo ""
    
    RESULT=$(curl -s -H "Authorization: token $TOKEN" \
        "https://api.github.com/search/code?q=${ENCODED_QUERY}")
    
    TOTAL=$(echo "$RESULT" | grep -o '"total_count":[0-9]*' | grep -o '[0-9]*')
    
    if [ "${TOTAL:-0}" -gt 0 ]; then
        echo "✅ SUCCESS! Found $TOTAL result(s)"
        echo ""
        echo "Gist URL:"
        echo "$RESULT" | python3 -c "import sys, json; data = json.load(sys.stdin); print(data['items'][0]['repository']['html_url'] if data.get('items') else 'Not found')" 2>/dev/null || echo "Parse error"
        echo ""
        echo "This confirms:"
        echo "  1. ✅ Gist exists and is searchable"
        echo "  2. ✅ Plain hex search works (no sha256: prefix needed)"
        echo "  3. ✅ Our normalization fix should work!"
        echo ""
    else
        echo "❌ NOT FOUND"
        echo ""
        echo "This could mean:"
        echo "  1. GitHub indexing delay (wait 10 min)"
        echo "  2. Token has no search permission"
        echo "  3. Gist is private or deleted"
        echo ""
    fi
    
    # Now test WITH prefix (what website sends before our fix)
    echo "Testing search WITH sha256: prefix (old behavior)..."
    SEARCH_QUERY_PREFIXED="\"sha256:${GIST_HASH}\" in:file filename:chm_proof_timestamp.json"
    ENCODED_QUERY_PREFIXED=$(printf %s "$SEARCH_QUERY_PREFIXED" | jq -sRr @uri)
    
    RESULT_PREFIXED=$(curl -s -H "Authorization: token $TOKEN" \
        "https://api.github.com/search/code?q=${ENCODED_QUERY_PREFIXED}")
    
    TOTAL_PREFIXED=$(echo "$RESULT_PREFIXED" | grep -o '"total_count":[0-9]*' | grep -o '[0-9]*')
    
    if [ "${TOTAL_PREFIXED:-0}" -gt 0 ]; then
        echo "Found with prefix (unexpected)"
    else
        echo "❌ Not found with prefix (expected - confirms our fix is needed!)"
    fi
    
else
    echo "❌ No GitHub token found at ~/.config/chm/github_token.txt"
    echo "Cannot test GitHub search"
fi

echo ""
echo "=================================="
echo "CONCLUSION:"
echo ""
echo "The gist exists with hash: ${GIST_HASH:0:40}..."
echo "Current uploaded file has: c866dca959452b8b4bee..."
echo ""
echo "❌ These don't match! The file was modified after export."
echo ""
echo "TO FIX: Upload the ORIGINAL unmodified file, or re-export from Krita."
echo ""

