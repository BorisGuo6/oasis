"""
示例外部 Agent HTTP 服务

这个脚本启动一个 HTTP 服务器，模拟一个外部 Agent。
每轮 Platform 会 POST 调用 /act 端点，发送当前 feed，
外部 Agent 返回要执行的操作列表。

用法:
    python example_external_agent.py [--port 5001]

然后启动社区模拟时指定:
    python community_simulation.py --external-agents http://localhost:5001/act ...
"""

import argparse
import json
import random
from http.server import HTTPServer, BaseHTTPRequestHandler


class ExternalAgentHandler(BaseHTTPRequestHandler):
    """处理来自 OASIS Platform 的 HTTP 请求。"""

    def do_POST(self):
        if self.path != "/act":
            self.send_response(404)
            self.end_headers()
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        payload = json.loads(body)

        agent_id = payload.get("agent_id", "?")
        feed = payload.get("feed", {})
        round_num = payload.get("round", 0)
        num_followers = payload.get("num_followers", 0)
        num_followings = payload.get("num_followings", 0)
        groups = payload.get("groups", {})
        posts = feed.get("posts", []) if feed.get("success") else []

        print(f"\n[轮次 {round_num}] Agent {agent_id} "
              f"粉丝={num_followers} 关注={num_followings} "
              f"帖子={len(posts)} 群组={len(groups.get('joined_groups', []))}")

        # ── 决策逻辑（示例：简单规则） ──
        actions = self.decide(posts, round_num)

        print(f"  -> 返回 {len(actions)} 个操作: "
              f"{[a['action'] for a in actions]}")

        response = json.dumps({"actions": actions})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(response.encode())

    def decide(self, posts, round_num):
        """
        示例决策逻辑。你可以替换成任意逻辑：
        - 调用你自己的 LLM
        - 基于规则引擎
        - 机器学习模型
        - 甚至是人工输入
        """
        actions = []

        # 策略1: 每轮发一条帖子
        if round_num % 2 == 0:
            actions.append({
                "action": "create_post",
                "args": {"content": f"[外部Agent] 轮次 {round_num} 的思考: "
                                    f"今天看到了 {len(posts)} 条帖子，社区很活跃！"}
            })

        # 策略2: 随机点赞看到的帖子
        if posts:
            post = random.choice(posts)
            actions.append({
                "action": "like_post",
                "args": {"post_id": post["post_id"]}
            })

        # 策略3: 对第一条帖子评论
        if posts and round_num % 3 == 0:
            actions.append({
                "action": "create_comment",
                "args": {
                    "post_id": posts[0]["post_id"],
                    "content": f"[外部Agent评论] 关于: {posts[0]['content'][:50]}..."
                }
            })

        # 如果没有任何操作，返回 do_nothing
        if not actions:
            actions.append({"action": "do_nothing", "args": {}})

        return actions

    def log_message(self, format, *args):
        """抑制默认的 HTTP 日志输出。"""
        pass


def main():
    parser = argparse.ArgumentParser(description="示例外部 Agent HTTP 服务")
    parser.add_argument("--port", type=int, default=5001, help="监听端口")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), ExternalAgentHandler)
    print(f"🤖 外部 Agent HTTP 服务已启动: http://{args.host}:{args.port}/act")
    print(f"   OASIS 连接方式: --external-agents http://localhost:{args.port}/act")
    print(f"   Ctrl+C 退出")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n外部 Agent 已退出")
        server.server_close()


if __name__ == "__main__":
    main()
