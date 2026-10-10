import re
import mysql.connector

conn = mysql.connector.connect(
    host='127.0.0.1', port=3306, user='root',
    password='wan1314xy', charset='utf8mb4',
    autocommit=True,
)
cur = conn.cursor()

raw = open('sql/init.sql', 'r', encoding='utf-8').read()
lines = []
for line in raw.split('\n'):
    s = line.strip()
    if s.startswith('--') or not s:
        continue
    lines.append(line)
clean = '\n'.join(lines)

for stmt in clean.split(';'):
    s = stmt.strip()
    if s:
        cur.execute(s)

cur.execute('SELECT username, real_name, role FROM users')
print('初始化完成，当前用户：')
for row in cur.fetchall():
    print(' ', row)

cur.execute('SHOW TABLES')
print('数据表：')
for row in cur.fetchall():
    print(' ', row[0])

conn.close()
