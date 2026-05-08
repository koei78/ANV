"""
ANV 請求・稼働管理システム — 操作マニュアル スクリーンショット撮影 & HTML生成
"""
import base64, os, time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:8765"
USERNAME = "admin"
PASSWORD = "admin1234"
OUT_HTML = Path(__file__).parent / "manual.html"

PAGES = [
    ("login",          "/login/",                   "ログイン画面"),
    ("dashboard",      "/",                          "ダッシュボード"),
    ("work_create",    "/work/new/",                 "稼働登録"),
    ("work_list",      "/work/",                     "稼働一覧"),
    ("transfer",       "/transfer/",                 "振込一覧"),
    ("invoice_list",   "/invoices/",                 "請求書管理"),
    ("invoice_new",    "/invoices/new/",             "請求書作成"),
    ("sales_report",   "/report/sales-rep/",         "担当営業レポート"),
    ("client_list",    "/master/clients/",           "クライアント先一覧"),
    ("client_new",     "/master/clients/new/",       "クライアント先登録"),
    ("sales_rep_list", "/master/sales-reps/",        "担当営業一覧"),
    ("sales_rep_new",  "/master/sales-reps/new/",    "担当営業登録"),
    ("partner_list",   "/master/partners/",          "パートナー企業一覧"),
    ("worker_list",    "/master/workers/",           "稼働者一覧"),
    ("settings",       "/settings/",                 "会社設定"),
]

SECTIONS = [
    {
        "title": "1. ログイン",
        "pages": ["login"],
        "steps": [
            "ブラウザで表示されたURLにアクセスします。",
            "「ユーザー名」と「パスワード」を入力して「ログイン」ボタンをクリックします。",
            "ログインに成功するとダッシュボードが表示されます。",
        ],
    },
    {
        "title": "2. ダッシュボード",
        "pages": ["dashboard"],
        "steps": [
            "今月の請求額（月初・月末）・粗利・稼働件数を KPI カードで確認できます。",
            "担当営業別の売上・粗利が表とグラフで確認できます。",
            "直近6ヶ月の粗利推移グラフが表示されます。",
            "未対応・振込待ちの件数がアラートとして表示されます。",
        ],
    },
    {
        "title": "3. 稼働登録",
        "pages": ["work_create"],
        "steps": [
            "サイドバーの「稼働登録」をクリックします。",
            "対象年・月、クライアント先、稼働者を選択します。",
            "クライアントを選択すると稼働店舗が自動入力されます。",
            "出勤数（0.5日単位可）と交通費を入力します。",
            "「登録」ボタンをクリックして保存します。",
        ],
    },
    {
        "title": "4. 稼働一覧・ステータス管理",
        "pages": ["work_list"],
        "steps": [
            "サイドバーの「稼働一覧」をクリックします。",
            "月・クライアント・ステータスで絞り込みができます。",
            "「次のステータスへ」ボタンをクリックしてステータスを進めます。",
            "ステータスの流れ：未対応 → 月初請求書送付済 → 月末請求書送付済 → 振込待ち → 振込完了",
        ],
    },
    {
        "title": "5. 振込一覧",
        "pages": ["transfer"],
        "steps": [
            "サイドバーの「振込一覧」をクリックします。",
            "パートナー企業への振込が必要な稼働記録を月別に確認できます。",
            "パートナー企業・稼働者・振込金額が一覧表示されます。",
            "振込完了後はステータスを「振込完了」に更新してください。",
        ],
    },
    {
        "title": "6. 請求書管理",
        "pages": ["invoice_list", "invoice_new"],
        "steps": [
            "サイドバーの「請求書管理」をクリックします。",
            "「新規作成」ボタンから請求書を作成します。",
            "クライアント・対象年月を選択すると稼働実績が自動プレビューされます。",
            "発行日・支払期限・備考を入力して「作成」をクリックします。",
            "請求書一覧から「PDF」ボタンをクリックしてPDFをダウンロードできます。",
            "ステータスは「下書き → 発行済 → 入金済」の順に管理します。",
        ],
    },
    {
        "title": "7. 担当営業レポート",
        "pages": ["sales_report"],
        "steps": [
            "サイドバーの「担当営業レポート」をクリックします。",
            "対象月を選択（または「全期間」）して絞り込みます。",
            "担当営業ごとの売上・パートナー支払・粗利・粗利率を確認できます。",
            "棒グラフで各担当の売上と粗利を視覚的に比較できます。",
            "詳細セクションでは担当ごとのクライアント別内訳も確認できます。",
        ],
    },
    {
        "title": "8. マスター管理 — クライアント先",
        "pages": ["client_list", "client_new"],
        "steps": [
            "サイドバーの「クライアント先」をクリックします（管理者のみ編集可）。",
            "「新規登録」ボタンから新しいクライアントを追加します。",
            "会社名・稼働店舗名・担当者名・メールアドレスを入力します。",
            "受け単価（日当）・支払いサイト・請求書送付方法を設定します。",
            "担当営業をドロップダウンから選択します。",
        ],
    },
    {
        "title": "9. マスター管理 — 担当営業",
        "pages": ["sales_rep_list", "sales_rep_new"],
        "steps": [
            "サイドバーの「担当営業」をクリックします（管理者のみ編集可）。",
            "「新規登録」ボタンから担当営業を追加します。",
            "氏名を入力して「登録」をクリックします。",
            "登録した担当営業はクライアント先の編集画面で選択できます。",
        ],
    },
    {
        "title": "10. マスター管理 — パートナー企業・稼働者",
        "pages": ["partner_list", "worker_list"],
        "steps": [
            "「パートナー企業」ではパートナー会社の情報・振込先口座を登録します。",
            "「稼働者」では稼働者の氏名・所属パートナー企業・パートナー単価を登録します。",
            "稼働者は稼働登録時にドロップダウンで選択します。",
        ],
    },
    {
        "title": "11. 会社設定",
        "pages": ["settings"],
        "steps": [
            "サイドバー下部の「会社設定」をクリックします（管理者のみ）。",
            "請求書に表示される会社名・住所・電話番号を設定します。",
            "振込先の銀行情報（銀行名・支店名・口座種別・口座番号・口座名義）を入力します。",
            "請求書の備考欄に表示するテキストを設定できます。",
        ],
    },
]


def take_screenshots(page):
    shots = {}

    # ログイン画面（認証前）
    page.goto(f"{BASE_URL}/login/")
    page.wait_for_load_state("networkidle")
    shots["login"] = page.screenshot(full_page=False)

    # ログイン
    page.fill("input[name=username]", USERNAME)
    page.fill("input[name=password]", PASSWORD)
    page.click("button[type=submit]")
    page.wait_for_load_state("networkidle")

    for key, path, _ in PAGES[1:]:
        try:
            page.goto(f"{BASE_URL}{path}")
            page.wait_for_load_state("networkidle")
            time.sleep(0.5)
            shots[key] = page.screenshot(full_page=False)
            print(f"  OK {key}")
        except Exception as e:
            print(f"  NG {key}: {e}")

    return shots


def img_tag(data: bytes) -> str:
    b64 = base64.b64encode(data).decode()
    return f'<img src="data:image/png;base64,{b64}" alt="screenshot">'


def build_html(shots: dict) -> str:
    section_html = ""
    for sec in SECTIONS:
        steps_html = "".join(f"<li>{s}</li>" for s in sec["steps"])
        imgs_html = ""
        for key in sec["pages"]:
            if key in shots:
                imgs_html += f'<div class="shot">{img_tag(shots[key])}</div>'
        section_html += f"""
<div class="section">
  <h2>{sec["title"]}</h2>
  <div class="content">
    <div class="steps"><ol>{steps_html}</ol></div>
    <div class="shots">{imgs_html}</div>
  </div>
</div>
"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>ANV 請求・稼働管理システム 操作マニュアル</title>
<style>
  @page {{ size: A4; margin: 15mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font-family: 'Helvetica Neue', Arial, 'Hiragino Sans', Meiryo, sans-serif;
         font-size: 11pt; color: #1a1a1a; margin: 0; background: #fff; }}
  h1 {{ background: #1a2b4a; color: #fff; padding: 20px 24px; margin: 0 0 24px;
        font-size: 20pt; }}
  h1 small {{ display: block; font-size: 11pt; font-weight: 400;
               color: #c8d6f0; margin-top: 4px; }}
  h2 {{ background: #1a2b4a; color: #fff; padding: 8px 14px;
        font-size: 13pt; margin: 0 0 12px; border-radius: 4px; }}
  .section {{ page-break-inside: avoid; margin-bottom: 28px; }}
  .content {{ display: flex; gap: 16px; align-items: flex-start; }}
  .steps {{ flex: 0 0 38%; }}
  .steps ol {{ margin: 0; padding-left: 18px; line-height: 1.7; }}
  .steps li {{ margin-bottom: 6px; }}
  .shots {{ flex: 1; }}
  .shot {{ margin-bottom: 8px; }}
  .shot img {{ width: 100%; border: 1px solid #d0d8e8; border-radius: 6px;
                box-shadow: 0 2px 6px rgba(0,0,0,.12); }}
  .cover {{ text-align: center; margin-bottom: 32px; padding: 20px;
             border: 2px solid #1a2b4a; border-radius: 8px; }}
  .cover p {{ color: #555; margin: 6px 0; }}
  @media print {{
    .section {{ page-break-inside: avoid; }}
  }}
</style>
</head>
<body>
<h1>ANV 請求・稼働管理システム<small>操作マニュアル</small></h1>
<div class="cover">
  <p>本マニュアルでは ANV 請求・稼働管理システムの各機能の使い方を説明します。</p>
  <p>ブラウザの「印刷」→「PDFとして保存」でPDF化できます。</p>
</div>
{section_html}
</body>
</html>"""


def main():
    print("スクリーンショット撮影中...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 800})
        shots = take_screenshots(page)
        browser.close()

    print("HTML生成中...")
    html = build_html(shots)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"完成: {OUT_HTML}")
    print("ブラウザで開いて「印刷」→「PDFとして保存」してください。")


if __name__ == "__main__":
    main()
