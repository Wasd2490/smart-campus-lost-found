import mysql.connector
conn = mysql.connector.connect(
    host='127.0.0.1', port=3306, user='root',
    password='wan1314xy', database='lost_and_found', autocommit=True
)
cur = conn.cursor()
cur.execute("DELETE FROM users WHERE username IN ('testuser','teststu')")
cur.execute("SELECT COUNT(*) FROM users")
print('清理完成，剩余用户数:', cur.fetchone()[0])
conn.close()
