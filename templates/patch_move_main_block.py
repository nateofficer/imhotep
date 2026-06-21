"""
Patch: move the `if __name__ == '__main__': app.run(...)` block to the very
end of app.py.

Right now it sits in the middle of the file (around line 2374), with the
entire Document Library section (admin documents, trainee documents, the
Sign page, etc.) written AFTER it. Because app.run() blocks execution,
running this file directly with `python app.py` means every route defined
after that block never actually gets registered -- it only ever worked on
Render because Render likely imports the app rather than running it as a
script, so app.run() never gets called there and route order doesn't matter.

This patch moves the if __name__ block to the true end of the file, after
every route definition, which is the standard/correct place for it. This
does not change what routes exist or how they behave on Render -- it only
fixes local testing with `python app.py`.

Run from your project root (same folder as app.py):
    python patch_move_main_block.py
"""

import shutil
from datetime import datetime

FILE = "app.py"

BLOCK = """if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)"""


def main():
    with open(FILE, "r", encoding="utf-8") as f:
        content = f.read()

    if BLOCK not in content:
        print("Could not find the expected if __name__ block -- app.py may have changed.")
        print("No changes made.")
        return

    if content.count(BLOCK) != 1:
        print(f"Found {content.count(BLOCK)} matches, expected exactly 1 -- aborting to be safe.")
        return

    backup_name = f"{FILE}.bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(FILE, backup_name)
    print(f"Backup saved as {backup_name}")

    # Remove the block from its current spot (and one of the surrounding blank lines)
    content = content.replace("\n\n\n" + BLOCK + "\n\n\n", "\n\n\n")
    if BLOCK in content:
        # Fallback in case the surrounding blank-line pattern didn't match exactly
        content = content.replace(BLOCK + "\n\n\n", "")
        content = content.replace(BLOCK, "")

    # Make sure the file ends with exactly one trailing newline before we append
    content = content.rstrip("\n") + "\n"

    # Append the block at the true end of the file
    content += "\n\n" + BLOCK + "\n"

    with open(FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("Done. The if __name__ == '__main__': block now sits at the true end of app.py.")
    print("All routes (including the Document Library section) will now register")
    print("correctly when running `python app.py` locally.")


if __name__ == "__main__":
    main()
