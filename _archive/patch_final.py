with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = "        html += f'''\n        <div"
new = "        html += f'''\n        <div class=\"{card_class}\">\n            <h2><span class=\"step-number {step_class}\">{i}</span>{f[\"title\"]}</h2>\n            {download_html}\n            {action_html}\n        </div>\n        '''"

# Find the html += f''' near download_html
idx = content.find("download_html = ''")
if idx == -1:
    print("download_html not found")
else:
    # Find the html += f''' after it
    idx2 = content.find("html += f'''", idx)
    if idx2 == -1:
        print("html += f''' not found after download_html")
    else:
        # Find the end of this block (the closing ''')
        idx3 = content.find("'''", idx2 + 12)
        if idx3 == -1:
            print("closing ''' not found")
        else:
            old_block = content[idx2:idx3+3]
            print("Found block:")
            print(repr(old_block))
            print("\nReplacing...")
            new_block = "        html += f'''\n        <div class=\"{card_class}\">\n            <h2><span class=\"step-number {step_class}\">{i}</span>{f[\"title\"]}</h2>\n            {download_html}\n            {action_html}\n        </div>\n        '''"
            content = content[:idx2] + new_block + content[idx3+3:]
            with open('app.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("Done!")
