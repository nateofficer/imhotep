text = open("app.py", encoding="utf-8").read()
old_btn = "<a class=\"btn\" href=\"/admin/documents/assign/{trainee_id}\">Assign Documents</a>"
text = text.replace(old_btn, "")
open("app.py", "w", encoding="utf-8").write(text)
print("Done - button line removed")
