# Tamper Resistance Tests - Quick Reference

## Running Tests

```bash
# Run all tests
./tests/run-tamper-tests.sh

# Run with Python directly
python3 tests/test_tamper_resistance.py

# Run with verbose output
./tests/run-tamper-tests.sh --verbose

# Run for CI/CD
./tests/ci-tamper-tests.sh

# Run with coverage
./tests/ci-tamper-tests.sh --coverage
```

## Test Coverage Summary

| # | Test | What It Validates |
|---|------|-------------------|
| 01 | Signing Key Loaded | Key is set and accessible |
| 02 | Missing Key Handling | Graceful failure without key |
| 03 | Valid Proof Generation | All fields present and correct |
| 04 | Signature Verification | Valid proofs pass verification |
| 05 | Tamper: Classification | Modified classification detected |
| 06 | Tamper: Event Counts | Modified event counts detected |
| 07 | Tamper: Events Hash | Modified events hash detected |
| 08 | Tamper: Signature | Modified signature detected |
| 09 | Tamper: Layer Count | Modified layer count detected |
| 10 | Tamper: Import Count | Modified import count detected |
| 11 | Tamper: AI Metadata | Modified AI tools detected |
| 12 | Signature Determinism | Same data = same signature |
| 13 | Non-Critical Fields | Timestamps don't break signature |
| 14 | Multiple Tampering | Multiple changes detected |
| 15 | JSON Serialization | Round-trip through JSON works |
| 16 | File-Based Verification | Load and verify from file |
| 17 | AI-Assisted Classification | AI-assisted proofs work |
| 18 | Empty Session | 0 events session works |
| 19 | Signature Version | Version field handled correctly |
| 20 | Large Proof | 1000+ events handled |

## Expected Results

**All tests should PASS (20/20)**

```
======================================================================
TEST SUMMARY
======================================================================
Tests run: 20
Successes: 20
Failures: 0
Errors: 0
======================================================================
```

## What Gets Signed (Critical Fields)

These fields are included in the HMAC signature and **CANNOT be modified**:

- ✅ `version` - Proof format version
- ✅ `session_id` - Session identifier
- ✅ `events_hash` - Hash of all events
- ✅ `file_hash` - Hash of exported artwork
- ✅ `classification` - HumanMade/AI-Assisted/MixedMedia
- ✅ `event_summary.total_events` - Total event count
- ✅ `event_summary.stroke_count` - Stroke count
- ✅ `event_summary.layer_count` - Layer count
- ✅ `event_summary.import_count` - Import count
- ✅ `metadata.ai_tools_used` - AI tools flag
- ✅ `metadata.ai_tools_list` - List of AI tools
- ✅ `signature_version` - Signature version

## What's NOT Signed (Non-Critical Fields)

These fields **CAN be modified** without breaking the signature:

- ⚪ `start_time` - Session start timestamp
- ⚪ `end_time` - Session end timestamp
- ⚪ `duration_seconds` - Session duration
- ⚪ `document_id` - Document identifier

## Troubleshooting

### All Tests Failing

```bash
# Check Python version (need 3.7+)
python3 --version

# Check plugin directory exists
ls -la krita-plugin/chm_verifier/chm_core.py

# Check for import errors
python3 -c "import sys; sys.path.insert(0, 'krita-plugin/chm_verifier'); import chm_core"
```

### Specific Test Failing

```bash
# Run just that test
python3 -m unittest tests.test_tamper_resistance.TamperResistanceTestSuite.test_05_tampering_classification

# Add verbose logging
python3 -m unittest tests.test_tamper_resistance.TamperResistanceTestSuite.test_05_tampering_classification -v
```

### Import Errors

```bash
# Verify path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/krita-plugin/chm_verifier"

# Try running tests again
python3 tests/test_tamper_resistance.py
```

## Performance Benchmarks

| Metric | Expected |
|--------|----------|
| Total time | 2-5 seconds |
| Per test | 0.1-0.3 seconds |
| Tests run | 20 |
| Memory usage | < 50 MB |

## CI/CD Integration

**GitHub Actions**: See `.github/workflows/tamper-resistance-tests.yml`

**Exit Codes**:
- `0` = All tests passed ✅
- `1` = Some tests failed ❌

**Example CI Usage**:
```yaml
- name: Run Tamper Tests
  run: ./tests/ci-tamper-tests.sh
  
- name: Check Coverage
  run: ./tests/ci-tamper-tests.sh --coverage
```

## Key Files

```
tests/
├── test_tamper_resistance.py    # Main test suite (20 tests)
├── run-tamper-tests.sh          # Simple test runner
├── ci-tamper-tests.sh           # CI/CD runner with coverage
├── README-TAMPER-TESTS.md       # Full documentation
└── QUICK-REFERENCE.md           # This file
```

## Support

- **Full Documentation**: `tests/README-TAMPER-TESTS.md`
- **Manual Testing Guide**: `docs/tamper-resistance-testing-guide.md`
- **Issues**: GitHub Issues

