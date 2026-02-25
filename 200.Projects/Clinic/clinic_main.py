import os
import sys
from playwright.sync_api import sync_playwright

def _log(msg):
    print(msg, file=sys.stderr, flush=True)

def test_codmon():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # iPhoneとして認識させてアクセスします
        context = browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        )
        page = context.new_page()
        
        try:
            _log("1. コドモンにアクセス開始...")
            page.goto("https://parents.codmon.com/", wait_until="networkidle", timeout=60000)
            
            # 画面がしっかり出るまで少し待機
            page.wait_for_timeout(5000)
            
            # 【重要】現在の画面を「screenshot.png」として保存
            page.screenshot(path="screenshot.png")
            _log("📸 スクリーンショットを保存しました。")
            
            # ページ内のテキストを細かくチェック
            content = page.inner_text("body")
            _log(f"ページの内容(抜粋): {content[:200]}")
            
            if "ログイン" in content or "ID" in content or "パスワード" in content:
                _log("✅ ログイン画面を検知しました！")
            else:
                _log("⚠️ ログインボタンが見当たりません。画像を確認してください。")
                
        except Exception as e:
            _log(f"❌ エラー発生: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    test_codmon()
    # import os
# import re
# import sys
# import requests
# from datetime import datetime, timedelta
# from typing import Tuple
# from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# CLINIC_URL = "https://matsumotowomens.reserve.ne.jp/sp/index.php"
# LINE_PUSH_API = "https://api.line.me/v2/bot/message/push"

# def get_check_date() -> str:
#     s = os.environ.get("CHECK_DATE", "").strip()
#     if s:
#         try:
#             datetime.strptime(s, "%Y-%m-%d")
#             return s
#         except ValueError: pass
#     return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

# def send_line_message(token, user_id, message):
#     if not token or not user_id: return False
#     try:
#         r = requests.post(LINE_PUSH_API,
#             headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
#             json={"to": user_id, "messages": [{"type": "text", "text": message}]}, timeout=10)
#         return r.status_code == 200
#     except: return False

# def _log(msg):
#     print(msg, file=sys.stderr, flush=True)

# def check_clinic_availability(target_date: str) -> Tuple[bool, str]:
#     with sync_playwright() as p:
#         # 日本国内の公開プロキシサーバーを経由する設定を追加
#         # ※もし以下のプロキシが繋がらない場合は、別の日本のIPを探して差し替えます
#         browser = p.chromium.launch(
#             headless=True,
#             proxy={
#                 "server": "http://219.100.37.245:443" # 筑波大学のVPN Gateプロジェクトなどの比較的安定した日本のIP（例）
#             }
#         )
#         context = browser.new_context(user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1")
#         page = context.new_page()
#         try:
#             _log("1. トップページを開いています...")
#             page.goto(CLINIC_URL, wait_until="domcontentloaded", timeout=30000)
#             page.wait_for_timeout(2000)

#             _log("2. ページの読み込みを確認中...")
#             page.wait_for_timeout(5000) # 念のため5秒待つ
            
#             # 【重要】今見ている画面を画像として保存します（ActionsのSummaryで確認可能）
#             page.screenshot(path="error_debug.png")
#             _log("   デバッグ用スクリーンショットを保存しました。")

#             # ページ内のテキストをログに出して、何が表示されているか確認
#             content = page.inner_text("body")
#             _log(f"ページ内のテキスト（先頭100文字）: {content[:100]}...")

#             # 以前のソースに基づき、一番確実な方法でクリックを試みる
#             target = page.locator("li.nextpage").filter(has_text="再診(婦人科)").first
            
#             # JavaScriptでクリックを実行
#             target.evaluate("node => node.click()")
#             _log("   クリック命令を送信しました。")
#             page.wait_for_timeout(3000)

#             _log("3. 『次へ』ボタンをクリックします...")
#             next_btn = page.locator("input[type='submit'], button, a").filter(has_text=re.compile(r"次へ")).first
#             next_btn.click()
#             page.wait_for_load_state("networkidle")
#             page.wait_for_timeout(3000)
            
#             _log(f"4. {target_date} の空きを確認中...")
#             _, m, d = target_date.split("-")
#             short_date = f"{int(m)}/{int(d)}" 

#             day_cell = page.locator("td, .calendar_day, li").filter(has_text=re.compile(rf"^{int(d)}$|{short_date}")).first
#             if day_cell.count() > 0:
#                 cell_text = day_cell.inner_text().replace("\n", " ")
#                 _log(f"検知したセル情報: {cell_text}")
#                 if any(mark in cell_text for mark in ["○", "◯", "△", "予約", "空き"]):
#                     if "×" not in cell_text and "満" not in cell_text:
#                         return True, f"【空きあり】{target_date} 付近に予約可能な枠があります！"
#             return False, f"{target_date} は空きが見つかりませんでした。"
#         except Exception as e:
#             return False, f"エラー: {e}"
#         finally:
#             browser.close()

# def main():
#     target_date = get_check_date()
#     token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
#     user = os.environ.get("LINE_USER_ID", "").strip()
#     _log(f"--- クリニック空きチェック開始 ({target_date}) ---")
#     success, detail = check_clinic_availability(target_date)
#     _log(detail)
#     if success:
#         send_line_message(token, user, f"🏥 クリニック空き情報\n{detail}\n{CLINIC_URL}")

# if __name__ == "__main__":
#     main()
