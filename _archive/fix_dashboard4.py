patch_file = r"C:\Users\natec\OneDrive\Documents\imhotep\app.py"

with open(patch_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

fixed_count = 0
for i, line in enumerate(lines):
    stripped = line.strip()
    
    # Fix apps ternary
    if 'app_rows' in stripped and 'if recent_apps else' in stripped:
        lines[i] = '                {apps_section}\n'
        fixed_count += 1
        print(f"Fixed apps ternary at line {i+1}")
    
    # Fix trainees ternary
    elif 'trainee_rows' in stripped and 'if recent_trainees else' in stripped:
        lines[i] = '                {trainees_section}\n'
        fixed_count += 1
        print(f"Fixed trainees ternary at line {i+1}")
    
    # Fix leads ternary
    elif 'lead_rows' in stripped and 'if recent_leads else' in stripped:
        lines[i] = '                {leads_section}\n'
        fixed_count += 1
        print(f"Fixed leads ternary at line {i+1}")

with open(patch_file, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"Fixed {fixed_count} lines. Running syntax check...")
import subprocess
result = subprocess.run(['python', '-m', 'py_compile', patch_file], capture_output=True, text=True)
if result.returncode == 0:
    print("SYNTAX OK - ready to push!")
else:
    print("STILL HAS ERRORS:")
    print(result.stderr)
