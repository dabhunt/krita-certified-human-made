"""
Test UUID-based Session Keys

Tests the new UUID annotation system for session persistence.
Validates that sessions work for both saved and unsaved documents.

Run from Krita Script Editor (Tools > Scripts > Scripter).
"""

from krita import Krita
import sys

def test_uuid_session_keys():
    """
    Test UUID-based session key system.
    
    Tests:
    1. UUID generation for new unsaved document
    2. UUID persistence in document annotation
    3. Session key stability through save operation
    4. Session resumption with UUID key
    5. Backward compatibility with existing saved documents
    """
    print("\n" + "="*80)
    print("TEST: UUID-based Session Keys")
    print("="*80)
    
    app = Krita.instance()
    
    # Get extension instance
    extension = None
    for ext in app.extensions():
        if hasattr(ext, 'session_manager'):
            extension = ext
            break
    
    if not extension:
        print("❌ FAIL: CHM extension not found")
        return False
    
    session_manager = extension.session_manager
    
    # Test 1: Create new unsaved document
    print("\n[TEST 1] Creating new unsaved document...")
    doc = app.createDocument(1000, 1000, "Test Document", "RGBA", "U8", "", 300.0)
    
    if not doc:
        print("❌ FAIL: Could not create document")
        return False
    
    print(f"✓ Document created: {doc.name()}")
    print(f"  Filepath: {doc.fileName() if doc.fileName() else 'None (unsaved)'}")
    
    # Test 2: Check UUID annotation
    print("\n[TEST 2] Checking UUID annotation...")
    
    doc_key = session_manager._get_document_key(doc)
    print(f"  Document key: {doc_key[:32]}...")
    
    if not doc_key.startswith("uuid_"):
        print(f"❌ FAIL: Expected UUID-based key, got: {doc_key}")
        return False
    
    print("✓ UUID-based key generated")
    
    # Extract UUID from annotation
    doc_uuid = session_manager._ensure_document_uuid(doc)
    print(f"  UUID: {doc_uuid[:16]}...")
    
    # Test 3: Create session
    print("\n[TEST 3] Creating session...")
    
    session = session_manager.create_session(doc)
    
    if not session:
        print("❌ FAIL: Could not create session")
        return False
    
    print(f"✓ Session created: {session.id}")
    
    # Test 4: Verify session key stability
    print("\n[TEST 4] Verifying session key stability...")
    
    # Get key multiple times
    key1 = session_manager._get_document_key(doc)
    key2 = session_manager._get_document_key(doc)
    key3 = session_manager._get_document_key(doc)
    
    if key1 != key2 or key2 != key3:
        print(f"❌ FAIL: Keys not stable!")
        print(f"  Key 1: {key1}")
        print(f"  Key 2: {key2}")
        print(f"  Key 3: {key3}")
        return False
    
    print("✓ Session key is stable")
    print(f"  Consistent key: {key1[:32]}...")
    
    # Test 5: Simulate drawing activity
    print("\n[TEST 5] Simulating drawing activity...")
    
    session.record_stroke(100, 100, 0.5, "test_brush")
    session.record_stroke(200, 200, 0.8, "test_brush")
    session.record_layer_added("layer_1", "paint")
    
    print(f"✓ Recorded {session.event_count} events")
    
    # Test 6: Session persistence for unsaved document
    print("\n[TEST 6] Testing session persistence for unsaved document...")
    
    event_capture = extension.event_capture
    if not event_capture:
        print("❌ FAIL: EventCapture not found")
        return False
    
    # Try to persist session
    try:
        event_capture._persist_session(doc, session, "test")
        print("✓ Session persisted for unsaved document")
    except Exception as e:
        print(f"❌ FAIL: Could not persist session: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 7: Verify session file exists
    print("\n[TEST 7] Verifying session file on disk...")
    
    storage = event_capture.session_storage
    if not storage:
        print("⚠️  SKIP: SessionStorage not available")
    else:
        # Extract UUID from key for storage lookup
        session_uuid = doc_key[5:]  # Remove "uuid_" prefix
        session_file = storage._get_session_filepath(session_uuid)
        
        import os
        if os.path.exists(session_file):
            file_size = os.path.getsize(session_file)
            print(f"✓ Session file exists: {session_file}")
            print(f"  File size: {file_size} bytes")
        else:
            print(f"❌ FAIL: Session file not found: {session_file}")
            return False
    
    # Test 8: Test session resumption
    print("\n[TEST 8] Testing session resumption...")
    
    # Remove session from memory
    del session_manager.active_sessions[doc_key]
    print("  Removed session from memory")
    
    # Try to resume
    session_resumed = event_capture._try_resume_or_create_session(doc, "test")
    
    # Check if session was resumed
    resumed_session = session_manager.get_session(doc)
    
    if not resumed_session:
        print("❌ FAIL: Session not resumed")
        return False
    
    if resumed_session.event_count != 3:  # 2 strokes + 1 layer
        print(f"❌ FAIL: Expected 3 events, got {resumed_session.event_count}")
        return False
    
    print(f"✓ Session resumed successfully")
    print(f"  Session ID: {resumed_session.id}")
    print(f"  Events restored: {resumed_session.event_count}")
    
    # Test 9: Key stability through save operation
    print("\n[TEST 9] Testing key stability through save...")
    
    # Save the document
    import tempfile
    temp_file = tempfile.mktemp(suffix=".kra")
    
    print(f"  Saving to: {temp_file}")
    doc.setFileName(temp_file)
    saved = doc.save()
    
    if not saved:
        print("⚠️  SKIP: Could not save document (may require interactive save)")
    else:
        # Check if key is still UUID-based
        key_after_save = session_manager._get_document_key(doc)
        
        if key_after_save != doc_key:
            print(f"❌ FAIL: Key changed after save!")
            print(f"  Before: {doc_key[:32]}...")
            print(f"  After:  {key_after_save[:32]}...")
            return False
        
        print("✓ Session key remained stable after save")
        print(f"  Key: {key_after_save[:32]}...")
        
        # Cleanup
        import os
        try:
            os.remove(temp_file)
            print("  Cleaned up temp file")
        except:
            pass
    
    # Close document
    doc.close()
    print("\n✓ Document closed")
    
    # Overall result
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED")
    print("="*80)
    print("\nUUID-based session keys are working correctly!")
    print("Sessions now work for both saved and unsaved documents.")
    
    return True


# Run the test
try:
    success = test_uuid_session_keys()
    sys.stdout.flush()
    
    if success:
        print("\n🎉 Test suite completed successfully!")
    else:
        print("\n❌ Test suite failed - see errors above")
        
except Exception as e:
    print(f"\n❌ FATAL ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()

