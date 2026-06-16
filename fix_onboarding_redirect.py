with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = "def trainee_onboarding():\n    return redirect(url_for('trainee_documents'))\n    conn = get_db()"
new = "def trainee_onboarding():\n    conn = get_db()"

if old in content:
    content = content.replace(old, new)
    print("✅ Fix applied: removed premature redirect from trainee_onboarding()")
else:
    print("❌ Still no match — printing what's actually there:")
    idx = content.find("def trainee_onboarding()")
    if idx != -1:
        print(repr(content[idx:idx+120]))
    else:
        print("Function not found at all!")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
