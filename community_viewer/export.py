import argparse
import json
import os
import sqlite3
from datetime import datetime


def fetch_all(conn, query, params=None):
    cur = conn.cursor()
    cur.execute(query, params or [])
    cols = [c[0] for c in cur.description]
    rows = cur.fetchall()
    return [dict(zip(cols, row)) for row in rows]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="../community_simulation.db")
    parser.add_argument("--out", default="./data.json")
    parser.add_argument("--limit-trace", type=int, default=1000)
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    out_path = os.path.abspath(args.out)

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"DB not found: {db_path}")

    conn = sqlite3.connect(db_path)

    users = fetch_all(conn, "SELECT * FROM user ORDER BY user_id")
    posts = fetch_all(conn, "SELECT * FROM post ORDER BY post_id")
    comments = fetch_all(conn, "SELECT * FROM comment ORDER BY comment_id")
    likes = fetch_all(conn, "SELECT * FROM 'like' ORDER BY like_id")
    dislikes = fetch_all(conn, "SELECT * FROM dislike ORDER BY dislike_id")
    follows = fetch_all(conn, "SELECT * FROM follow ORDER BY follow_id")
    trace = fetch_all(conn, "SELECT * FROM trace ORDER BY created_at DESC LIMIT ?", [args.limit_trace])

    # Build lookup maps
    user_map = {u["user_id"]: u for u in users}

    # Attach comments to posts
    comment_map = {}
    for c in comments:
        comment_map.setdefault(c["post_id"], []).append(c)

    cleaned_posts = []
    for post in posts:
        content = post.get("content")
        if content is None or str(content).strip() == "":
            continue
        post_comments = comment_map.get(post["post_id"], [])
        # attach user info
        for c in post_comments:
            c["user"] = user_map.get(c["user_id"], {})
        post["comments"] = post_comments
        post["user"] = user_map.get(post["user_id"], {})
        cleaned_posts.append(post)

    # Stats
    stats = {
        "users": len(users),
        "posts": len(cleaned_posts),
        "comments": len(comments),
        "likes": len(likes),
        "dislikes": len(dislikes),
        "follows": len(follows),
        "trace": len(trace),
    }

    # Action summary
    action_summary = {}
    for t in trace:
        action_summary[t["action"]] = action_summary.get(t["action"], 0) + 1

    # Per-user summaries
    comments_by_user = {}
    for c in comments:
        comments_by_user[c["user_id"]] = comments_by_user.get(c["user_id"], 0) + 1

    likes_by_user = {}
    for l in likes:
        likes_by_user[l["user_id"]] = likes_by_user.get(l["user_id"], 0) + 1

    actions_by_user = {}
    for t in trace:
        key = (t["user_id"], t["action"])
        actions_by_user[key] = actions_by_user.get(key, 0) + 1

    per_user_actions = {}
    for (uid, action), n in actions_by_user.items():
        per_user_actions.setdefault(uid, {})[action] = n

    # Top posts by comments
    top_posts = sorted(
        cleaned_posts,
        key=lambda p: len(p.get("comments", [])),
        reverse=True,
    )[:10]

    payload = {
        "meta": {
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "db_path": db_path,
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

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
