"""
Patch: fix uploaded documents always downloading instead of opening in the
browser.

Cloudinary forces a download (Content-Disposition: attachment) by default
for resource_type='raw' uploads -- that's documented Cloudinary behavior,
not a bug in your code or a browser setting. Cloudinary's own docs list
PDFs under resource_type='image' (same category as photos), which delivers
inline instead.

This patch changes both upload calls (Add Document and Edit Document) from
resource_type='raw' to resource_type='image'. Since this form is labeled
"Upload PDF from your computer," this only affects PDF uploads.

Note: this only fixes documents uploaded AFTER this patch is live. Anything
already uploaded under the old 'raw' setting will keep downloading until
it's re-uploaded (e.g. Kitchen checklist and "cleaning procedure" will need
to be re-uploaded once this is live, if they still download).

Run from your project root (same folder as app.py):
    python patch_cloudinary_inline_pdf.py
"""

import shutil
from datetime import datetime

FILE = "app.py"

OLD = "                resource_type='raw',"
NEW = "                resource_type='image',"


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    count = content.count(OLD)
    if count == 0:
        print("Could not find the expected resource_type='raw' lines -- app.py may have changed.")
        print("No changes made.")
        return
    if count != 2:
        print(f"Found {count} matches, expected exactly 2 -- aborting to be safe.")
        print("(This usually means something else in app.py changed since this patch was written.)")
        return

    backup_name = f"{FILE}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(FILE, backup_name)
    print(f"Backup saved as {backup_name}")

    content = content.replace(OLD, NEW)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("Done. Both upload calls (Add Document and Edit Document) now use")
    print("resource_type='image', so newly uploaded PDFs will open inline")
    print("in the browser instead of downloading.")
    print()
    print("Remember: documents already uploaded before this patch (Kitchen")
    print("checklist, cleaning procedure) will need to be re-uploaded to pick")
    print("up the fix -- this only changes behavior for new uploads.")


if __name__ == "__main__":
    main()
