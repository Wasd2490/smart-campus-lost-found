import mysql.connector

conn = mysql.connector.connect(
    host='127.0.0.1', port=3306, user='root',
    password='wan1314xy', database='lost_and_found', autocommit=True
)
cur = conn.cursor()

# 给 users 表增加校园字段
columns = [
    ("student_id", "VARCHAR(20)"),
    ("college", "VARCHAR(50)"),
    ("class_name", "VARCHAR(50)"),
]
for col, typ in columns:
    try:
        cur.execute(f"ALTER TABLE users ADD COLUMN {col} {typ}")
        print(f"users.{col} 已添加")
    except Exception as e:
        if "Duplicate column" in str(e):
            print(f"users.{col} 已存在，跳过")
        else:
            raise

conn.close()
