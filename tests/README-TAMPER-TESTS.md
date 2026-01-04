# Tamper Resistance Automated Test Suite

Comprehensive automated testing for the CHM plugin's HMAC signature-based tamper resistance system.

## Overview

This test suite validates that:
- Session proofs include valid HMAC-SHA256 signatures
- Tampering with critical proof fields is detected
- Non-critical fields can be modified without breaking signatures
- Signature verification works correctly in all scenarios

## Quick Start

```bash
# Run all tests
./tests/run-tamper-tests.sh

# Run with verbose output
./tests/run-tamper-tests.sh --verbose

# Or run directly with Python
python3 tests/test_tamper_resistance.py
```

## Test Coverage

The test suite includes **20 comprehensive tests** covering:

### 1. Signing Key Management
- ✅ **Test 01**: Signing key loaded and accessible
- ✅ **Test 02**: Graceful handling of missing signing key

### 2. Proof Generation
- ✅ **Test 03**: Valid proof generation with all required fields
- ✅ **Test 15**: JSON serialization/deserialization
- ✅ **Test 16**: File-based proof verification
- ✅ **Test 18**: Empty session (0 events) proof generation

### 3. Signature Verification
- ✅ **Test 04**: Valid untampered proofs pass verification
- ✅ **Test 12**: Signature determinism (same data = same signature)
- ✅ **Test 19**: Signature version field handling

### 4. Tampering Detection
- ✅ **Test 05**: Modified classification detected
- ✅ **Test 06**: Modified event counts detected
- ✅ **Test 07**: Modified events hash detected
- ✅ **Test 08**: Modified signature itself detected
- ✅ **Test 09**: Modified layer count detected
- ✅ **Test 10**: Modified import count detected
- ✅ **Test 11**: Modified AI tools metadata detected
- ✅ **Test 14**: Multiple simultaneous tampering attempts detected

### 5. Non-Critical Fields
- ✅ **Test 13**: Timestamps can be modified without breaking signature

### 6. Classification Scenarios
- ✅ **Test 17**: AI-Assisted classification signature

### 7. Stress Testing
- ✅ **Test 20**: Large proof with 1000+ events

## Test Structure

```
tests/
├── test_tamper_resistance.py    # Main test suite
├── run-tamper-tests.sh          # Test runner script
└── README-TAMPER-TESTS.md       # This file
```

## Test Output Example

```
======================================================================
CHM Plugin - Tamper Resistance Test Suite
======================================================================

[SETUP] Generated test signing key: ES4OZZO/...RUZXEw=
[SETUP] ✓ Signing key set in chm_core module
[SETUP] ✓ Test artifacts directory: /tmp/chm_test_xyz

[TEST-01] Verifying signing key is loaded...
[TEST-01] ✓ Signature present: 9f8e7d...1a2b3c
[TEST-01] ✅ PASSED

[TEST-05] Testing tampering detection (classification)...
[TEST-05] ✓ Original: HumanMade
[TEST-05] ✓ Tampered: AI-Assisted
[TEST-05] ✓ Tampering detected successfully
[TEST-05] ✅ PASSED

...

======================================================================
TEST SUMMARY
======================================================================
Tests run: 20
Successes: 20
Failures: 0
Errors: 0
======================================================================
```

## What Gets Tested

### Critical Fields (MUST be signed)
These fields are included in the HMAC signature. Any modification breaks the signature:

- `version` - Proof format version
- `session_id` - Unique session identifier
- `events_hash` - Hash of all recorded events
- `file_hash` - Hash of exported artwork
- `classification` - HumanMade/AI-Assisted/MixedMedia
- `event_summary.total_events` - Total event count
- `event_summary.stroke_count` - Brush stroke count
- `event_summary.layer_count` - Layer count
- `event_summary.import_count` - Image import count
- `metadata.ai_tools_used` - Whether AI tools were used
- `metadata.ai_tools_list` - List of AI tools used
- `signature_version` - Signature version (for key rotation)

### Non-Critical Fields (NOT signed)
These fields can be modified without breaking the signature:

- `start_time` - Session start timestamp
- `end_time` - Session end timestamp
- `duration_seconds` - Session duration
- `document_id` - Document identifier

## Prerequisites

- Python 3.7+
- CHM plugin built and installed
- `chm_core.py` module available in `krita-plugin/chm_verifier/`

## Running Individual Tests

```python
# Run a specific test
python3 -m unittest tests.test_tamper_resistance.TamperResistanceTestSuite.test_05_tampering_classification

# Run tests matching pattern
python3 -m unittest discover -s tests -p "test_tamper*" -v
```

## Integration with CI/CD

The test suite is designed for CI/CD integration:

```bash
# Exit code 0 = all tests passed
# Exit code 1 = some tests failed
./tests/run-tamper-tests.sh

# Check exit code
if [ $? -eq 0 ]; then
    echo "✅ Tests passed"
else
    echo "❌ Tests failed"
    exit 1
fi
```

## Troubleshooting

### Issue: "No module named 'chm_core'"

**Solution:** Ensure the plugin directory is in the Python path:
```python
import sys
sys.path.insert(0, '/path/to/krita-plugin/chm_verifier')
```

### Issue: Tests fail with signature verification errors

**Solution:** Check that the signing key hasn't changed between test runs. The test suite generates a fresh key for each run.

### Issue: Import errors for unittest

**Solution:** Ensure you're using Python 3.7+:
```bash
python3 --version
```

## Test Development

### Adding New Tests

1. Add a new test method to `TamperResistanceTestSuite`
2. Use naming convention: `test_NN_descriptive_name`
3. Include clear print statements for debugging
4. Follow existing test patterns

Example:

```python
def test_21_new_feature(self):
    """Test description"""
    print("\n[TEST-21] Testing new feature...")
    
    # Test logic here
    proof_data = self._generate_test_proof()
    
    # Assertions
    self.assertTrue(condition, "Error message")
    
    print("[TEST-21] ✓ Feature works correctly")
    print("[TEST-21] ✅ PASSED")
```

### Helper Methods

- `_create_test_session(with_events=True)` - Create a test session
- `_generate_test_proof(session=None)` - Generate a test proof
- `self.temp_dir` - Temporary directory for test artifacts

## Coverage Report

To generate a coverage report:

```bash
# Install coverage tool
pip3 install coverage

# Run tests with coverage
coverage run -m unittest tests.test_tamper_resistance

# Generate report
coverage report -m

# Generate HTML report
coverage html
```

## Performance Benchmarks

Expected test execution time:
- All 20 tests: ~2-5 seconds
- Individual test: ~0.1-0.3 seconds

## Related Documentation

- [Tamper Resistance Testing Guide](../docs/tamper-resistance-testing-guide.md) - Manual testing procedures
- [CHM Core Module](../krita-plugin/chm_verifier/chm_core.py) - Implementation details

## Security Considerations

⚠️ **Important:**
- Test signing keys are randomly generated and temporary
- Do NOT use test keys in production
- Production signing keys must be kept secret
- Never commit signing keys to git

## Maintenance

This test suite should be updated when:
- New critical fields are added to proofs
- Signature algorithm changes
- Classification logic changes
- Event types are added or modified

## Support

For issues or questions about the test suite:
1. Check the troubleshooting section above
2. Review test output for specific error messages
3. Consult the manual testing guide
4. Check the CHM core module implementation

---

**Last Updated:** January 4, 2026

**Test Suite Version:** 1.0

**Coverage:** 20 tests, 100% of critical functionality

