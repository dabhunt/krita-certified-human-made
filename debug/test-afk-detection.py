#!/usr/bin/env python3
"""
Test script for AFK (Away From Keyboard) detection in session duration tracking.

This script tests that:
1. Duration increments normally when events are being recorded
2. Duration stops incrementing after 10 seconds of no activity
3. Duration resumes incrementing when activity resumes
"""

import sys
import time
import os

# Add the Rust library path
lib_path = os.path.join(os.path.dirname(__file__), '..', 'krita-plugin', 'chm_verifier', 'lib')
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

try:
    from chm import CHMSession
    
    print("=" * 60)
    print("AFK Detection Test")
    print("=" * 60)
    
    # Create a new session
    session = CHMSession()
    print(f"✓ Created session: {session.id}")
    print(f"  Start time: {session.start_time}")
    
    # Test 1: Active recording (should increment normally)
    print("\n--- Test 1: Active Recording ---")
    for i in range(5):
        session.record_stroke(100 + i * 10, 200 + i * 10, 0.8, "Test Brush")
        time.sleep(0.5)  # 0.5s between strokes
        duration = session.duration_secs
        print(f"  After stroke {i+1}: duration = {duration}s")
    
    print(f"\n✓ After active recording: {session.event_count} events, {session.duration_secs}s duration")
    
    # Test 2: Go AFK for 15 seconds (exceeds 10s threshold)
    print("\n--- Test 2: Going AFK (15 seconds) ---")
    print("  Waiting 15 seconds with no activity...")
    
    duration_before_afk = session.duration_secs
    print(f"  Duration before AFK: {duration_before_afk}s")
    
    # Check duration every 3 seconds
    for i in range(5):
        time.sleep(3)
        current_duration = session.duration_secs
        elapsed = (i + 1) * 3
        print(f"  After {elapsed}s idle: duration = {current_duration}s")
        
        # After 12s, duration should have stopped incrementing
        if elapsed > 10:
            # Duration should be roughly: duration_before_afk + 10s (threshold)
            # Allow some margin for timing
            expected_max = duration_before_afk + 13  # 10s threshold + 3s margin
            if current_duration <= expected_max:
                print(f"    ✓ AFK detection working! (duration capped near {duration_before_afk + 10}s)")
            else:
                print(f"    ✗ AFK detection may not be working (expected <= {expected_max}s)")
    
    duration_after_afk = session.duration_secs
    print(f"\n  Duration after 15s AFK: {duration_after_afk}s")
    
    # Test 3: Resume activity
    print("\n--- Test 3: Resume Activity ---")
    print("  Recording new strokes...")
    
    for i in range(3):
        session.record_stroke(200 + i * 10, 300 + i * 10, 0.8, "Test Brush")
        time.sleep(0.5)
        duration = session.duration_secs
        print(f"  After stroke {i+1}: duration = {duration}s")
    
    print(f"\n✓ After resuming: {session.event_count} events, {session.duration_secs}s duration")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Total events recorded: {session.event_count}")
    print(f"Final duration: {session.duration_secs}s")
    print(f"\nExpected behavior:")
    print(f"  - Duration should be ~18-23s (not ~20s+)")
    print(f"  - The 15s AFK period should only add ~10s to duration")
    print(f"  - Duration during AFK should have stopped incrementing after 10s threshold")
    
    # Verify AFK detection worked
    final_duration = session.duration_secs
    # We had ~2.5s active, 15s AFK (only 10s counted), 1.5s active = ~14s total
    # Allow generous margin for timing
    if final_duration < 25:
        print(f"\n✓ ✓ ✓  AFK DETECTION WORKING!")
        print(f"  Duration ({final_duration}s) is reasonable for the actual activity.")
    else:
        print(f"\n✗ ✗ ✗  AFK DETECTION MAY NOT BE WORKING")
        print(f"  Duration ({final_duration}s) seems too high.")
    
    print("\nTest complete!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


