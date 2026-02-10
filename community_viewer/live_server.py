"""
OASIS Community Viewer — 实时服务器

在持续模式 community_simulation.py --continuous 运行的同时启动此服务，
前端会自动轮询 /api/data 获取 SQLite 中最新数据，实现实时可视化。

用法:
    python live_server.py --db ../community_simulation.db --port 8001
"""

import argparse
import json
import os
import sqlite3
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from datetime import datetime
from urllib.parse import urlparse, parse_qs


def fetch_all(conn, query, params=None):
    cur = conn.cursor()
    cur.execute(query, params or [])
    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()
    return [dict(zip(cols, row)) for row in rows]


def build_payload(db_path, since_trace_id=0, since_post_id=0, since_comment_id=0,
                  limit_trace=500, full=False):
    """构建 JSON 数据。full=True 返回全量，否则返回增量。"""
    if not os.path.exists(db_path):
        return {"error": "db_not_found", "message": f"Database not found: {db_path}"}

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.execute("PRAGMA journal_mode=WAL")  # 允许并发读

    try:
        users = fetch_all(conn, "SELECT * FROM user ORDER BY user_id")
        user_map = {u["user_id"]: u for u in users}

        if full or (since_post_id == 0 and since_comment_id == 0):
            # 全量
            posts = fetch_all(conn, "SELECT * FROM post ORDER BY post_id")
            comments = fetch_all(conn, "SELECT * FROM comment ORDER BY comment_id")
            likes = fetch_all(conn, "SELECT * FROM 'like' ORDER BY like_id")
            dislikes = fetch_all(conn, "SELECT * FROM dislike ORDER BY dislike_id")
            follows = fetch_all(conn, "SELECT * FROM follow ORDER BY follow_id")
            trace = fetch_all(conn,
                              "SELECT * FROM trace ORDER BY created_at DESC LIMIT ?",
                              [limit_trace])
            is_incremental = False
        else:
            # 增量：只取新数据
            posts = fetch_all(conn,
                              "SELECT * FROM post WHERE post_id > ? ORDER BY post_id",
                              [since_post_id])
            comments = fetch_all(conn,
                                 "SELECT * FROM comment WHERE comment_id > ? ORDER BY comment_id",
                                 [since_comment_id])
            # likes/dislikes/follows 也取增量（用 like_id 等判断）
            likes = fetch_all(conn, "SELECT * FROM 'like' ORDER BY like_id")
            dislikes = fetch_all(conn, "SELECT * FROM dislike ORDER BY dislike_id")
            follows = fetch_all(conn, "SELECT * FROM follow ORDER BY follow_id")
            trace = fetch_all(conn,
                              "SELECT * FROM trace WHERE ROWID > ? ORDER BY created_at DESC LIMIT ?",
                              [since_trace_id, limit_trace])
            is_incremental = True

        # 构建 comment_map
        all_comments = fetch_all(conn, "SELECT * FROM comment ORDER BY comment_id")
        comment_map = {}
        for c in all_comments:
            comment_map.setdefault(c["post_id"], []).append(c)

        # 给帖子附加评论和用户信息
        cleaned_posts = []
        for post in posts:
            content = post.get("content")
            if content is None or str(content).strip() == "":
                continue
            post_comments = comment_map.get(post["post_id"], [])
            for c in post_comments:
                c["user"] = user_map.get(c["user_id"], {})
            post["comments"] = post_comments
            post["user"] = user_map.get(post["user_id"], {})
            cleaned_posts.append(post)

        # 统计
        total_posts = fetch_all(conn, "SELECT COUNT(*) as cnt FROM post")[0]["cnt"]
        total_comments = fetch_all(conn, "SELECT COUNT(*) as cnt FROM comment")[0]["cnt"]
        total_likes = fetch_all(conn, "SELECT COUNT(*) as cnt FROM 'like'")[0]["cnt"]
        total_dislikes = fetch_all(conn, "SELECT COUNT(*) as cnt FROM dislike")[0]["cnt"]
        total_follows = fetch_all(conn, "SELECT COUNT(*) as cnt FROM follow")[0]["cnt"]
        total_trace = fetch_all(conn, "SELECT COUNT(*) as cnt FROM trace")[0]["cnt"]

        stats = {
            "users": len(users),
            "posts": total_posts,
            "comments": total_comments,
            "likes": total_likes,
            "dislikes": total_dislikes,
            "follows": total_follows,
            "trace": total_trace,
        }

        # Action summary (全量)
        action_rows = fetch_all(conn,
                                "SELECT action, COUNT(*) as cnt FROM trace GROUP BY action")
        action_summary = {r["action"]: r["cnt"] for r in action_rows}

        # Per-user comment counts
        comment_rows = fetch_all(conn,
                                 "SELECT user_id, COUNT(*) as cnt FROM comment GROUP BY user_id")
        comments_by_user = {r["user_id"]: r["cnt"] for r in comment_rows}

        # Per-user like counts
        like_rows = fetch_all(conn,
                              "SELECT user_id, COUNT(*) as cnt FROM 'like' GROUP BY user_id")
        likes_by_user = {r["user_id"]: r["cnt"] for r in like_rows}

        # Per-user action breakdown
        action_detail = fetch_all(conn,
                                  "SELECT user_id, action, COUNT(*) as cnt FROM trace GROUP BY user_id, action")
        per_user_actions = {}
        for r in action_detail:
            per_user_actions.setdefault(r["user_id"], {})[r["action"]] = r["cnt"]

        # Top posts by comment count
        all_posts_full = fetch_all(conn, "SELECT * FROM post ORDER BY post_id")
        full_cleaned = []
        for post in all_posts_full:
            content = post.get("content")
            if content is None or str(content).strip() == "":
                continue
            post["comments"] = comment_map.get(post["post_id"], [])
            for c in post["comments"]:
                c["user"] = user_map.get(c["user_id"], {})
            post["user"] = user_map.get(post["user_id"], {})
            full_cleaned.append(post)

        top_posts = sorted(full_cleaned,
                           key=lambda p: len(p.get("comments", [])),
                           reverse=True)[:10]

        # Watermarks: 前端下次增量请求用
        max_post_id = fetch_all(conn,
                                "SELECT COALESCE(MAX(post_id),0) as v FROM post")[0]["v"]
        max_comment_id = fetch_all(conn,
                                   "SELECT COALESCE(MAX(comment_id),0) as v FROM comment")[0]["v"]
        max_trace_rowid = fetch_all(conn,
                                    "SELECT COALESCE(MAX(ROWID),0) as v FROM trace")[0]["v"]

        payload = {
            "meta": {
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "db_path": db_path,
                "is_live": True,
                "is_incremental": is_incremental,
            },
            "watermarks": {
                "post_id": max_post_id,
                "comment_id": max_comment_id,
                "trace_rowid": max_trace_rowid,
            },
            "stats": stats,
            "action_summary": action_summary,
            "users": users,
            "posts": cleaned_posts,
            "likes": likes,
            "dislikes": dislikes,
            "follows": follows,
            "trace": trace,
            "comments_by_user": comments_by_user,
            "likes_by_user": likes_by_user,
            "per_user_actions": per_user_actions,
            "top_posts": top_posts,
        }
        return payload

    finally:
        conn.close()


class LiveHandler(SimpleHTTPRequestHandler):
    """处理 API 请求和静态文件。"""

    db_path = ""

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/data":
            qs = parse_qs(parsed.query)
            since_post = int(qs.get("since_post_id", [0])[0])
            since_comment = int(qs.get("since_comment_id", [0])[0])
            since_trace = int(qs.get("since_trace_rowid", [0])[0])
            full = qs.get("full", ["0"])[0] == "1"

            payload = build_payload(
                self.db_path,
                since_trace_id=since_trace,
                since_post_id=since_post,
                since_comment_id=since_comment,
                full=full,
            )

            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", len(body))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store")
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/health":
            exists = os.path.exists(self.db_path)
            mtime = os.path.getmtime(self.db_path) if exists else 0
            body = json.dumps({
                "ok": exists,
                "db_path": self.db_path,
                "db_exists": exists,
                "db_mtime": mtime,
                "server_time": datetime.utcnow().isoformat() + "Z",
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(body)
            return

        # 默认：静态文件
        return super().do_GET()

    def log_message(self, format, *args):
        # 只打印非静态请求日志
        if "/api/" in str(args[0]):
            super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description="OASIS Community Viewer — 实时服务器")
    parser.add_argument("--db", default="../community_simulation.db",
                        help="SQLite 数据库路径")
    parser.add_argument("--port", type=int, default=8001,
                        help="HTTP 服务端口")
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)

    # 切换到 community_viewer 目录（静态文件根目录）
    viewer_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(viewer_dir)

    LiveHandler.db_path = db_path

    server = HTTPServer((args.host, args.port), LiveHandler)
    print(f"🌐 OASIS Live Viewer 启动")
    print(f"   数据库: {db_path}")
    print(f"   地址:   http://{args.host}:{args.port}")
    print(f"   API:    http://{args.host}:{args.port}/api/data")
    print(f"   Ctrl+C 停止")

    if not os.path.exists(db_path):
        print(f"⚠️  数据库尚不存在，等待 community_simulation.py 创建...")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止服务器")
        server.server_close()


if __name__ == "__main__":
    main()
