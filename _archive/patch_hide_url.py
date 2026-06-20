with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """            <h2><span class="step-number {step_class}">{i}</span>{f["title"]}</h2>
            {download_html}
            {action_html}"""

new = """            <h2><span class="step-number {step_class}">{i}</span>{f["title"]}</h2>
            {download_html}
            {action_html if not (f['description'] or '').startswith('http') else action_html}"""

# Simpler approach - just hide description if it's a URL
old2 = '            <p>{f["description"] or ""}</p>\n            {download_html}'
new2 = '            {download_html}'

if old2 in content:
    content = content.replace(old2, new2)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Done!')
else:
    # Try without the description line
    print('Looking for description line...')
    idx = content.find('download_html}\n            {action_html}')
    if idx > -1:
        print('Card looks correct already - description may be elsewhere')
        # Show context
        print(repr(content[idx-200:idx+100]))
