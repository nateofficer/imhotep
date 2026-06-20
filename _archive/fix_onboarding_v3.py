with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
fixed = False

for i, line in enumerate(lines):
    if 'url_for(trainee_documents)' in line or "url_for('trainee_documents')" in line or 'url_for("trainee_documents")' in line:
        context = ''.join(lines[max(0,i-3):i])
        if 'def trainee_onboarding' in context:
            print(f"✅ Removing line {i+1}: {repr(line)}")
            fixed = True
            continue
    new_lines.append(line)

if fixed:
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("✅ app.py saved")
else:
    print("❌ Still not found — line 1712 content:")
    print(repr(lines[1711]))
