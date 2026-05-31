with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find download_html section
idx = content.find('download_html')
if idx > -1:
    print("FOUND download_html at position", idx)
    print(content[idx-100:idx+600])
else:
    print('download_html NOT found')
    # Find the onboarding card loop
    idx2 = content.find('onboard-step')
    if idx2 > -1:
        print("Found onboard-step at:", idx2)
        print(content[idx2-200:idx2+400])
