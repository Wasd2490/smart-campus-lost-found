import mysql.connector, hashlib

conn = mysql.connector.connect(
    host='127.0.0.1', port=3306, user='root',
    password='wan1314xy', database='lost_and_found', autocommit=True
)
cur = conn.cursor()

# 清空所有业务表，重置自增ID
cur.execute('SET FOREIGN_KEY_CHECKS=0')
for t in ['comments', 'claim_records', 'lost_items', 'found_items', 'users']:
    cur.execute(f'TRUNCATE TABLE {t}')
    print(f'{t} 已清空')
cur.execute('SET FOREIGN_KEY_CHECKS=1')

# 恢复管理员账号
pw = hashlib.sha256('admin123'.encode()).hexdigest()
cur.execute(
    "INSERT INTO users(username,password_hash,real_name,role) VALUES(%s,%s,%s,%s)",
    ('admin', pw, '系统管理员', 'admin')
)
print('管理员账号 admin/admin123 已恢复')
conn.close()
