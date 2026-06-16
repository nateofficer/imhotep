"""
fix_assign_redirect.py
Run from your imhotep folder:
    python fix_assign_redirect.py
"""

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

OLD = """        cur.execute(
            "DELETE FROM trainee_documents WHERE trainee_id=%s AND status='pending' AND document_id NOT IN ({})".format(
        return redirect(url_for('trainee_detail', trainee_id=trainee_id))
            ),
            [trainee_id] + [int(i) for i in selected_ids] if selected_ids else [trainee_id]
        )
        for doc_id in selected_ids:
            cur.execute(
                "INSERT IGNORE INTO trainee_documents (trainee_id, document_id) VALUES (%s, %s)",
                (trainee_id, int(doc_id))
            )
        conn.commit()
        return redirect(url_for('trainees_list'))"""

NEW = """        cur.execute(
            "DELETE FROM trainee_documents WHERE trainee_id=%s AND status='pending' AND document_id NOT IN ({})".format(
                ','.join(['%s'] * len(selected_ids)) if selected_ids else '0'
            ),
            [trainee_id] + [int(i) for i in selected_ids] if selected_ids else [trainee_id]
        )
        for doc_id in selected_ids:
            cur.execute(
                "INSERT IGNORE INTO trainee_documents (trainee_id, document_id) VALUES (%s, %s)",
                (trainee_id, int(doc_id))
            )
        conn.commit()
        return redirect(url_for('trainee_detail', trainee_id=trainee_id))"""

if OLD not in content:
    print("ERROR: Could not find exact block. Printing context around 'trainees_list'...")
    if 'trainees_list' in content:
        idx = content.index('trainees_list')
        print(repr(content[idx-400:idx+100]))
    else:
        print("'trainees_list' not found.")
else:
    content = content.replace(OLD, NEW, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Fixed! Now run: python fix_blank_documents.py")
