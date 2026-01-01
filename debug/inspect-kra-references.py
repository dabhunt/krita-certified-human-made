#!/usr/bin/env python3
"""
Inspect .kra file structure to find where reference images are stored.

Usage:
    python3 debug/inspect-kra-references.py path/to/file.kra

Requirements:
    - Python 3.6+
    - No external dependencies (uses stdlib only)

This script will:
1. Extract .kra file (ZIP archive)
2. List all files in archive
3. Parse maindoc.xml and pretty-print structure
4. Search for reference-image related nodes
5. Show where reference image files are stored
"""

import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import re

def pretty_print_xml(element, indent=0):
    """Recursively print XML tree structure"""
    tag = element.tag
    attrs = " ".join(f'{k}="{v}"' for k, v in element.attrib.items())
    text = (element.text or "").strip()
    
    prefix = "  " * indent
    
    if attrs:
        print(f"{prefix}<{tag} {attrs}>", end="")
    else:
        print(f"{prefix}<{tag}>", end="")
    
    if text:
        print(f" {text[:50]}..." if len(text) > 50 else f" {text}", end="")
    
    if len(element) > 0:
        print()  # New line for children
        for child in element:
            pretty_print_xml(child, indent + 1)
        print(f"{prefix}</{tag}>")
    else:
        print(f"</{tag}>")

def search_xml_for_references(element, path="", results=None):
    """Recursively search XML for reference-image related nodes"""
    if results is None:
        results = []
    
    current_path = f"{path}/{element.tag}"
    
    # Check if this node relates to references
    tag_lower = element.tag.lower()
    if 'reference' in tag_lower or 'ref' in tag_lower:
        results.append({
            'path': current_path,
            'tag': element.tag,
            'attrs': dict(element.attrib),
            'text': (element.text or "").strip()
        })
    
    # Check attributes for reference-related values
    for attr_name, attr_value in element.attrib.items():
        if 'reference' in attr_name.lower() or 'reference' in attr_value.lower():
            results.append({
                'path': current_path,
                'tag': element.tag,
                'attr': f"{attr_name}={attr_value}",
                'context': 'attribute'
            })
    
    # Recurse into children
    for child in element:
        search_xml_for_references(child, current_path, results)
    
    return results

def inspect_kra_file(kra_path):
    """Main inspection function"""
    print("=" * 70)
    print(f"INSPECTING: {kra_path}")
    print("=" * 70)
    
    if not Path(kra_path).exists():
        print(f"❌ File not found: {kra_path}")
        return
    
    if not kra_path.endswith('.kra'):
        print(f"⚠️  Warning: File doesn't have .kra extension")
    
    try:
        with zipfile.ZipFile(kra_path, 'r') as kra:
            # Step 1: List all files
            print("\n" + "-" * 70)
            print("STEP 1: Files in .kra archive")
            print("-" * 70)
            
            file_list = kra.namelist()
            print(f"Total files: {len(file_list)}\n")
            
            # Categorize files
            xml_files = [f for f in file_list if f.endswith('.xml')]
            image_files = [f for f in file_list if re.search(r'\.(png|jpg|jpeg|gif|svg|bmp)$', f, re.I)]
            other_files = [f for f in file_list if f not in xml_files and f not in image_files]
            
            print("📄 XML Files:")
            for f in xml_files:
                size = kra.getinfo(f).file_size
                print(f"   - {f} ({size} bytes)")
            
            print("\n🖼️  Image Files:")
            for f in image_files:
                size = kra.getinfo(f).file_size
                print(f"   - {f} ({size} bytes)")
            
            if other_files:
                print("\n📦 Other Files:")
                for f in other_files[:10]:  # Limit to 10
                    size = kra.getinfo(f).file_size
                    print(f"   - {f} ({size} bytes)")
                if len(other_files) > 10:
                    print(f"   ... and {len(other_files) - 10} more")
            
            # Step 2: Parse maindoc.xml
            print("\n" + "-" * 70)
            print("STEP 2: Parsing maindoc.xml")
            print("-" * 70)
            
            if 'maindoc.xml' not in file_list:
                print("❌ maindoc.xml not found in archive!")
                return
            
            xml_data = kra.read('maindoc.xml')
            tree = ET.fromstring(xml_data)
            
            print(f"Root element: <{tree.tag}>")
            print(f"Root attributes: {dict(tree.attrib)}")
            
            # Step 3: Search for reference-related nodes
            print("\n" + "-" * 70)
            print("STEP 3: Searching for reference-related nodes")
            print("-" * 70)
            
            ref_results = search_xml_for_references(tree)
            
            if ref_results:
                print(f"✅ Found {len(ref_results)} reference-related nodes:\n")
                for i, result in enumerate(ref_results, 1):
                    print(f"[{i}] {result['path']}")
                    if 'attrs' in result:
                        for k, v in result['attrs'].items():
                            print(f"     {k} = {v}")
                    if 'text' in result and result['text']:
                        print(f"     Text: {result['text'][:100]}")
                    if 'attr' in result:
                        print(f"     Attribute: {result['attr']}")
                    print()
            else:
                print("❌ No reference-related nodes found in XML")
                print("\n💡 This could mean:")
                print("   1. No reference images in this document")
                print("   2. Reference images stored outside maindoc.xml")
                print("   3. Different naming convention used")
            
            # Step 4: Show XML structure (first 2 levels)
            print("\n" + "-" * 70)
            print("STEP 4: XML Structure (first 2 levels)")
            print("-" * 70)
            
            print(f"<{tree.tag}>")
            for child in tree:
                print(f"  <{child.tag}> ({len(child)} children)")
                for subchild in child:
                    attrs = " ".join(f'{k}="{v}"' for k, v in list(subchild.attrib.items())[:2])
                    if attrs:
                        print(f"    <{subchild.tag} {attrs}... > ({len(subchild)} children)")
                    else:
                        print(f"    <{subchild.tag}> ({len(subchild)} children)")
            
            # Step 5: Check specific paths
            print("\n" + "-" * 70)
            print("STEP 5: Checking common reference image paths")
            print("-" * 70)
            
            common_paths = [
                './/REFERENCEIMAGES',
                './/referenceimages',
                './/ReferenceImages',
                './/reference-images',
                './/REFERENCEIMAGE',
                './/referenceimage',
                './/ASSISTANT',
                './/assistant',
                './/IMAGE[@type="reference"]',
                './/image[@type="reference"]',
            ]
            
            for xpath in common_paths:
                results = tree.findall(xpath)
                if results:
                    print(f"✅ Found {len(results)} node(s) at: {xpath}")
                    for node in results:
                        print(f"   Tag: {node.tag}")
                        print(f"   Attrs: {dict(node.attrib)}")
                else:
                    print(f"❌ Not found: {xpath}")
            
            # Step 6: Full XML dump (for manual inspection)
            print("\n" + "-" * 70)
            print("STEP 6: Full XML tree (verbose)")
            print("-" * 70)
            print("(Limited to first 100 lines, save to file for full output)\n")
            
            xml_str = ET.tostring(tree, encoding='unicode', method='xml')
            lines = xml_str.split('\n')
            for i, line in enumerate(lines[:100], 1):
                print(f"{i:4}: {line}")
            
            if len(lines) > 100:
                print(f"\n... and {len(lines) - 100} more lines")
                print("\n💾 To see full XML, save to file:")
                print(f"   unzip -p '{kra_path}' maindoc.xml > maindoc_extracted.xml")
    
    except zipfile.BadZipFile:
        print(f"❌ Error: Not a valid ZIP/KRA file: {kra_path}")
    except ET.ParseError as e:
        print(f"❌ Error parsing XML: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("INSPECTION COMPLETE")
    print("=" * 70)
    print("\n📝 NEXT STEPS:")
    print("1. Review reference-related nodes found (if any)")
    print("2. Check image files for reference image data")
    print("3. Document XML path in krita-reference-image-api.md")
    print("4. Implement .kra parser in event_capture.py")
    print("=" * 70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 inspect-kra-references.py <path-to-kra-file>")
        print()
        print("Example:")
        print("  python3 debug/inspect-kra-references.py ~/Documents/reference-test.kra")
        sys.exit(1)
    
    kra_path = sys.argv[1]
    inspect_kra_file(kra_path)


