with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
fixed = False

for i, line in enumerate(lines):
    if "return redirect(url_for('trainee_documents'))" in line:
        # Check if we're inside trainee_onboarding (look back up to 3 lines)
        context = ''.join(lines[max(0,i-3):i])
        if 'def trainee_onboarding' in context:
            print(f"✅ Removing premature redirect at line {i+1}")
            fixed = True
            continue
    new_lines.append(line)

if fixed:
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("✅ app.py saved")
else:
    print("❌ Not found")
