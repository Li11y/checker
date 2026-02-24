#!/usr/bin/env python3
"""
国立科学博物館コンパス（ART PASS）の空き状況を監視し、
指定日付に空きがあれば LINE または Gmail で通知する。
"""

import os
import re
import smtplib
import sys
from email.mime.text import MIMEText
from email.utils import formatdate
from datetime import datetime, timedelta
from typing import Tuple

import requests
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


COMPASS_URL = "https://art-ap.passes.jp/user/e/compass/tickets"
LINE_PUSH_API = "https://api.line.me/v2/bot/message/push"


def get_check_date() -> str:
    """環境変数 CHECK_DATE (YYYY-MM-DD) または明日の日付を返す。"""
    s = os.environ.get("CHECK_DATE", "").strip()
    if s:
        try:
            datetime.strptime(s, "%Y-%m-%d")
            return s
        except ValueError:
            pass
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return tomorrow


def send_line_message(channel_token: str, user_id: str, message: str) -> bool:
    """LINE Messaging API でプッシュメッセージを送信する。"""
    if not channel_token or not user_id:
        return False
    try:
        r = requests.post(
            LINE_PUSH_API,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {channel_token}",
            },
            json={
                "to": user_id,
                "messages": [{"type": "text", "text": message}],
            },
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def send_gmail(to_email: str, from_email: str, app_password: str, subject: str, body: str) -> bool:
    """Gmail SMTP でメールを送信する（Google のアプリパスワードを使用）。"""
    if not all([to_email, from_email, app_password]):
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        msg["Date"] = formatdate(localtime=True)
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
            smtp.login(from_email, app_password)
            smtp.sendmail(from_email, [to_email], msg.as_string())
        return True
    except Exception:
        return False


def _log(msg: str) -> None:
    """進行ログ（stderr に出すので標準出力と分離）"""
    print(msg, file=sys.stderr, flush=True)


def check_availability(target_date: str) -> Tuple[bool, str]:
    """
    Playwright でコンパスページを開き、指定日に空きがあるか判定する。
    戻り値: (空きありか, 判定の説明メッセージ)
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="ja-JP",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        try:
            _log("ページを開いています...")
            # networkidle は SPA で永遠に待つことがあるので domcontentloaded に
            page.goto(COMPASS_URL, wait_until="domcontentloaded", timeout=20000)
        except PlaywrightTimeout:
            browser.close()
            return False, "ページの読み込みがタイムアウトしました"
        except Exception as e:
            browser.close()
            return False, f"ページを開けませんでした: {e}"

        page.wait_for_timeout(4000)
        _log("カレンダーを確認しています...")

        year, month, day_part = target_date.split("-")
        month_int = int(month)
        year_int = int(year)
        day_num = day_part.lstrip("0") or "0"
        target_month_label = f"{year}年{month}月"
        target_month_label_alt = f"{year}年{month_int}月"

        def get_calendar_text() -> str:
            """カレンダー周辺のテキストを取得（body だと他と混ざるので候補を試す）"""
            for selector in [
                "[class*='calendar']", "[class*='Calendar']", "[role='application']",
                "text=入場日を選びます",
            ]:
                try:
                    el = page.locator(selector).first
                    if el.count() > 0:
                        return (el.inner_text() or "") + " " + (page.inner_text("body") or "")
                except Exception:
                    pass
            return page.inner_text("body") or ""

        page_text = get_calendar_text()
        max_clicks = 24
        for _ in range(max_clicks):
            if target_month_label in page_text or target_month_label_alt in page_text:
                _log(f"対象月 {target_date[:7]} を表示しました。")
                break
            try:
                match = re.search(r"(\d{4})年(\d{1,2})月", page_text)
                if match:
                    cur_y, cur_m = int(match.group(1)), int(match.group(2))
                    if (cur_y, cur_m) < (year_int, month_int):
                        # 次月へ（disabled でないボタンのみクリック）
                        next_btns = page.locator("button:not([disabled]), a, [role='button']:not([aria-disabled='true'])").filter(has_text=re.compile(r">|›|次"))
                        n = next_btns.count()
                        if n >= 2:
                            next_btns.nth(1).click(timeout=5000)
                        elif n == 1:
                            next_btns.first.click(timeout=5000)
                        else:
                            _log("次月ボタンが無効のため、この月で続行します。")
                            break
                        _log("次月へ移動しました。")
                    elif (cur_y, cur_m) > (year_int, month_int):
                        prev_btns = page.locator("button:not([disabled]), a, [role='button']:not([aria-disabled='true'])").filter(has_text=re.compile(r"<|‹|前"))
                        if prev_btns.count() > 0:
                            prev_btns.first.click(timeout=5000)
                        _log("前月へ移動しました。")
                    else:
                        break
                else:
                    next_btns = page.locator("button:not([disabled]), a, [role='button']:not([aria-disabled='true'])").filter(has_text=re.compile(r">|›"))
                    if next_btns.count() > 0:
                        next_btns.last.click(timeout=5000)
                        _log("次月へ移動しました。")
                    else:
                        break
            except Exception as e:
                _log(f"月送りクリックでエラー: {e}")
                break
            page.wait_for_timeout(1000)
            page_text = get_calendar_text()

        page.wait_for_timeout(1000)
        _log("対象日のセルを探しています...")

        # 対象日のセルを探す: 「日付の数字」と「× or ○ or △」が同じ要素内にあるセル
        no_slot_marks = ["X", "×", "✕", "❌", "満員", "売切", "－", "ー", "−"]
        slot_marks = ["○", "〇", "△", "▲", "空き", "◯", "◎", "購入", "選択"]
        date_cell = None
        found_available = False
        found_no_slots = False

        # 1) data-date で振ってあればそれを使う
        date_cell = page.query_selector(f'[data-date="{target_date}"]')
        if not date_cell:
            date_cell = page.query_selector(f'[data-date*="{target_date}"]')

        if not date_cell:
            # 2) カレンダーらしいセルを広く取得（td, li, gridcell, 日付らしいボタン）
            candidates = page.query_selector_all(
                "td, li, [role='gridcell'], [role='button'], button, a"
            )
            for el in candidates:
                try:
                    text = (el.inner_text() or "").strip()
                except Exception:
                    continue
                if not text or len(text) > 50:
                    continue
                # 日付だけの数字（1–31）と ○/×/△ が含まれる＝その日のセル
                if not re.search(rf"\b{day_num}\b", text):
                    continue
                has_no = any(m in text for m in no_slot_marks)
                has_yes = any(m in text for m in slot_marks)
                if has_no or has_yes:
                    date_cell = el
                    if has_no:
                        found_no_slots = True
                    if has_yes:
                        found_available = True
                    break
                # 210行目付近の判定をデバッグ用に強化（何が見えていたかログに出す）
                _log(f"デバッグ: 対象日のテキスト = '{cell_text}'")
                # 日付＋—（ダッシュ）だけのセルは「未選択」なのでスキップして続行
                if "—" in text or "－" in text:
                    continue
                if day_num in text or day_part in text:
                    date_cell = el
                    break
            if date_cell and not found_no_slots and not found_available:
                cell_text = (date_cell.inner_text() or "").strip()
                for m in no_slot_marks:
                    if m in cell_text:
                        found_no_slots = True
                        break
                for m in slot_marks:
                    if m in cell_text:
                        found_available = True
                        break
        else:
            cell_text = (date_cell.inner_text() or "").strip()
            for m in no_slot_marks:
                if m in cell_text:
                    found_no_slots = True
                    break
            if not found_no_slots:
                cell_class = (date_cell.get_attribute("class") or "").lower()
                for c in ["unavailable", "soldout", "sold-out", "closed", "full", "disabled", "no-slot", "blocked"]:
                    if c in cell_class:
                        found_no_slots = True
                        break
            if not found_no_slots:
                for m in slot_marks:
                    if m in cell_text:
                        found_available = True
                        break

        browser.close()
        _log("判定しました。")

        if found_no_slots:
            return False, f"{target_date} は空きなし（カレンダーでX/満員等の表示です）。"
        if found_available:
            return True, f"{target_date} に空きがあります。サイトでご確認ください。"
        if date_cell:
            return False, f"{target_date} は空きなしの表示です。"
        return False, f"{target_date} のカレンダーセルを特定できませんでした。要サイト確認。"


def main() -> int:
    target_date = get_check_date()
    channel_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    user_id = os.environ.get("LINE_USER_ID", "").strip()
    gmail_user = os.environ.get("GMAIL_USER", "").strip()
    gmail_app_password = os.environ.get("GMAIL_APP_PASSWORD", "").strip()
    notify_email = os.environ.get("NOTIFY_EMAIL", "").strip() or gmail_user
    notify_always = os.environ.get("LINE_NOTIFY_ALWAYS", "").strip().lower() in ("1", "true", "yes")

    print(f"対象日: {target_date}")
    try:
        has_slots, detail = check_availability(target_date)
    except Exception as e:
        detail = f"エラー: {e}"
        has_slots = False
        print(detail, file=sys.stderr)
    print(detail)

    if not (has_slots or notify_always):
        return 0

    msg_body = f"【コンパス空き情報】\n{detail}\n{COMPASS_URL}"

    # Gmail で通知（設定されていれば）
    if gmail_user and gmail_app_password and notify_email:
        if send_gmail(
            notify_email,
            gmail_user,
            gmail_app_password,
            subject=f"コンパス空き: {detail.split(chr(10))[0]}",
            body=msg_body,
        ):
            print("Gmail で通知を送信しました。")
        else:
            print("Gmail の送信に失敗しました。", file=sys.stderr)

    # LINE で通知（設定されていれば）
    if channel_token and user_id:
        if send_line_message(channel_token, user_id, msg_body):
            print("LINE に通知を送信しました。")
        else:
            print("LINE の送信に失敗しました。", file=sys.stderr)

    if not (channel_token and user_id) and not (gmail_user and gmail_app_password):
        print("通知先が未設定です。Gmail: GMAIL_USER, GMAIL_APP_PASSWORD, NOTIFY_EMAIL または LINE を設定してください。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
