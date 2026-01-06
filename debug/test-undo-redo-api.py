#!/usr/bin/env python3
"""
Test Krita Undo/Redo API Access

This script tests different approaches to detect undo/redo operations:
1. QUndoStack API (if accessible)
2. Document API methods
3. Action system
4. Event filter approach

Run this in Krita Scripter to see which APIs are available.
"""

import sys

def test_undo_api():
    """Test if we can access Krita's undo/redo system"""
    
    print("=" * 60)
    print("KRITA UNDO/REDO API TEST")
    print("=" * 60)
    
    try:
        from krita import Krita
        
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            print("❌ No active document - please open or create a document first!")
            return
        
        print(f"\n✅ Active document: {doc.name()}")
        print(f"   Document type: {type(doc)}")
        
        # Test 1: Check for undoStack() method
        print("\n" + "=" * 60)
        print("TEST 1: QUndoStack API")
        print("=" * 60)
        
        if hasattr(doc, 'undoStack'):
            print("✅ document.undoStack() EXISTS!")
            try:
                stack = doc.undoStack()
                print(f"   Stack object: {stack}")
                print(f"   Stack type: {type(stack)}")
                
                # Try to get stack properties
                if hasattr(stack, 'count'):
                    print(f"   Stack count: {stack.count()}")
                if hasattr(stack, 'canUndo'):
                    print(f"   Can undo: {stack.canUndo()}")
                if hasattr(stack, 'canRedo'):
                    print(f"   Can redo: {stack.canRedo()}")
                if hasattr(stack, 'undoText'):
                    print(f"   Undo text: {stack.undoText()}")
                
                # Try connecting signals
                print("\n   Testing signal connections:")
                if hasattr(stack, 'indexChanged'):
                    print("   ✅ indexChanged signal exists")
                    stack.indexChanged.connect(lambda idx: print(f"      → indexChanged fired: {idx}"))
                    print("      Signal connected! (try undo/redo now)")
                else:
                    print("   ❌ indexChanged signal NOT found")
                
                if hasattr(stack, 'canUndoChanged'):
                    print("   ✅ canUndoChanged signal exists")
                else:
                    print("   ❌ canUndoChanged signal NOT found")
                    
            except Exception as e:
                print(f"   ⚠️  Error accessing undoStack: {e}")
        else:
            print("❌ document.undoStack() NOT FOUND")
            print("   Will need to use event filter approach")
        
        # Test 2: Check for other undo-related methods
        print("\n" + "=" * 60)
        print("TEST 2: Document Undo Methods")
        print("=" * 60)
        
        undo_methods = ['undo', 'redo', 'waitForDone']
        for method in undo_methods:
            if hasattr(doc, method):
                print(f"✅ document.{method}() EXISTS")
            else:
                print(f"❌ document.{method}() NOT FOUND")
        
        # Test 3: Check Krita actions
        print("\n" + "=" * 60)
        print("TEST 3: Krita Action System")
        print("=" * 60)
        
        if hasattr(app, 'action'):
            undo_action = app.action('edit_undo')
            redo_action = app.action('edit_redo')
            
            if undo_action:
                print(f"✅ edit_undo action found: {undo_action}")
                print(f"   Type: {type(undo_action)}")
                if hasattr(undo_action, 'triggered'):
                    print("   ✅ triggered signal exists")
                    undo_action.triggered.connect(lambda: print("      → UNDO TRIGGERED!"))
                    print("      Signal connected! (try undo now)")
            else:
                print("❌ edit_undo action NOT FOUND")
            
            if redo_action:
                print(f"✅ edit_redo action found: {redo_action}")
                if hasattr(redo_action, 'triggered'):
                    print("   ✅ triggered signal exists")
                    redo_action.triggered.connect(lambda: print("      → REDO TRIGGERED!"))
                    print("      Signal connected! (try redo now)")
            else:
                print("❌ edit_redo action NOT FOUND")
        else:
            print("❌ app.action() NOT FOUND")
        
        # Test 4: List all document attributes
        print("\n" + "=" * 60)
        print("TEST 4: All Document Attributes")
        print("=" * 60)
        
        print("\nSearching for 'undo', 'redo', 'history', 'stack':")
        all_attrs = dir(doc)
        undo_related = [attr for attr in all_attrs if any(keyword in attr.lower() for keyword in ['undo', 'redo', 'history', 'stack'])]
        
        if undo_related:
            for attr in undo_related:
                print(f"   - {attr}")
        else:
            print("   (none found)")
        
        print("\n" + "=" * 60)
        print("RECOMMENDATION")
        print("=" * 60)
        
        if hasattr(doc, 'undoStack'):
            print("✅ Use QUndoStack signals (Option 2) - BEST APPROACH")
            print("   Connect to indexChanged signal in connect_document_signals()")
        elif hasattr(app, 'action') and app.action('edit_undo'):
            print("✅ Use Krita action system (Option 4) - GOOD APPROACH")
            print("   Connect to action.triggered signals")
        else:
            print("⚠️  Use Qt Event Filter (Option 1) - FALLBACK APPROACH")
            print("   Intercept Ctrl+Z / Cmd+Z keyboard events")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        print(f"\nTraceback:\n{traceback.format_exc()}")

if __name__ == "__main__":
    test_undo_api()

