"""
fix_syntax_error3.py
Run from your imhotep folder:
    python fix_syntax_error3.py
"""

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the unclosed f''' block by looking for the pattern
# We need to find the line with </div> that's inside the unclosed f'''
# then insert the closing ''' after it, and fix the return/html lines after

# Print lines 1693-1710 (0-indexed: 1692-1709) so we can see exact content
print("=== Current lines 1693-1710 ===")
for i, line in enumerate(lines[1692:1710], start=1693):
    print(f"{i}: {repr(line)}")

print()

# Find the line with 'return redirect(url_for(\x27trainee_documents\x27))'
# that is INSIDE the f''' block (wrong place)
target_redirect = None
target_html_btn = None
target_return_html = None

for i, line in enumerate(lines):
    if "return redirect(url_for('trainee_documents'))" in line and i > 1690 and i < 1720:
        target_redirect = i
    if "Back to Trainee Profile" in line and i > 1690 and i < 1720:
        target_html_btn = i
    if line.strip() == 'return html' and i > 1690 and i < 1720:
        target_return_html = i

print(f"target_redirect line: {target_redirect + 1 if target_redirect is not None else 'NOT FOUND'}")
print(f"target_html_btn line: {target_html_btn + 1 if target_html_btn is not None else 'NOT FOUND'}")
print(f"target_return_html line: {target_return_html + 1 if target_return_html is not None else 'NOT FOUND'}")

if target_redirect is None:
    print("ERROR: Could not find misplaced return redirect line. Aborting.")
    exit(1)

# The line before return redirect should be </div> — we insert ''' after </div>
# Then fix indentation of the lines after

# Find the </div> line just before the misplaced return redirect
div_close_line = target_redirect - 1
while div_close_line >= 1690 and '</div>' not in lines[div_close_line]:
    div_close_line -= 1

print(f"</div> line: {div_close_line + 1}: {repr(lines[div_close_line])}")

confirm = input("\nProceed with fix? (yes/no): ").strip().lower()
if confirm != 'yes':
    print("Aborted.")
    exit(0)

# Insert closing ''' after </div>
lines.insert(div_close_line + 1, "        '''\n")

# After insertion, indices shift by 1
# Fix the misplaced return redirect — remove it (it's already handled elsewhere)
# and fix indentation of html += and return html lines
new_redirect_idx = target_redirect + 1  # shifted by insert
new_html_btn_idx = target_html_btn + 1
new_return_html_idx = target_return_html + 1

# Remove the misplaced return redirect line
del lines[new_redirect_idx]

# Fix indentation on html += f'<p>...' line (now shifted back)
new_html_btn_idx = new_html_btn_idx  # no change since we deleted one
lines[new_html_btn_idx] = "    " + lines[new_html_btn_idx].lstrip()

# Fix indentation on return html line
lines[new_return_html_idx] = "    " + lines[new_return_html_idx].lstrip()

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✅ Fix applied! Now run: python fix_blank_documents.py")
print("If that works, then: git add -A && git commit -m 'fix syntax errors' && git push")
