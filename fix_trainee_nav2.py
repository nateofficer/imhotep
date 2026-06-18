patch_file = r"C:\Users\natec\OneDrive\Documents\imhotep\app.py"

with open(patch_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed = 0
for i, line in enumerate(lines):
    if '<a href="/onboarding">My Onboarding</a>' in line and i > 325 and i < 345:
        lines[i] = line.replace(
            '<a href="/onboarding">My Onboarding</a>',
            '<a href="/trainee/documents">My Documents</a>'
        )
        fixed += 1
        print(f"Fixed trainee_nav at line {i+1}")

if fixed == 0:
    print("ERROR: trainee_nav Onboarding link not found in expected range")
else:
    with open(patch_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    import subprocess
    result = subprocess.run(['python', '-m', 'py_compile', patch_file], capture_output=True, text=True)
    if result.returncode == 0:
        print("SYNTAX OK - ready to push!")
    else:
        print("SYNTAX ERROR:")
        print(result.stderr)
