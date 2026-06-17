"""
fix_all_trainee_auth.py
Run from your imhotep folder:
    python fix_all_trainee_auth.py

Finds every route that checks session['logged_in'] and redirects to /login
but is actually a trainee route, and fixes it to check session['trainee_id']
and redirect to /trainee-login instead.
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# All the trainee routes that have the wrong auth check
fixes = [
    # (route indicator, old block, new block)
    (
        "def trainee_sign_document",
        "def trainee_sign_document(assignment_id):\n    if not session.get('logged_in'):\n        return redirect('/login')",
        "def trainee_sign_document(assignment_id):\n    if not session.get('trainee_id'):\n        return redirect('/trainee-login')"
    ),
]

# More general approach - find all instances of the pattern within trainee routes
# Replace ALL occurrences of the admin auth check that appear in trainee route functions

OLD_AUTH = "    if not session.get('logged_in'):\n        return redirect('/login')"
NEW_AUTH = "    if not session.get('trainee_id'):\n        return redirect('/trainee-login')"

# Find all trainee route functions that have the wrong check
import re

# Find all @app.route('/trainee/...') blocks
trainee_route_pattern = re.compile(
    r"(@app\.route\('/trainee[^']*'[^\n]*\)\n(?:@[^\n]+\n)*def [^\n]+\n(?:.*\n)*?)"
    r"(    if not session\.get\('logged_in'\):\n        return redirect\('/login'\))",
    re.MULTILINE
)

matches = list(trainee_route_pattern.finditer(content))
print(f"Found {len(matches)} trainee routes with wrong auth check")

count = 0
for match in matches:
    full_match = match.group(0)
    fixed = full_match.replace(
        "    if not session.get('logged_in'):\n        return redirect('/login')",
        "    if not session.get('trainee_id'):\n        return redirect('/trainee-login')"
    )
    content = content.replace(full_match, fixed, 1)
    count += 1
    print(f"  Fixed match {count}")

if count == 0:
    # Try simpler direct replacement for the sign document route specifically
    print("Regex approach found nothing. Trying direct replacement...")
    
    OLD = """def trainee_sign_document(assignment_id):
    if not session.get('logged_in'):
        return redirect('/login')"""
    NEW = """def trainee_sign_document(assignment_id):
    if not session.get('trainee_id'):
        return redirect('/trainee-login')"""
    
    if OLD in content:
        content = content.replace(OLD, NEW, 1)
        print("✅ Fixed trainee_sign_document auth")
        count += 1
    else:
        print("ERROR: Could not find trainee_sign_document. Printing context...")
        if 'trainee_sign_document' in content:
            idx = content.index('trainee_sign_document')
            print(repr(content[idx:idx+200]))

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✅ Fixed {count} trainee auth issue(s). Now run:")
print("  git add -A")
print("  git commit -m \"fix all trainee route auth checks\"")
print("  git push")
