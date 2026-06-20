"""
Patch: remove the "(Placeholder text -- Nate, edit this paragraph...)" note
that accidentally ended up visible in the About paragraph on the homepage.

Run from your project root (same folder as app.py):
    python patch_remove_placeholder_note.py
"""

import shutil
from datetime import datetime

FILE = "app.py"

OLD = """        <p>Casey's Cleaning Company keeps Las Vegas homes and businesses spotless with a trained, background-checked team you can trust. Whether it's a one-time deep clean, a recurring service, or a short-term rental turnover, we treat every property like it's our own. (Placeholder text -- Nate, edit this paragraph to say whatever you'd like about the company.)</p>"""

NEW = """        <p>Casey's Cleaning Company keeps Las Vegas homes and businesses spotless with a trained, background-checked team you can trust. Whether it's a one-time deep clean, a recurring service, or a short-term rental turnover, we treat every property like it's our own.</p>"""


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if OLD not in content:
        print("Could not find the placeholder text — app.py may have changed.")
        print("No changes made.")
        return

    if content.count(OLD) != 1:
        print(f"Found {content.count(OLD)} matches, expected exactly 1 — aborting to be safe.")
        return

    backup_name = f"{FILE}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(FILE, backup_name)
    print(f"Backup saved as {backup_name}")

    content = content.replace(OLD, NEW)

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("Done. The About paragraph no longer mentions the placeholder note.")


if __name__ == "__main__":
    main()
