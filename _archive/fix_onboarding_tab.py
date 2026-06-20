with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = "def trainee_onboarding():\n\treturn redirect(url_for('trainee_documents'))\n\tconn = get_db()"
new = "def trainee_onboarding():\n\tconn = get_db()"

if old in content:
    content = content.replace(old, new)
    print("✅ Fix applied: removed premature redirect from trainee_onboarding()")
else:
    print("❌ Still no match — printing raw repr:")
    idx = content.find("def trainee_onboarding()")
    if idx != -1:
        print(repr(content[idx:idx+120]))

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
