import os
import re
import sys
import requests
from datetime import datetime, timedelta
from typing import Tuple
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

CLINIC_URL = "https://matsumotowomens.reserve.ne.jp/sp/index.php"
LINE_PUSH_API = "https://api.line.me/v2/bot/message/push"

def get_check_date() -> str:
    s = os.environ.get("CHECK_DATE", "").strip()
    if s:
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except ValueError: pass
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

def send_line_message(token, user_id, message):
    if not token or not user_id: return False
    try:
        r = requests.post(LINE_PUSH_API,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            json={"to": user_id, "messages": [{"type": "text", "text": message}]}, timeout=10)
        return r.status_code == 200
    except: return False

def _log(msg):
    print(msg, file=sys.stderr, flush=True)

def check_clinic_availability(target_date: str) -> Tuple[bool, str]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1")
        page = context.new_page()
        try:
            _log("1. トップページを開いています...")
            page.goto(CLINIC_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            _log("2. 『再診(婦人科)』ボタンを探しています...")
            # 文字が含まれている要素をより広く探す
            reishin_btn = page.locator("a, button, input, div.btn").filter(has_text="再診").filter(has_text="婦人科").first
            
            # もし上記で見つからない場合の予備（「再診」だけで探す）
            if reishin_btn.count() == 0:
                _log("   条件を緩めて『再診』ボタンを探します...")
                reishin_btn = page.get_by_role("button", name=re.compile(r"再診")).first

            reishin_btn.click()
            _log("   クリック成功！")
            page.wait_for_timeout(2000)

            _log("3. 『次へ』ボタンをクリックします...")
            next_btn = page.locator("input[type='submit'], button, a").filter(has_text=re.compile(r"次へ")).first
            next_btn.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)
            
            _log(f"4. {target_date} の空きを確認中...")
            _, m, d = target_date.split("-")
            short_date = f"{int(m)}/{int(d)}" 

            day_cell = page.locator("td, .calendar_day, li").filter(has_text=re.compile(rf"^{int(d)}$|{short_date}")).first
            if day_cell.count() > 0:
                cell_text = day_cell.inner_text().replace("\n", " ")
                _log(f"検知したセル情報: {cell_text}")
                if any(mark in cell_text for mark in ["○", "◯", "△", "予約", "空き"]):
                    if "×" not in cell_text and "満" not in cell_text:
                        return True, f"【空きあり】{target_date} 付近に予約可能な枠があります！"
            return False, f"{target_date} は空きが見つかりませんでした。"
        except Exception as e:
            return False, f"エラー: {e}"
        finally:
            browser.close()

def main():
    target_date = get_check_date()
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    user = os.environ.get("LINE_USER_ID", "").strip()
    _log(f"--- クリニック空きチェック開始 ({target_date}) ---")
    success, detail = check_clinic_availability(target_date)
    _log(detail)
    if success:
        send_line_message(token, user, f"🏥 クリニック空き情報\n{detail}\n{CLINIC_URL}")

if __name__ == "__main__":
    main()
