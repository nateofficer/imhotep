import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Trainee login redirect — /training → /trainee/documents
old1 = "return redirect('/training')"
new1 = "return redirect('/trainee/documents')"
if old1 in content:
    content = content.replace(old1, new1)
    print("✅ Fix 1 applied: trainee login now redirects to /trainee/documents")
else:
    print("⚠️  Fix 1 not found — check line 1274 manually")

# Fix 2: Remove premature redirect from trainee_onboarding()
# The dead line is:     return redirect(url_for('trainee_documents'))
old2 = """def trainee_onboarding():
    return redirect(url_for('trainee_documents'))
    conn = get_db()"""
new2 = """def trainee_onboarding():
    conn = get_db()"""
if old2 in content:
    content = content.replace(old2, new2)
    print("✅ Fix 2 applied: removed premature redirect from trainee_onboarding()")
else:
    print("⚠️  Fix 2 not found — trying alternate whitespace...")
    # Try with 4-space indent
    old2b = "def trainee_onboarding():\n    return redirect(url_for('trainee_documents'))\n    conn = get_db()"
    new2b = "def trainee_onboarding():\n    conn = get_db()"
    if old2b in content:
        content = content.replace(old2b, new2b)
        print("✅ Fix 2 applied (alternate): removed premature redirect from trainee_onboarding()")
    else:
        print("❌ Fix 2 failed — check trainee_onboarding() manually around line 1711")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone. Verify with:")
print("  Select-String -Path app.py -Pattern \"trainee_onboarding|redirect.*training\"")
