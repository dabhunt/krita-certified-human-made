#!/usr/bin/env python3
"""
Test script to verify if Krita's Python API exposes reference images.

Run this from Krita's Script Docker:
1. Open Krita
2. Settings → Dockers → Scripting
3. Paste this script
4. Click Run

Or save as plugin and run via Python Plugin Manager.
"""

from krita import Krita

def test_reference_images_api():
    """Test all possible ways to access reference images via Krita Python API"""
    
    print("=" * 60)
    print("TESTING KRITA REFERENCE IMAGES API")
    print("=" * 60)
    
    app = Krita.instance()
    doc = app.activeDocument()
    
    if not doc:
        print("❌ No active document. Please create/open a document first.")
        return
    
    print(f"\n✅ Active document: {doc.name()}")
    print(f"   Krita version: {app.version()}")
    
    # Test 1: Check if Document has referenceImages() method
    print("\n" + "-" * 60)
    print("TEST 1: Document.referenceImages()")
    print("-" * 60)
    
    if hasattr(doc, 'referenceImages'):
        print("✅ Document.referenceImages() EXISTS!")
        try:
            refs = doc.referenceImages()
            print(f"   Type: {type(refs)}")
            print(f"   Count: {len(refs) if hasattr(refs, '__len__') else 'N/A'}")
            
            if refs and hasattr(refs, '__iter__'):
                print("\n   Reference objects:")
                for i, ref in enumerate(refs):
                    print(f"   [{i}] Type: {type(ref)}")
                    print(f"       Dir: {[m for m in dir(ref) if not m.startswith('_')]}")
        except Exception as e:
            print(f"❌ Error calling referenceImages(): {e}")
    else:
        print("❌ Document.referenceImages() does NOT exist")
    
    # Test 2: Check for setReferenceImages() method
    print("\n" + "-" * 60)
    print("TEST 2: Document.setReferenceImages()")
    print("-" * 60)
    
    if hasattr(doc, 'setReferenceImages'):
        print("✅ Document.setReferenceImages() EXISTS!")
    else:
        print("❌ Document.setReferenceImages() does NOT exist")
    
    # Test 3: Check all Document methods containing 'reference'
    print("\n" + "-" * 60)
    print("TEST 3: All Document methods with 'reference'")
    print("-" * 60)
    
    doc_methods = [m for m in dir(doc) if 'reference' in m.lower() and not m.startswith('_')]
    if doc_methods:
        print("✅ Found reference-related methods:")
        for method in doc_methods:
            print(f"   - {method}")
    else:
        print("❌ No reference-related methods found")
    
    # Test 4: Check Window for reference-related methods
    print("\n" + "-" * 60)
    print("TEST 4: Window reference methods")
    print("-" * 60)
    
    window = app.activeWindow()
    if window:
        window_methods = [m for m in dir(window) if 'reference' in m.lower() and not m.startswith('_')]
        if window_methods:
            print("✅ Found reference-related methods on Window:")
            for method in window_methods:
                print(f"   - {method}")
        else:
            print("❌ No reference-related methods on Window")
    else:
        print("❌ No active window")
    
    # Test 5: Check View for reference-related methods
    print("\n" + "-" * 60)
    print("TEST 5: View reference methods")
    print("-" * 60)
    
    if window:
        view = window.activeView()
        if view:
            view_methods = [m for m in dir(view) if 'reference' in m.lower() and not m.startswith('_')]
            if view_methods:
                print("✅ Found reference-related methods on View:")
                for method in view_methods:
                    print(f"   - {method}")
            else:
                print("❌ No reference-related methods on View")
        else:
            print("❌ No active view")
    
    # Test 6: List ALL Document methods (comprehensive)
    print("\n" + "-" * 60)
    print("TEST 6: ALL Document methods (for manual review)")
    print("-" * 60)
    
    all_methods = [m for m in dir(doc) if not m.startswith('_')]
    print(f"Total public methods: {len(all_methods)}")
    print("\nMethods that might be related to references:")
    
    # Look for methods that might relate to references
    possible_reference_methods = [
        m for m in all_methods 
        if any(keyword in m.lower() for keyword in [
            'reference', 'ref', 'image', 'import', 'resource', 
            'attach', 'embed', 'external', 'link'
        ])
    ]
    
    if possible_reference_methods:
        for method in possible_reference_methods:
            print(f"   - {method}")
    else:
        print("   (None found)")
    
    # Test 7: Check for .kra-specific methods
    print("\n" + "-" * 60)
    print("TEST 7: .kra metadata methods")
    print("-" * 60)
    
    kra_methods = [m for m in all_methods if 'annotation' in m.lower() or 'metadata' in m.lower()]
    if kra_methods:
        print("✅ Found metadata-related methods:")
        for method in kra_methods:
            print(f"   - {method}")
            # Try to call annotation methods
            if 'annotation' in method.lower() and 'remove' not in method.lower():
                try:
                    result = getattr(doc, method)()
                    print(f"      Result: {result}")
                except Exception as e:
                    print(f"      Error: {e}")
    else:
        print("❌ No metadata methods found")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print("\n📋 ACTION ITEMS:")
    print("1. If Document.referenceImages() exists → Implement Option 1 (API-based)")
    print("2. If no API found → Implement Option 3 (.kra inspection) + Option 6 (user declaration)")
    print("3. Document findings in /docs/krita-reference-image-api.md")
    
    print("\n💡 TESTING INSTRUCTIONS:")
    print("To thoroughly test:")
    print("1. Add a reference image using the Reference Images Tool (pushpin icon)")
    print("2. Run this script again")
    print("3. Check if referenceImages() count increased")
    print("4. Try accessing reference image data (if API exists)")
    
    print("\n" + "=" * 60)

# Run the test
if __name__ == "__main__":
    test_reference_images_api()


