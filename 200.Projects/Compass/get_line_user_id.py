#!/usr/bin/env python3
"""
LINE Messaging API 用の「自分の User ID」を取得するための簡易 Webhook サーバーです。
1. このスクリプトを実行し、ngrok 等で HTTPS の URL を公開する
2. LINE 開発者コンソールで Webhook URL にその URL を設定
3. ボットを友だち追加して、トークでメッセージを1通送る
4. ターミナルに表示された User ID を LINE_USER_ID に設定する
"""

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8080


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # LINE の Webhook URL 検証用（検証時は 200 を返す）
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"success":true}')

        try:
            data = json.loads(body.decode("utf-8"))
            for event in data.get("events", []):
                src = event.get("source", {})
                uid = src.get("userId")
                if uid:
                    print(f"\n>>> あなたの LINE User ID: {uid}\n", file=sys.stderr, flush=True)
                    print(uid, flush=True)
        except Exception as e:
            print(f"Parse error: {e}", file=sys.stderr)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}", file=sys.stderr)


def main():
    print(f"Webhook 受付中 http://0.0.0.0:{PORT}", file=sys.stderr)
    print("ngrok 等で HTTPS 公開し、LINE の Webhook URL に設定してください。", file=sys.stderr)
    print("ボットにメッセージを送ると、このターミナルに User ID が表示されます。\n", file=sys.stderr)
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()
