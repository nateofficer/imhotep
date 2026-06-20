"""
Imhotep - Fix Login Redirect
------------------------------
Changes the post-login redirect to /admin/documents
so you land there directly after logging in.

Run from your imhotep folder:
    python fix_login_redirect.py
"""

import os

APP_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py')

with open(APP_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

old = "session['logged_in'] = True\n            return redirect('/applications')"
new = "session['logged_in'] = True\n            session.permanent = True\n            return redirect('/admin/documents')"

if old not in content:
    print("❌ Could not find the login redirect line.")
    print("Looking for it...")
    # Try to find what's actually there
    for i, line in enumerate(content.split('\n')):
        if 'logged_in' in line and 'True' in line:
            print(f"  Line {i+1}: {line}")
else:
    content = content.replace(old, new)
    with open(APP_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Login now redirects to /admin/documents")
    print("✅ Session set to permanent (24 hours)")

print("\nNext steps:")
print("  git add -A")
print("  git commit -m 'Fix login redirect to admin/documents'")
print("  git push")
