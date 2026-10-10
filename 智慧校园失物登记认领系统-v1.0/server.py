# -*- coding: utf-8 -*-
"""
基于原生 HTTP 的宿舍园区失物信息登记系统 - 后端服务器
====================================================
采用 Python 标准库 http.server 处理 HTTP 报文，
Cookie 维护登录会话,MySQL 存储业务数据。

启动:  python server.py
默认端口: 8000
"""
import json
import os
import re
import hashlib
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

import db

# ---------------- 配置 ----------------
PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 内存会话表: { session_id: user_id }
SESSIONS = {}

# 静态文件 MIME 类型
MIME = {
    ".html": "text/html; charset=utf-8",
    ".css":  "text/css; charset=utf-8",
    ".js":   "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".svg":  "image/svg+xml",
    ".ico":  "image/x-icon",
}


def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()


class Handler(BaseHTTPRequestHandler):
    # ---------- 基础工具 ----------
    def log_message(self, fmt, *args):
        # 简化日志
        print("[HTTP] %s - %s" % (self.address_string(), fmt % args))

    def _send_json(self, code, obj, extra_headers=None):
        body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            # 兼容表单提交
            form = parse_qs(raw)
            return {k: v[0] for k, v in form.items()}

    def _parse_cookies(self):
        cookie = self.headers.get("Cookie", "")
        jar = {}
        for part in cookie.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                jar[k] = v
        return jar

    def _current_user(self):
        """根据 Cookie 中的 SESSION_ID 返回用户 dict，未登录返回 None"""
        sid = self._parse_cookies().get("SESSION_ID")
        if not sid or sid not in SESSIONS:
            return None
        uid = SESSIONS[sid]
        return db.query_one("SELECT id,username,real_name,student_id,college,class_name,role,phone FROM users WHERE id=%s", (uid,))

    def _set_session_cookie(self, sid):
        return {"Set-Cookie": "SESSION_ID=%s; Path=/; HttpOnly; Max-Age=86400" % sid}

    def _clear_session_cookie(self):
        return {"Set-Cookie": "SESSION_ID=; Path=/; HttpOnly; Max-Age=0"}

    # ---------- GET 路由分发：页面数据查询 ----------
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        # ===== 用户相关：当前登录信息 =====
        if path == "/api/me":
            return self._api_me()

        # ===== 失物/招领列表与详情 =====
        if path == "/api/lost":
            return self._api_lost_list(qs)
        if path.startswith("/api/lost/"):
            return self._api_lost_detail(path.split("/")[-1])
        if path == "/api/found":
            return self._api_found_list(qs)
        if path.startswith("/api/found/"):
            return self._api_found_detail(path.split("/")[-1])

        # ===== 我的记录：个人发布与认领 =====
        if path == "/api/my/posts":
            return self._api_my_posts()
        if path == "/api/my/claims":
            return self._api_my_claims()

        # ===== 评论区 =====
        if path == "/api/comments":
            return self._api_comments_list(qs)

        # ===== 管理员后台 =====
        if path == "/api/admin/pending-items":
            return self._api_admin_pending_items()
        if path == "/api/admin/claims":
            return self._api_admin_claims()
        if path == "/api/admin/users":
            return self._api_admin_users()

        # ===== 静态文件 =====
        return self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
    # ---------- POST 路由分发：提交数据 ----------
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        # ===== 用户认证：注册、登录、退出 =====
        if path == "/api/register":
            return self._api_register(body)
        if path == "/api/login":
            return self._api_login(body)
        if path == "/api/logout":
            return self._api_logout()

        # ===== 发布失物/招领信息 =====
        if path == "/api/lost":
            return self._api_lost_create(body)
        if path == "/api/found":
            return self._api_found_create(body)

        # ===== 认领申请与图片上传 =====
        if path == "/api/claim":
            return self._api_claim_create(body)
        if path == "/api/upload":
            return self._api_upload(body)

        # ===== 发表评论 =====
        if path == "/api/comments":
            return self._api_comment_create(body)

        # ===== 用户确认领取/找回物品 =====
        if path == "/api/recover":
            return self._api_recover(body)

        self._send_json(404, {"error": "not found"})

    def do_PUT(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        # /api/admin/item/lost/5/status
        m = re.match(r"^/api/admin/item/(lost|found)/(\d+)/status$", path)
        if m:
            return self._api_admin_set_item_status(m.group(1), int(m.group(2)), body)
        # /api/admin/claim/3/status
        m = re.match(r"^/api/admin/claim/(\d+)/status$", path)
        if m:
            return self._api_admin_set_claim_status(int(m.group(1)), body)
        # /api/lost/5  (作者编辑)
        m = re.match(r"^/api/lost/(\d+)$", path)
        if m:
            return self._api_item_update("lost", int(m.group(1)), body)
        m = re.match(r"^/api/found/(\d+)$", path)
        if m:
            return self._api_item_update("found", int(m.group(1)), body)
        # /api/recover  (用户自己确认领取/找回物品)
        if path == "/api/recover":
            return self._api_recover(body)

        self._send_json(404, {"error": "not found"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        m = re.match(r"^/api/lost/(\d+)$", path)
        if m:
            return self._api_item_delete("lost", int(m.group(1)))
        m = re.match(r"^/api/found/(\d+)$", path)
        if m:
            return self._api_item_delete("found", int(m.group(1)))
        self._send_json(404, {"error": "not found"})

    # ---------- 静态文件 ----------
    def _serve_static(self, path):
        if path == "/":
            path = "/index.html"
        if path.startswith("/uploads/"):
            full = os.path.normpath(os.path.join(UPLOAD_DIR, path[len("/uploads/"):]))
            if not full.startswith(UPLOAD_DIR):
                self._send_json(403, {"error": "forbidden"})
                return
        else:
            full = os.path.normpath(os.path.join(STATIC_DIR, path.lstrip("/")))
            if not full.startswith(STATIC_DIR):
                self._send_json(403, {"error": "forbidden"})
                return
        if os.path.isdir(full):
            full = os.path.join(full, "index.html")
        if not os.path.isfile(full):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("404 Not Found".encode("utf-8"))
            return
        ext = os.path.splitext(full)[1].lower()
        ctype = MIME.get(ext, "application/octet-stream")
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ================================================================
    #  API 实现
    # ================================================================

    # ---- 认证 ----
    def _api_register(self, b):
        username = (b.get("username") or "").strip()
        password = b.get("password") or ""
        real_name = (b.get("real_name") or "").strip()
        student_id = (b.get("student_id") or "").strip()
        college = (b.get("college") or "").strip()
        class_name = (b.get("class_name") or "").strip()
        phone = (b.get("phone") or "").strip()
        if not username or not password:
            return self._send_json(400, {"error": "账号和密码不能为空"})
        if len(password) < 6:
            return self._send_json(400, {"error": "密码至少6位"})
        if not real_name:
            return self._send_json(400, {"error": "请填写真实姓名"})
        exist = db.query_one("SELECT id FROM users WHERE username=%s", (username,))
        if exist:
            return self._send_json(400, {"error": "该账号已被注册"})
        uid = db.execute(
            "INSERT INTO users(username,password_hash,real_name,student_id,college,class_name,phone,role) VALUES(%s,%s,%s,%s,%s,%s,%s,'user')",
            (username, hash_password(password), real_name, student_id, college, class_name, phone),
        )
        # 注册成功后自动登录，直接设置会话Cookie
        sid = secrets.token_hex(16)
        SESSIONS[sid] = uid
        return self._send_json(200, {"ok": True, "user_id": uid}, self._set_session_cookie(sid))

    def _api_login(self, b):
        username = (b.get("username") or "").strip()
        password = b.get("password") or ""
        row = db.query_one(
            "SELECT id,username,password_hash,role FROM users WHERE username=%s",
            (username,),
        )
        if not row or row["password_hash"] != hash_password(password or ""):
            return self._send_json(401, {"error": "账号或密码错误"})
        sid = secrets.token_hex(16)
        SESSIONS[sid] = row["id"]
        return self._send_json(
            200,
            {"ok": True, "role": row["role"]},
            extra_headers=self._set_session_cookie(sid),
        )

    def _api_logout(self):
        sid = self._parse_cookies().get("SESSION_ID")
        if sid in SESSIONS:
            del SESSIONS[sid]
        return self._send_json(200, {"ok": True}, extra_headers=self._clear_session_cookie())

    def _api_me(self):
        u = self._current_user()
        if not u:
            return self._send_json(200, {"user": None})
        return self._send_json(200, {"user": u})

    # ---- 失物 ----
    def _api_lost_list(self, qs):
        where = ["status='approved'"]
        params = []
        kw = (qs.get("kw") or [""])[0].strip()
        cat = (qs.get("category") or [""])[0].strip()
        if kw:
            where.append("(title LIKE %s OR description LIKE %s OR location_lost LIKE %s)")
            like = "%" + kw + "%"
            params += [like, like, like]
        if cat:
            where.append("category=%s")
            params.append(cat)
        sql = """SELECT l.*, u.real_name AS publisher_name
                 FROM lost_items l JOIN users u ON u.id=l.user_id
                 WHERE %s ORDER BY l.created_at DESC""" % " AND ".join(where)
        rows = db.query_all(sql, tuple(params))
        return self._send_json(200, {"list": rows})

    def _api_lost_detail(self, item_id):
        if not item_id.isdigit():
            return self._send_json(400, {"error": "bad id"})
        row = db.query_one(
            """SELECT l.*, u.real_name AS publisher_name
               FROM lost_items l JOIN users u ON u.id=l.user_id
               WHERE l.id=%s""",
            (int(item_id),),
        )
        if not row:
            return self._send_json(404, {"error": "not found"})
        return self._send_json(200, {"item": row})

    def _api_lost_create(self, b):
        u = self._current_user()
        if not u:
            return self._send_json(401, {"error": "请先登录"})
        title = (b.get("title") or "").strip()
        if not title:
            return self._send_json(400, {"error": "标题不能为空"})
        item_id = db.execute(
            """INSERT INTO lost_items(user_id,title,description,category,location_lost,time_lost,contact,image_path)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                u["id"],
                title,
                b.get("description") or "",
                b.get("category") or "其他",
                b.get("location_lost") or "",
                b.get("time_lost") or None,
                b.get("contact") or u.get("phone") or "",
                b.get("image_path") or None,
            ),
        )
        return self._send_json(200, {"ok": True, "id": item_id})

    # ---- 招领 ----
    def _api_found_list(self, qs):
        where = ["status='approved'"]
        params = []
        kw = (qs.get("kw") or [""])[0].strip()
        cat = (qs.get("category") or [""])[0].strip()
        if kw:
            where.append("(title LIKE %s OR description LIKE %s OR location_found LIKE %s)")
            like = "%" + kw + "%"
            params += [like, like, like]
        if cat:
            where.append("category=%s")
            params.append(cat)
        sql = """SELECT f.*, u.real_name AS publisher_name
                 FROM found_items f JOIN users u ON u.id=f.user_id
                 WHERE %s ORDER BY f.created_at DESC""" % " AND ".join(where)
        rows = db.query_all(sql, tuple(params))
        return self._send_json(200, {"list": rows})

    def _api_found_detail(self, item_id):
        if not item_id.isdigit():
            return self._send_json(400, {"error": "bad id"})
        row = db.query_one(
            """SELECT f.*, u.real_name AS publisher_name
               FROM found_items f JOIN users u ON u.id=f.user_id
               WHERE f.id=%s""",
            (int(item_id),),
        )
        if not row:
            return self._send_json(404, {"error": "not found"})
        return self._send_json(200, {"item": row})

    def _api_found_create(self, b):
        u = self._current_user()
        if not u:
            return self._send_json(401, {"error": "请先登录"})
        title = (b.get("title") or "").strip()
        if not title:
            return self._send_json(400, {"error": "标题不能为空"})
        item_id = db.execute(
            """INSERT INTO found_items(user_id,title,description,category,location_found,time_found,contact,image_path)
               VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                u["id"],
                title,
                b.get("description") or "",
                b.get("category") or "其他",
                b.get("location_found") or "",
                b.get("time_found") or None,
                b.get("contact") or u.get("phone") or "",
                b.get("image_path") or None,
            ),
        )
        return self._send_json(200, {"ok": True, "id": item_id})

    # ---- 编辑/删除 (作者本人或管理员) ----
    def _api_item_update(self, kind, item_id, b):
        u = self._current_user()
        if not u:
            return self._send_json(401, {"error": "请先登录"})
        table = "lost_items" if kind == "lost" else "found_items"
        row = db.query_one("SELECT user_id FROM %s WHERE id=%%s" % table, (item_id,))
        if not row:
            return self._send_json(404, {"error": "not found"})
        if row["user_id"] != u["id"] and u["role"] != "admin":
            return self._send_json(403, {"error": "无权修改"})
        fields = []
        params = []
        for k in ["title", "description", "category", "contact"]:
            if k in b:
                fields.append("%s=%%s" % k)
                params.append(b[k])
        if "location_lost" in b and kind == "lost":
            fields.append("location_lost=%s")
            params.append(b["location_lost"])
        if "location_found" in b and kind == "found":
            fields.append("location_found=%s")
            params.append(b["location_found"])
        if not fields:
            return self._send_json(200, {"ok": True})
        params.append(item_id)
        db.execute("UPDATE %s SET %s WHERE id=%%s" % (table, ",".join(fields)), tuple(params))
        return self._send_json(200, {"ok": True})

    def _api_recover(self, b):
        u = self._current_user()
        if not u:
            return self._send_json(401, {"error": "请先登录"})
        item_type = b.get("item_type", "lost")
        item_id = b.get("item_id")
        if not item_id:
            return self._send_json(400, {"error": "缺少物品ID"})
        table = "lost_items" if item_type == "lost" else "found_items"
        row = db.query_one("SELECT user_id FROM %s WHERE id=%%s" % table, (int(item_id),))
        if not row:
            return self._send_json(404, {"error": "物品不存在"})
        db.execute("UPDATE %s SET status='claimed' WHERE id=%%s" % table, (int(item_id),))
        return self._send_json(200, {"ok": True})

    def _api_item_delete(self, kind, item_id):
        u = self._current_user()
        if not u:
            return self._send_json(401, {"error": "请先登录"})
        table = "lost_items" if kind == "lost" else "found_items"
        row = db.query_one("SELECT user_id FROM %s WHERE id=%%s" % table, (item_id,))
        if not row:
            return self._send_json(404, {"error": "not found"})
        if row["user_id"] != u["id"] and u["role"] != "admin":
            return self._send_json(403, {"error": "无权删除"})
        db.execute("DELETE FROM %s WHERE id=%%s" % table, (item_id,))
        return self._send_json(200, {"ok": True})

    # ---- 我的 ----
    def _api_my_posts(self):
        u = self._current_user()
        if not u:
            return self._send_json(401, {"error": "请先登录"})
        lost = db.query_all("SELECT * FROM lost_items WHERE user_id=%s ORDER BY created_at DESC", (u["id"],))
        found = db.query_all("SELECT * FROM found_items WHERE user_id=%s ORDER BY created_at DESC", (u["id"],))
        return self._send_json(200, {"lost": lost, "found": found})

    def _api_my_claims(self):
        u = self._current_user()
        if not u:
            return self._send_json(401, {"error": "请先登录"})
        rows = db.query_all(
            """SELECT c.*, f.title AS item_title, f.location_found, f.time_found
               FROM claim_records c
               LEFT JOIN found_items f ON f.id=c.item_id
               WHERE c.claimer_id=%s ORDER BY c.created_at DESC""",
            (u["id"],),
        )
        return self._send_json(200, {"list": rows})

    # ---- 认领申请 ----
    def _api_claim_create(self, b):
        u = self._current_user()
        if not u:
            return self._send_json(401, {"error": "请先登录"})
        item_id = b.get("item_id")
        item_type = b.get("item_type", "found")
        reason = (b.get("claim_reason") or "").strip()
        if not item_id or not reason:
            return self._send_json(400, {"error": "请填写认领理由/物品特征"})
        # 只能对已通过的招领/失物发起认领
        table = "found_items" if item_type == "found" else "lost_items"
        item = db.query_one("SELECT id,user_id,status FROM %s WHERE id=%%s" % table, (int(item_id),))
        if not item:
            return self._send_json(404, {"error": "物品不存在"})
        if item["status"] != "approved":
            return self._send_json(400, {"error": "该物品尚未通过审核，无法认领"})
        if item["user_id"] == u["id"]:
            return self._send_json(400, {"error": "不能认领自己发布的物品"})
        cid = db.execute(
            "INSERT INTO claim_records(claimer_id,item_type,item_id,claim_reason) VALUES(%s,%s,%s,%s)",
            (u["id"], item_type, int(item_id), reason),
        )
        return self._send_json(200, {"ok": True, "id": cid})

    def _api_upload(self, b):
        u = self._current_user()
        if not u:
            return self._send_json(401, {"error": "请先登录"})
        data_url = b.get("image") or ""
        if not data_url.startswith("data:image/"):
            return self._send_json(400, {"error": "图片格式错误"})
        try:
            header, encoded = data_url.split(",", 1)
            ext = "jpg"
            if "png" in header: ext = "png"
            elif "webp" in header: ext = "webp"
            import base64
            raw = base64.b64decode(encoded)
            if len(raw) > 5 * 1024 * 1024:
                return self._send_json(400, {"error": "图片不能超过5MB"})
            fname = secrets.token_hex(8) + "." + ext
            fpath = os.path.join(UPLOAD_DIR, fname)
            with open(fpath, "wb") as f:
                f.write(raw)
            return self._send_json(200, {"ok": True, "path": "/uploads/" + fname})
        except Exception as e:
            return self._send_json(500, {"error": "上传失败: " + str(e)})

    def _api_comments_list(self, qs):
        item_type = (qs.get("type") or ["lost"])[0]
        item_id = (qs.get("item_id") or ["0"])[0]
        if not item_id.isdigit():
            return self._send_json(400, {"error": "bad item_id"})
        rows = db.query_all(
            """SELECT c.*, u.real_name, u.username
               FROM comments c JOIN users u ON u.id=c.user_id
               WHERE c.item_type=%s AND c.item_id=%s
               ORDER BY c.created_at ASC""",
            (item_type, int(item_id)),
        )
        return self._send_json(200, {"list": rows})

    def _api_comment_create(self, b):
        u = self._current_user()
        if not u:
            return self._send_json(401, {"error": "请先登录后留言"})
        item_type = b.get("item_type", "lost")
        item_id = b.get("item_id")
        content = (b.get("content") or "").strip()
        if not item_id or not content:
            return self._send_json(400, {"error": "留言内容不能为空"})
        if len(content) > 500:
            return self._send_json(400, {"error": "留言不能超过500字"})
        cid = db.execute(
            "INSERT INTO comments(item_type,item_id,user_id,content) VALUES(%s,%s,%s,%s)",
            (item_type, int(item_id), u["id"], content),
        )
        return self._send_json(200, {"ok": True, "id": cid})

    # ---- 管理员 ----
    def _require_admin(self):
        u = self._current_user()
        if not u:
            self._send_json(401, {"error": "请先登录"})
            return None
        if u["role"] != "admin":
            self._send_json(403, {"error": "需要管理员权限"})
            return None
        return u

    def _api_admin_pending_items(self):
        if not self._require_admin():
            return
        lost = db.query_all(
            """SELECT l.*, u.real_name AS publisher_name FROM lost_items l
               JOIN users u ON u.id=l.user_id WHERE l.status='pending'
               ORDER BY l.created_at DESC"""
        )
        found = db.query_all(
            """SELECT f.*, u.real_name AS publisher_name FROM found_items f
               JOIN users u ON u.id=f.user_id WHERE f.status='pending'
               ORDER BY f.created_at DESC"""
        )
        return self._send_json(200, {"lost": lost, "found": found})

    def _api_admin_set_item_status(self, kind, item_id, b):
        if not self._require_admin():
            return
        status = b.get("status")
        if status not in ("approved", "rejected", "claimed", "pending"):
            return self._send_json(400, {"error": "bad status"})
        table = "lost_items" if kind == "lost" else "found_items"
        db.execute("UPDATE %s SET status=%%s WHERE id=%%s" % table, (status, item_id))
        return self._send_json(200, {"ok": True})

    def _api_admin_claims(self):
        if not self._require_admin():
            return
        rows = db.query_all(
            """SELECT c.*, u.real_name AS claimer_name, u.phone AS claimer_phone,
                      f.title AS item_title, f.location_found, f.time_found, f.contact
               FROM claim_records c
               JOIN users u ON u.id=c.claimer_id
               LEFT JOIN found_items f ON f.id=c.item_id
               ORDER BY (c.status='pending') DESC, c.created_at DESC"""
        )
        return self._send_json(200, {"list": rows})

    def _api_admin_set_claim_status(self, claim_id, b):
        admin = self._require_admin()
        if not admin:
            return
        status = b.get("status")
        if status not in ("approved", "rejected"):
            return self._send_json(400, {"error": "bad status"})
        rec = db.query_one("SELECT item_type,item_id FROM claim_records WHERE id=%s", (claim_id,))
        if not rec:
            return self._send_json(404, {"error": "not found"})
        db.execute(
            "UPDATE claim_records SET status=%s, admin_id=%s, processed_at=NOW() WHERE id=%s",
            (status, admin["id"], claim_id),
        )
        # 若认领通过,把对应物品标记为已认领
        if status == "approved":
            table = "found_items" if rec["item_type"] == "found" else "lost_items"
            db.execute("UPDATE %s SET status='claimed' WHERE id=%%s" % table, (rec["item_id"],))
        return self._send_json(200, {"ok": True})

    def _api_admin_users(self):
        if not self._require_admin():
            return
        rows = db.query_all(
            "SELECT id,username,real_name,role,phone,created_at FROM users ORDER BY id"
        )
        return self._send_json(200, {"list": rows})


def main():
    import socket
    # 获取本机局域网IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        lan_ip = "127.0.0.1"
    print("=" * 60)
    print(" 智慧校园失物登记认领系统 后端启动中...")
    print(" 本机访问:   http://127.0.0.1:%d" % PORT)
    print(" 局域网访问: http://%s:%d" % (lan_ip, PORT))
    print(" 管理员账号: admin / admin123")
    print("=" * 60)
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")


if __name__ == "__main__":
    main()
