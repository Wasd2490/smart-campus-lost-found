# 智慧校园失物登记认领系统

基于原生 HTTP 的校园失物招领全栈应用，不使用任何 Web 框架。

---

## 一、项目技术栈

| 层 | 技术 | 说明 |
|---|---|---|
| 前端 | HTML + CSS + 原生 JavaScript | fetch 发请求，无框架 |
| 后端 | Python 标准库 http.server | 原生处理 HTTP 报文 |
| 数据库 | MySQL | 5 张业务表 |
| 会话 | Cookie (SESSION_ID) | 内存会话表 |

---

## 二、目录结构

```
lost-and-found/
├── server.json           # 后端主程序（所有路由）
├── db.py                 # MySQL 连接封装
├── reset_db.py           # 一键清空数据（保留表结构）
├── init_db.py            # 首次初始化建库
├── migrate_add_student_fields.py  # 数据库字段迁移脚本
├── sql/init.sql          # 建表 SQL
├── static/
│   ├── index.html        # 首页（寻物/招领列表 + 搜索）
│   ├── login.html        # 登录
│   ├── register.html    # 注册（含学号/学院/班级）
│   ├── post-lost.html    # 失物登记（带拍照上传）
│   ├── post-notice.html  # 招领通知（带拍照上传）
│   ├── post-found.html   # 领取确认（下拉选物品 + 表单）
│   ├── detail.html      # 物品详情（图片/联系方式/认领/评论）
│   ├── my.html          # 我的记录（发布/认领列表）
│   ├── admin.html        # 管理后台（审核/处理认领/用户）
│   ├── css/style.css     # 全局样式
│   ├── js/common.js     # 公共 JS（api/导航/工具）
│   └── uploads/         # 上传图片目录
└── README.md
```

---

## 三、快速启动

### 1. 准备 MySQL

修改 `db.py` 中的连接配置：

```python
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "你的MySQL密码",
    "database": "lost_and_found",
    "charset": "utf8mb4",
}
```

### 2. 初始化数据库

```bash
python init_db.py
```

自动建库、建表、插入管理员账号。

### 3. 启动服务器

```bash
python server.py
```

启动后会显示三个地址：
- 本机访问：`http://127.0.0.1:8000`
- 局域网访问：`http://你的局域网IP:8000`

---

## 四、默认账号

| 账号 | 密码 | 角色 |
|---|---|---|
| admin | admin123 | 管理员 |

普通用户在注册页自行注册（注册成功自动登录）。

---

## 五、功能说明

### 学生端

| 功能 | 说明 |
|---|---|
| 注册 | 用户名 + 密码 + 真实姓名（必填）+ 学号 + 学院 + 班级 + 手机号 |
| 首页 | 双 Tab 切换寻物/招领，关键词搜索，只显示已审核物品 |
| 失物登记 | 填写丢失物品信息，可拍照上传照片，提交后待审核 |
| 招领通知 | 填写捡到物品信息，可拍照上传照片，提交后待审核 |
| 物品详情 | 描述、照片、地点时间、联系方式（蓝色卡片高亮）、评论区 |
| 申请认领 | 招领物品详情页，失主填写物品特征提交认领申请 |
| 领取确认 | 下拉选物品 + 填写说明，确认后物品从首页消失（数据库保留） |
| 我的记录 | 我发布的寻物/招领、我提交的认领，寻物有"已找回"按钮 |

### 管理员端（/admin.html）

| 功能 | 说明 |
|---|---|
| 统计卡片 | 用户数、待审核物品数、待处理认领数 |
| 待审核物品 | 通过 / 驳回 |
| 待处理认领 | 通过 / 拒绝，通过后物品自动标记已领取 |
| 用户列表 | 查看所有注册用户信息（姓名、学号、学院、班级） |

---

## 六、数据库表

| 表 | 主要字段 |
|---|---|
| users | id, username, password_hash, real_name, student_id, college, class_name, phone, role |
| lost_items | id, user_id, title, description, category, location_lost, time_lost, contact, image_path, status |
| found_items | id, user_id, title, description, category, location_found, time_found, contact, image_path, status |
| claim_records | id, item_type, item_id, user_id, claim_reason, status |
| comments | id, item_type, item_id, user_id, content |

**状态流转**：`pending（待审核）` → `approved（已通过）` → `claimed（已找回/已领取）`，也可 `rejected（已驳回）`。

---

## 七、API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /api/register | 注册（自动登录） |
| POST | /api/login | 登录 |
| POST | /api/logout | 退出 |
| GET | /api/me | 当前登录用户 |
| GET | /api/lost | 失物列表 |
| GET | /api/lost/{id} | 失物详情 |
| POST | /api/lost | 发布失物 |
| GET | /api/found | 招领列表 |
| GET | /api/found/{id} | 招领详情 |
| POST | /api/found | 发布招领 |
| POST | /api/claim | 提交认领申请 |
| POST | /api/recover | 用户确认领取 |
| POST | /api/upload | base64 图片上传 |
| GET | /api/comments | 评论列表 |
| POST | /api/comments | 发表评论 |
| GET | /api/my/posts | 我发布的 |
| GET | /api/my/claims | 我认领的 |
| GET | /api/admin/pending-items | 待审核物品 |
| GET | /api/admin/claims | 待处理认领 |
| GET | /api/admin/users | 用户列表 |
| PUT | /api/admin/item/{type}/{id}/status | 审核物品 |
| PUT | /api/admin/claim/{id}/status | 处理认领 |

---

## 八、外网访问配置（重要）

服务器已绑定 `0.0.0.0`，局域网可直接访问。要让外网用户也能访问，有两种方案：

### 方案一：路由器端口转发（有公网IP）

适合：家里有公网IP，有路由器管理权限。

**步骤**：

1. **查看本机局域网IP**：
   ```bash
   ipconfig
   ```
   找到以太网/WLAN 的 IPv4 地址，例如 `192.168.1.100`

2. **登录路由器管理页**：
   浏览器打开 `192.168.1.1`（或路由器底部标签上的地址）

3. **添加端口转发规则**（虚拟服务器/NAT）：
   - 外部端口：`8000`
   - 内部IP：`192.168.1.100`（你的本机IP）
   - 内部端口：`8000`
   - 协议：TCP

4. **确认公网IP**：
   浏览器打开 `ip138.com` 查看公网IP

5. **外网访问**：
   ```
   http://你的公网IP:8000
   ```

> 注意：校园网通常没有公网IP，此方案可能不适用。

### 方案二：内网穿透（无公网IP，推荐）

适合：校园网、公司网、没有公网IP的环境。免费、即用。

#### 推荐工具：cpolar（国内，速度快）

1. **下载安装**：https://www.cpolar.com/
2. **注册账号，获取Authtoken**
3. **启动隧道**：
   ```bash
   cpolar http 8000
   ```
4. **得到公网地址**：
   例如 `https://xxxx.cpolar.top`
5. **外网直接访问**这个地址即可

#### 备选工具：ngrok

```bash
ngrok http 8000
```

会生成一个 `https://xxxx.ngrok.io` 的公网地址。

> 内网穿透的免费版每次重启地址会变，付费版可以固定域名。

---

## 九、常见问题

| 问题 | 解决方法 |
|---|---|
| 启动报错 MySQL 连接失败 | 检查 db.py 里的密码是否正确，MySQL 服务是否启动 |
| 局域网其他电脑打不开 | 检查防火墙是否放行 8000 端口（已自动添加） |
| 注册后没反应 | 确认 MySQL 服务正常，浏览器按 F12 看控制台报错 |
| 上传照片不显示 | 检查 static/uploads/ 目录是否存在 |
| 清空数据 | 运行 `python reset_db.py`，只保留管理员账号 |
