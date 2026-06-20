text = open("app.py", encoding="utf-8").read()
old = "<a class=\"btn\" href=\"/admin/documents/assign/{trainee_id}\">Assign Documents</a>"
count = text.count(old)
print("Found", count, "matches")
