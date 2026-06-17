import re

patch_file = r"C:\Users\natec\OneDrive\Documents\imhotep\app.py"

with open(patch_file, 'r', encoding='utf-8') as f:
    content = f.read()

# ── 1. Fix login redirect: /applications → /dashboard ──────────────────────
old_login = "return redirect('/applications')"
new_login = "return redirect('/dashboard')"
assert old_login in content, "ERROR: login redirect not found"
content = content.replace(old_login, new_login, 1)

# ── 2. Insert /dashboard route before /applications route ──────────────────
dashboard_route = '''
@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    # Open applications (candidates not yet hired)
    cursor.execute(\'\'\'
        SELECT candidates.*, jobs.title as job_title
        FROM candidates
        LEFT JOIN jobs ON candidates.job_id = jobs.id
        ORDER BY candidates.applied_date DESC
        LIMIT 5
    \'\'\')
    recent_apps = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) as cnt FROM candidates')
    app_count = cursor.fetchone()['cnt']

    # Active trainees
    cursor.execute(\'\'\'
        SELECT trainees.*, candidates.first_name, candidates.last_name
        FROM trainees
        LEFT JOIN candidates ON trainees.candidate_id = candidates.id
        ORDER BY trainees.hired_date DESC
        LIMIT 5
    \'\'\')
    recent_trainees = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) as cnt FROM trainees')
    trainee_count = cursor.fetchone()['cnt']

    # Recent CRM leads
    cursor.execute(\'\'\'
        SELECT * FROM leads
        ORDER BY id DESC
        LIMIT 5
    \'\'\')
    recent_leads = cursor.fetchall()
    cursor.execute('SELECT COUNT(*) as cnt FROM leads')
    lead_count = cursor.fetchone()['cnt']

    conn.close()

    # Build application rows
    app_rows = ''
    for a in recent_apps:
        name = f"{a['first_name']} {a['last_name']}" if a.get('first_name') else 'Unknown'
        job = a.get('job_title') or 'N/A'
        date = str(a.get('applied_date', ''))[:10]
        app_rows += f\'\'\'
            <tr>
                <td>{name}</td>
                <td>{job}</td>
                <td>{date}</td>
                <td><a class="btn btn-sm" href="/applications">View</a></td>
            </tr>\'\'\'

    # Build trainee rows
    trainee_rows = ''
    for t in recent_trainees:
        name = f"{t['first_name']} {t['last_name']}" if t.get('first_name') else 'Unknown'
        hired = str(t.get('hired_date', ''))[:10]
        trainee_rows += f\'\'\'
            <tr>
                <td>{name}</td>
                <td>{hired}</td>
                <td><a class="btn btn-sm" href="/trainee/{t[\\'id\\']}">View</a></td>
            </tr>\'\'\'

    # Build lead rows
    lead_rows = ''
    for l in recent_leads:
        name = f"{l['first_name']} {l['last_name']}"
        status = l.get('status', 'new').title()
        stype = l.get('service_type', '')
        badge_color = '#e07b39' if status.lower() == 'new' else '#6b8f71'
        lead_rows += f\'\'\'
            <tr>
                <td>{name}</td>
                <td>{stype}</td>
                <td><span style="background:{badge_color};color:#fff;padding:2px 8px;border-radius:10px;font-size:0.8rem;">{status}</span></td>
                <td><a class="btn btn-sm" href="/crm">View</a></td>
            </tr>\'\'\'

    html = STYLE + admin_nav() + f\'\'\'
    <style>
        .dash-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}
        .dash-stat {{
            background: #fff;
            border-radius: 10px;
            padding: 1.5rem 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            border-left: 5px solid #8B5E3C;
            text-decoration: none;
            color: inherit;
            transition: transform 0.15s, box-shadow 0.15s;
        }}
        .dash-stat:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 18px rgba(0,0,0,0.13);
        }}
        .dash-stat .stat-number {{
            font-size: 2.8rem;
            font-weight: 700;
            color: #8B5E3C;
            line-height: 1;
        }}
        .dash-stat .stat-label {{
            font-size: 1rem;
            color: #555;
            margin-top: 0.4rem;
            font-family: 'Nunito', sans-serif;
        }}
        .dash-stat .stat-icon {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        .dash-card {{
            background: #fff;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 1.5rem;
        }}
        .dash-card h2 {{
            font-family: 'Lora', serif;
            color: #5a3e2b;
            font-size: 1.2rem;
            margin: 0 0 1rem 0;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #f0e8df;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .dash-card h2 a {{
            font-size: 0.8rem;
            font-family: 'Nunito', sans-serif;
            color: #e07b39;
            text-decoration: none;
            font-weight: 600;
        }}
        .dash-card table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
        }}
        .dash-card th {{
            text-align: left;
            color: #8B5E3C;
            font-weight: 700;
            padding: 0.4rem 0.5rem;
            border-bottom: 1px solid #f0e8df;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        .dash-card td {{
            padding: 0.5rem 0.5rem;
            border-bottom: 1px solid #faf6f2;
            color: #333;
        }}
        .dash-card tr:last-child td {{ border-bottom: none; }}
        .dash-card .empty-msg {{
            color: #aaa;
            font-style: italic;
            padding: 0.5rem 0;
        }}
        .schedule-placeholder {{
            text-align: center;
            padding: 2.5rem 1rem;
            color: #aaa;
        }}
        .schedule-placeholder .big-icon {{ font-size: 3rem; }}
        .schedule-placeholder p {{ margin: 0.5rem 0 0 0; font-style: italic; }}
        .dash-cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 1.5rem;
        }}
        .btn-sm {{
            padding: 3px 10px;
            font-size: 0.8rem;
            background: #8B5E3C;
            color: #fff;
            border-radius: 5px;
            text-decoration: none;
        }}
    </style>

    <div style="max-width:1200px;margin:2rem auto;padding:0 1.5rem;">
        <h1 style="font-family:\\'Lora\\',serif;color:#5a3e2b;margin-bottom:0.25rem;">Dashboard</h1>
        <p style="color:#888;font-family:\\'Nunito\\',sans-serif;margin-bottom:1.8rem;">Casey\\'s Cleaning — Business Overview</p>

        <!-- Stat Cards -->
        <div class="dash-grid">
            <a class="dash-stat" href="/applications">
                <div class="stat-icon">📋</div>
                <div class="stat-number">{app_count}</div>
                <div class="stat-label">Open Applications</div>
            </a>
            <a class="dash-stat" href="/trainees">
                <div class="stat-icon">👷</div>
                <div class="stat-number">{trainee_count}</div>
                <div class="stat-label">Active Trainees</div>
            </a>
            <a class="dash-stat" href="/crm">
                <div class="stat-icon">📞</div>
                <div class="stat-number">{lead_count}</div>
                <div class="stat-label">CRM Leads</div>
            </a>
            <a class="dash-stat" href="/schedule" style="border-left-color:#b0bec5;opacity:0.7;cursor:default;">
                <div class="stat-icon">📅</div>
                <div class="stat-number">—</div>
                <div class="stat-label">Upcoming Jobs <span style="font-size:0.75rem;">(coming soon)</span></div>
            </a>
        </div>

        <!-- Detail Cards -->
        <div class="dash-cards-grid">

            <!-- Applications -->
            <div class="dash-card">
                <h2>Recent Applications <a href="/applications">View All →</a></h2>
                {"<table><tr><th>Name</th><th>Position</th><th>Date</th><th></th></tr>" + app_rows + "</table>" if recent_apps else \\'<p class="empty-msg">No applications yet.</p>\\'}
            </div>

            <!-- Trainees -->
            <div class="dash-card">
                <h2>Active Trainees <a href="/trainees">View All →</a></h2>
                {"<table><tr><th>Name</th><th>Hired</th><th></th></tr>" + trainee_rows + "</table>" if recent_trainees else \\'<p class="empty-msg">No trainees yet.</p>\\'}
            </div>

            <!-- CRM Leads -->
            <div class="dash-card">
                <h2>Recent Leads <a href="/crm">View All →</a></h2>
                {"<table><tr><th>Name</th><th>Service</th><th>Status</th><th></th></tr>" + lead_rows + "</table>" if recent_leads else \\'<p class="empty-msg">No leads yet.</p>\\'}
            </div>

            <!-- Schedule Placeholder -->
            <div class="dash-card">
                <h2>Upcoming Schedule</h2>
                <div class="schedule-placeholder">
                    <div class="big-icon">🗓️</div>
                    <p>Scheduling module coming soon.</p>
                </div>
            </div>

        </div>
    </div>
    \'\'\'
    return html

'''

# Insert dashboard route before /applications route
target = "@app.route('/applications')\n@login_required"
assert target in content, "ERROR: /applications route anchor not found"
content = content.replace(target, dashboard_route + target, 1)

with open(patch_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Dashboard route added and login redirect updated.")
