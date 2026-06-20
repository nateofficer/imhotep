patch_file = r"C:\Users\natec\OneDrive\Documents\imhotep\app.py"

with open(patch_file, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''            trainee_rows += f\'\'\'
            <tr>
                <td>{name}</td>
                <td>{hired}</td>
                <td><a class="btn btn-sm" href="/trainee/{t[\\'id\\']}">View</a></td>
            </tr>\'\'\''''

new = '''            tid = t['id']
            trainee_rows += f\'\'\'
            <tr>
                <td>{name}</td>
                <td>{hired}</td>
                <td><a class="btn btn-sm" href="/trainee/{tid}">View</a></td>
            </tr>\'\'\''''

assert old in content, "ERROR: target string not found"
content = content.replace(old, new, 1)

with open(patch_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Trainee link syntax fixed.")
