with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the onboarding card section
idx = content.find('card_class}')
if idx > -1:
    print(content[idx-200:idx+500])
else:
    print('card_class not found')
