#!/usr/bin/env python3
"""Test script to verify lazrs and laspy installation"""

import sys
import os

print("=" * 60)
print("Testing lazrs and laspy installation")
print("=" * 60)

# Test 1: Import lazrs
print("\n1. Testing lazrs import...")
try:
    import lazrs
    print("   [OK] lazrs imported successfully")
except ImportError as e:
    print(f"   [ERROR] Failed to import lazrs: {e}")
    sys.exit(1)

# Test 2: Import laspy
print("\n2. Testing laspy import...")
try:
    import laspy
    print("   [OK] laspy imported successfully")
except ImportError as e:
    print(f"   [ERROR] Failed to import laspy: {e}")
    sys.exit(1)

# Test 3: Check LAZ backends
print("\n3. Checking available LAZ backends...")
try:
    from laspy.compression import LazBackend
    available = LazBackend.detect_available()
    if available:
        print(f"   [OK] Available backends: {[str(b) for b in available]}")
    else:
        print("   [ERROR] No LAZ backends available!")
        print("   This means lazrs is not properly detected by laspy")
        sys.exit(1)
except Exception as e:
    print(f"   [ERROR] Error checking backends: {e}")
    sys.exit(1)

# Test 4: Check if we can read a file (if uploads folder has files)
print("\n4. Checking for test files...")
uploads_dir = 'uploads'
if os.path.exists(uploads_dir):
    files = [f for f in os.listdir(uploads_dir) if f.endswith(('.las', '.laz'))]
    if files:
        test_file = os.path.join(uploads_dir, files[0])
        print(f"   Found test file: {test_file}")
        print(f"   Attempting to read...")
        try:
            las = laspy.read(test_file)
            print(f"   [OK] Successfully read {len(las.points)} points")
        except Exception as e:
            print(f"   [ERROR] Failed to read file: {e}")
            print(f"   Error type: {type(e).__name__}")
    else:
        print("   No test files found in uploads directory")
else:
    print("   Uploads directory does not exist")

print("\n" + "=" * 60)
print("All basic tests passed!")
print("=" * 60)

