path = r"C:\Users\natec\OneDrive\Documents\imhotep\app.py"

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

target_line = 451  # 1-indexed
idx = target_line - 1

print(f"Line {target_line} current content: {lines[idx].rstrip()}")

if "redirect('/admin/documents')" in lines[idx]:
    lines[idx] = lines[idx].replace("redirect('/admin/documents')", "redirect('/applications')")
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"Fixed — line {target_line} now reads: {lines[idx].rstrip()}")
else:
    print("ERROR: Expected content not found on line 451. No changes made.")
