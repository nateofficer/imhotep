import os, pymysql
from urllib.parse import urlparse
url = urlparse(os.environ["MYSQL_URL"])
conn = pymysql.connect(host=url.hostname, user=url.username, password=url.password, database=url.path.lstrip("/"), port=url.port)
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM onboarding_forms")
