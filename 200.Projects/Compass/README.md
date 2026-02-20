# コンパス空きチェック

国立科学博物館「親と子のたんけんひろば コンパス」の予約空きを監視し、空きがあれば **Gmail** または **LINE** で通知します。

---

## 通知方法は2つ（どちらかだけでOK）

### おすすめ: Gmail（かんたん）

**3つの環境変数**を設定するだけです。

1. **Google アカウント**で [2段階認証](https://myaccount.google.com/security) を有効にする
2. **アプリパスワード**を発行: 同じページの「アプリ パスワード」→ デバイス「メール」などで生成 → 表示された **16文字**をコピー
3. 次を設定する:
  - `GMAIL_USER` … 送信元（あなたの Gmail アドレス）
  - `GMAIL_APP_PASSWORD` … 上記のアプリパスワード
  - `NOTIFY_EMAIL` … 届け先（省略すると GMAIL_USER と同じ＝自分に送る）

**ローカル例:**

```bash
GMAIL_USER=あなた@gmail.com GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx NOTIFY_EMAIL=あなた@gmail.com CHECK_DATE=2026-03-05 python3 main.py
```

**GitHub Actions:** Settings → Secrets に `GMAIL_USER` / `GMAIL_APP_PASSWORD` / `NOTIFY_EMAIL` を登録すれば、自動実行で空きがあればメールが届きます。

---

### LINE（Messaging API）

### 1. LINE 公式アカウント（チャネル）を作る

1. [LINE Developers](https://developers.line.biz/ja/) にログイン
2. **プロバイダー**を作成（まだなければ）
3. **Messaging API チャネル**を新規作成
4. チャネルの **Messaging API** タブで **Channel access token** を発行 → **長期**トークンをコピー（`LINE_CHANNEL_ACCESS_TOKEN` に設定）

### 2. 自分の User ID を取得する（かんたん・3分）

通知を受け取るには **あなたの LINE User ID**（`U` で始まる文字列）が必要です。**ngrok もインストール不要**で取れます。

1. ブラウザで **[webhook.site](https://webhook.site)** を開く → 画面に **あなただけの URL**（例: `https://webhook.site/xxxx-xxxx-xxxx`）が表示されるので **コピー**
2. [LINE Developers コンソール](https://developers.line.biz/console/) で、あなたのチャネル → **Messaging API** タブを開く
3. **Webhook URL** の欄に、コピーした webhook.site の URL を貼り付けて **「検証」** を押す（成功と出ればOK）
4. **LINE アプリ**で、友だち追加したその公式アカウント（ボット）を開き、**「テスト」などメッセージを1通送る**
5. **webhook.site のページ**に戻る → 左に届いたリクエストが1件出るので **クリック** → **Request body**（または Body）を開く
6. 中身の JSON で **`"userId": "Uxxxxxxxxxxxxxxxx..."`** を探す（`events` → `source` → `userId`）。その **`U` から始まる部分をコピー** → これが **LINE_USER_ID**
7. 終わったら LINE の **Webhook URL を空欄にして「検証」** しておくと安心（任意）

### 3. 環境変数・Secret の設定（LINE を使う場合）


| 使う場所               | 設定内容                                                           |
| ------------------ | -------------------------------------------------------------- |
| **ローカル**           | `LINE_CHANNEL_ACCESS_TOKEN`、`LINE_USER_ID` を export または実行時に指定  |
| **GitHub Actions** | **Secrets** に `LINE_CHANNEL_ACCESS_TOKEN` と `LINE_USER_ID` を登録 |


Gmail と LINE の両方を設定すると、**両方に**通知が送られます。

---

## 30分ごとに自動でチェックする（GitHub Actions）

次の手順で、**30分ごとに自動で空きをチェックし、空きがあれば LINE に通知**されます。

### 1. コードを GitHub にプッシュする

- このフォルダ（Vault）が **Git リポジトリ** になっていて、**GitHub のリポジトリ** にプッシュされている必要があります。
- まだなら:
  1. GitHub で新しいリポジトリを作成（空でOK）
  2. ターミナルで Vault フォルダに移動して:
     ```bash
     git init
     git add .
     git commit -m "Add Compass checker"
     git remote add origin https://github.com/あなたのユーザー名/リポジトリ名.git
     git push -u origin main
     ```
  - すでに別ブランチ名（例: master）の場合は `git push -u origin ブランチ名` に読み替えてください。

### 2. Secrets を登録する

1. GitHub でそのリポジトリを開く → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** で次を **1つずつ** 追加する:

   | Name | Value（例） |
   |------|-------------|
   | `LINE_CHANNEL_ACCESS_TOKEN` | あなたのチャネルアクセストークン（長期） |
   | `LINE_USER_ID` | あなたの User ID（`U` で始まる文字列） |

  - Gmail で通知したい場合は、あわせて `GMAIL_USER` / `GMAIL_APP_PASSWORD` / `NOTIFY_EMAIL` も登録する。

### 3. チェックする日付を決める（任意）

- **Variables** タブ → **New repository variable**
  - Name: `CHECK_DATE`
  - Value: `2026-03-15`（チェックしたい日付を YYYY-MM-DD で）
- 設定しなければ、**毎回「明日」** の日付がチェックされます。

### 4. 動作確認

- **Actions** タブ → **コンパス空きチェック** → **Run workflow** で手動実行できる
- 成功すれば、**30分ごと**（cron）でも自動実行され、空きがあれば LINE に通知が届きます。

---

## チェックする日付の指定（毎回入力しなくてよい）

- **Variables** に `CHECK_DATE=2026-03-15` などを設定すると、30分ごとの自動実行でその日付をチェックします。
- **手動実行**時は「チェックする日付」入力欄に `2026-03-05` のように指定できます（空欄なら Variables の値、未設定なら明日）。

---

## ローカルでの実行

```bash
cd 200.Projects/Compass
pip3 install -r requirements.txt
python3 -m playwright install chromium

# 日付は省略可（省略すると明日）
CHECK_DATE=2026-03-05 python3 main.py

# Gmail で通知（かんたん）
GMAIL_USER=あなた@gmail.com GMAIL_APP_PASSWORD=アプリパスワード NOTIFY_EMAIL=あなた@gmail.com CHECK_DATE=2026-03-05 python3 main.py

# LINE で通知
LINE_CHANNEL_ACCESS_TOKEN=xxx LINE_USER_ID=Uxxxx... CHECK_DATE=2026-03-05 python3 main.py
```

空きがなくても通知したい場合は `LINE_NOTIFY_ALWAYS=1` を付けて実行します。