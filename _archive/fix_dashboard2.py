patch_file = r"C:\Users\natec\OneDrive\Documents\imhotep\app.py"

with open(patch_file, 'r', encoding='utf-8') as f:
    content = f.read()

old = "        <td><a class=\"btn btn-sm\" href=\"/trainee/{t[\\'id\\']}\">View</a></td>"
new = "        <td><a class=\"btn btn-sm\" href=\"/trainee/{t['id']}\">View</a></td>"

if old in content:
    content = content.replace(old, new, 1)
    with open(patch_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS: Fixed with method 1")
else:
    # Try alternate escaping
    old2 = "        <td><a class=\"btn btn-sm\" href=\"/trainee/{t[\\'id\\']}\">View</a></td>"
    print(f"Method 1 failed. Searching for the line differently...")
    
    lines = content.split('\n')
    fixed = False
    for i, line in enumerate(lines):
        if 'btn-sm' in line and '/trainee/' in line and 'id' in line:
            print(f"Found at line {i+1}: {repr(line)}")
            tid_line = "            tid = t['id']"
            new_line = "            <td><a class=\"btn btn-sm\" href=\"/trainee/{tid}\">View</a></td>"
            # Insert tid assignment before the trainee_rows += line
            for j in range(i, max(0, i-5), -1):
                if 'trainee_rows +=' in lines[j]:
                    lines.insert(j, tid_line)
                    lines[i+1] = new_line  # +1 because we inserted a line
                    fixed = True
                    break
            break
    
    if fixed:
        content = '\n'.join(lines)
        with open(patch_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("SUCCESS: Fixed with method 2")
    else:
        print("FAILED: Could not locate the line to fix")
