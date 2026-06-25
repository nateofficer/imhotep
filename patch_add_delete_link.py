"""
Patch script: adds a Delete link next to Edit/View in admin_documents.html

Usage:
    1. Place this file in the same folder as app.py
       (C:\\Users\\natec\\OneDrive\\Documents\\imhotep)
    2. In the same PowerShell window you used before, run:
       python patch_add_delete_link.py
    3. It will print SUCCESS or tell you what went wrong.
"""

import re

TEMPLATE_FILE = "templates/admin_documents.html"

# Matches the closing of the View link's {% endif %} right before the </td>,
# using flexible whitespace so exact indentation doesn't matter.
PATTERN = re.compile(r'(View</a>\s*\{%\s*endif\s*%\}\s*)(</td>)')

DELETE_LINK = (
    '<a href="/admin/documents/delete/{{ doc.id }}" '
    'onclick="return confirm(\'Delete this document?\')" '
    'style="color:#c0392b;font-weight:700;margin-left:8px;">Delete</a>\n        '
)

with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
    content = f.read()

if "Delete this document?" in content:
    print("SKIPPED: Delete link already exists in the template. No changes made.")
else:
    matches = PATTERN.findall(content)
    if len(matches) == 0:
        print("ERROR: Could not find the expected View/endif/</td> pattern.")
        print("No changes were made. Paste this output back to Claude.")
    elif len(matches) > 1:
        print(f"ERROR: Found {len(matches)} matches, expected exactly 1. Refusing to guess.")
        print("Paste this output back to Claude.")
    else:
        new_content = PATTERN.sub(lambda m: m.group(1) + DELETE_LINK + m.group(2), content, count=1)
        with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("SUCCESS: Delete link added to admin_documents.html.")
