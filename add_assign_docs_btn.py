path = r"C:\Users\natec\OneDrive\Documents\imhotep\app.py"

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# ── 1. Add Documents link to admin nav (before Logout) ──────────────────────
old_nav = '<a href="/trainees">Trainees</a>\n        <a href="/logout">Logout</a>'
new_nav = '<a href="/trainees">Trainees</a>\n        <a href="/admin/documents">Documents</a>\n        <a href="/logout">Logout</a>'

if old_nav in content:
    content = content.replace(old_nav, new_nav, 1)
    changes += 1
    print("✅ 1. Documents link added to admin nav")
else:
    print("❌ 1. Could not find admin nav target — check manually")

# ── 2. Add Assign Documents button to trainees LIST page ────────────────────
old_list_btn = '<a class="btn" href="/trainee/{t[\'id\']}">View Details &amp; Access Code</a>'
new_list_btn = (
    '<a class="btn" href="/trainee/{t[\'id\']}">View Details &amp; Access Code</a>\n'
    '                <a class="btn" href="/admin/documents/assign/{t[\'id\']}">Assign Documents</a>'
)

if old_list_btn in content:
    content = content.replace(old_list_btn, new_list_btn, 1)
    changes += 1
    print("✅ 2. Assign Documents button added to Trainees list")
else:
    print("❌ 2. Could not find Trainees list button — check manually")

# ── 3. Add Assign Documents button to trainee DETAIL page ───────────────────
old_detail = "        <div class=\"access-code-display\">{t['access_code']}</div>"
new_detail = (
    "        <div class=\"access-code-display\">{t['access_code']}</div>\n"
    "        <a class=\"btn\" href=\"/admin/documents/assign/{trainee_id}\">Assign Documents</a>"
)

if old_detail in content:
    content = content.replace(old_detail, new_detail, 1)
    changes += 1
    print("✅ 3. Assign Documents button added to Trainee detail page")
else:
    print("❌ 3. Could not find trainee detail access code block — check manually")

# ── Save ─────────────────────────────────────────────────────────────────────
if changes > 0:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\nDone — {changes}/3 changes applied and saved.")
else:
    print("\nNo changes made.")
