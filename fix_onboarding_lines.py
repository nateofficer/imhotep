with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed = False
skip_next = False
new_lines = []

for i, line in enumerate(lines):
    if skip_next:
        skip_next = False
        continue
    # If this line is the premature redirect inside trainee_onboarding
    if "return redirect(url_for('trainee_documents'))" in line:
        # Check previous line was the function def
        if i > 0 and 'def trainee_onboarding' in lines[i-1]:
            print(f"✅ Found premature redirect at line {i+1}, removing it")
            fixed = True
            continue  # skip this line
    new_lines.append(line)

if fixed:
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("✅ app.py updated successfully")
else:
    print("❌ Line not found — printing lines around trainee_onboarding:")
    for i, line in enumerate(lines):
        if 'trainee_onboarding' in line:
            start = max(0, i-1)
            for j in range(start, min(len(lines), i+4)):
                print(f"  {j+1}: {repr(lines[j])}")
