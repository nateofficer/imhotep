"""
Imhotep - Fix Cloudinary PDF Upload
-------------------------------------
Fixes two issues:
1. Sets resource_type back to 'raw' for PDFs (correct type)
2. Adds public access so files can be viewed in browser

Run from your imhotep folder:
    python fix_cloudinary_pdf.py
"""

import os

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')

with open(APP_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

old = """            upload_result = cloudinary.uploader.upload(
                uploaded_file,
                resource_type='auto',
                folder='imhotep_docs',
                use_filename=True,
                unique_filename=True
            )
            file_url = upload_result.get('secure_url', '')"""

new = """            upload_result = cloudinary.uploader.upload(
                uploaded_file,
                resource_type='raw',
                folder='imhotep_docs',
                use_filename=True,
                unique_filename=True,
                access_mode='public',
                type='upload'
            )
            file_url = upload_result.get('secure_url', '')"""

count = content.count(old)

if count == 0:
    print("❌ Could not find upload block — checking what's in app.py...")
    for i, line in enumerate(content.split('\n')):
        if 'cloudinary.uploader.upload' in line:
            print(f"  Line {i+1}: {line}")
else:
    content = content.replace(old, new)
    with open(APP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Fixed {count} upload block(s) — PDFs will now be publicly accessible.")

print("\nNext steps:")
print("  git add -A")
print("  git commit -m 'Fix Cloudinary PDF public access'")
print("  git push")
