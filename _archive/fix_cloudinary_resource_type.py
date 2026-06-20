"""
Imhotep - Fix Cloudinary PDF Resource Type
--------------------------------------------
Changes resource_type from 'raw' to 'auto' so uploaded
PDFs open in the browser instead of downloading.

Run from your imhotep folder:
    python fix_cloudinary_resource_type.py
"""

import os

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')

with open(APP_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

old = "resource_type='raw'"
new = "resource_type='auto'"

count = content.count(old)

if count == 0:
    print("❌ Could not find resource_type='raw' in app.py")
else:
    content = content.replace(old, new)
    with open(APP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Fixed {count} instance(s) — PDFs will now open in browser.")

print("\nNext steps:")
print("  git add -A")
print("  git commit -m 'Fix Cloudinary resource type for PDF browser viewing'")
print("  git push")
