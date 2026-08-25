# Dự án: Bot Crawl Học bổng / CLB / Cơ hội việc làm (UET & Điện tử Viễn thông)

## 1. Mục tiêu

Xây dựng bot tự động thu thập thông tin từ:
- Trang web trường (UET)
- Trang khoa/ngành Điện tử Viễn thông
- Trang chính phủ (học bổng nhà nước, đề án du học...)
- Trang doanh nghiệp liên quan (tuyển dụng, học bổng doanh nghiệp)
- Trang CLB / Đoàn thanh niên trường

Khi có tin mới (học bổng, CLB tuyển thành viên, cơ hội việc làm...) → **gửi thông báo qua Telegram** (ưu tiên vì dễ làm bot, free, không cần duyệt như Zalo OA).

ESP32 (LCD/OLED hiển thị tin mới) → để giai đoạn sau, kiến trúc sẽ chừa sẵn chỗ để cắm vào (đọc qua MQTT/HTTP từ server).

---

## 2. Kiến trúc tổng thể

```
[Nguồn web] --(requests/BeautifulSoup/Playwright)--> [Crawler Python]
                                                            |
                                                    [So sánh với DB cũ]
                                                    (SQLite: đã có / mới)
                                                            |
                                                  [Tin mới?] --Yes--> [Telegram Bot API]
                                                            |
                                                        [Lưu vào DB]
                                                            |
                                        (tương lai) --> [MQTT broker] --> [ESP32 hiển thị]
```

**Thành phần:**
| Thành phần | Công nghệ |
|---|---|
| Crawler | Python (`requests`, `BeautifulSoup4`, `Playwright` cho trang JS-render) |
| Lưu trữ | SQLite (nhẹ, không cần server DB riêng) |
| Lịch chạy | `cron` (Linux) hoặc GitHub Actions (chạy free, không cần server riêng) |
| Thông báo | Telegram Bot API (`python-telegram-bot` hoặc `requests` gọi thẳng API) |
| Config nguồn | File `sources.yaml` — dễ thêm/bớt URL không cần sửa code |
| (Tương lai) ESP32 | Đọc dữ liệu qua HTTP endpoint nhỏ hoặc MQTT topic |

---

## 3. Cấu trúc thư mục đề xuất

```
scholarship-crawler/
├── sources.yaml          # danh sách URL + loại nguồn (school/gov/company/club)
├── crawler.py             # logic crawl + parse
├── notifier.py            # gửi Telegram
├── storage.py             # SQLite: check trùng, lưu tin mới
├── main.py                # entrypoint, orchestrate toàn bộ
├── db/
│   └── seen_items.db
├── requirements.txt
└── .env                    # TELEGRAM_BOT_TOKEN, CHAT_ID (KHÔNG commit lên git)
```

---

## 4. `sources.yaml` — cấu hình nguồn (Đã tối ưu & mở rộng thực tế)

```yaml
sources:
  # --- TRƯỜNG ĐẠI HỌC CÔNG NGHỆ (UET) ---
  - name: "UET - Học phí & Học bổng"
    type: "school"
    url: "https://uet.vnu.edu.vn/category/sinh-vien/hoc-phi-hoc-bong/"
    selector: "h2.entry-title a"
    verified: true

  - name: "UET - Tin tức Sinh viên"
    type: "school"
    url: "https://uet.vnu.edu.vn/category/tin-tuc/tin-sinh-vien/"
    selector: "h2.entry-title a"
    verified: true

  - name: "UET - Thông báo chung"
    type: "school"
    url: "https://uet.vnu.edu.vn/category/tin-tuc/thong-bao/"
    selector: "h2.entry-title a"
    verified: true

  # --- KHOA ĐIỆN TỬ VIỄN THÔNG (FET) ---
  - name: "FET - Học bổng & Hỗ trợ"
    type: "faculty"
    url: "https://fet.uet.vnu.edu.vn/category/hoc-bong/"
    selector: "h3.entry-title a"
    verified: true

  - name: "FET - Cơ hội việc làm"
    type: "faculty"
    url: "https://fet.uet.vnu.edu.vn/category/co-hoi-viec-lam/"
    selector: "h3.entry-title a"
    verified: true

  - name: "FET - Hoạt động & Sự kiện"
    type: "faculty"
    url: "https://fet.uet.vnu.edu.vn/category/su-kien/"
    selector: "h3.entry-title a"
    verified: true

  # --- CÔ QUAN / ĐƠN VỊ NGOÀI (CẦN BYPASS BOT PROTECTION HOẶC RENDER JS) ---
  - name: "Cục Hợp tác Quốc tế (Bộ GD&ĐT)"
    type: "gov"
    url: "https://icd.edu.vn/"
    selector: "a.news-title"
    notes: "Chứa thông tin học bổng Hiệp định/Chính phủ. Có Cloudflare bảo vệ (403 Forbidden), cần dùng Playwright hoặc bypass header."

  # --- DOANH NGHIỆP ĐỐI TÁC (TIN TUYỂN DỤNG / HỌC BỔNG STP, V-STT...) ---
  - name: "Samsung Careers Vietnam"
    type: "company"
    url: "https://www.samsungcareers.com.vn/"
    selector: "table.tbl-board a"
    notes: "Trang web động, nên sử dụng Playwright hoặc gọi thẳng API của server."

  - name: "Viettel Careers"
    type: "company"
    url: "https://careers.viettel.com.vn/"
    selector: "a.job-title"
    notes: "Trang tuyển dụng Viettel, render bằng JS."

  - name: "FPT Software Careers"
    type: "company"
    url: "https://career.fpt-software.com/vi/co-hoi-nghe-nghiep/"
    selector: "h3.job-title a"
    notes: "Trang tuyển dụng FPT Software, cập nhật Fresher/Junior."
```

> **Lưu ý thực tế:**
> 1. Các nguồn của **UET** (`uet.vnu.edu.vn`) sử dụng cùng giao diện WordPress, các link bài viết đều nằm trong thẻ `h2.entry-title a`.
> 2. Các nguồn của **FET UET** (`fet.uet.vnu.edu.vn`) sử dụng theme Newspaper của WordPress, các link bài viết nằm trong thẻ `h3.entry-title a`.
> 3. Các trang tuyển dụng doanh nghiệp hoặc chính phủ (`icd.edu.vn`) có hệ thống bảo vệ bot hoặc render JS động, do đó ở hàm `crawler.py` cần nâng cấp để tự động chuyển đổi sang dùng `Playwright` hoặc thêm headers chi tiết cho từng loại trang.

---

## 5. Logic crawl (`crawler.py`) — khung sườn

```python
import requests
from bs4 import BeautifulSoup
import yaml

def load_sources(path="sources.yaml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["sources"]

def crawl_source(source: dict) -> list[dict]:
    """Trả về danh sách {title, link, source_name} từ 1 nguồn."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ScholarshipBot/1.0)"}
    resp = requests.get(source["url"], headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    items = []
    for el in soup.select(source["selector"]):
        title = el.get_text(strip=True)
        link = el.get("href", "")
        if link and not link.startswith("http"):
            # nối domain nếu link tương đối
            from urllib.parse import urljoin
            link = urljoin(source["url"], link)
        if title and link:
            items.append({
                "title": title,
                "link": link,
                "source_name": source["name"],
                "type": source["type"],
            })
    return items

def crawl_all(sources: list[dict]) -> list[dict]:
    all_items = []
    for src in sources:
        try:
            all_items.extend(crawl_source(src))
        except Exception as e:
            print(f"[LỖI] {src['name']}: {e}")
    return all_items
```

> Với trang render bằng JavaScript (React/Vue, nội dung không có sẵn trong HTML gốc), `requests` sẽ không lấy được — cần dùng **Playwright** thay thế cho nguồn đó.

---

## 6. Chống trùng lặp (`storage.py`) — khung sườn

```python
import sqlite3
import hashlib

def init_db(path="db/seen_items.db"):
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seen_items (
            id TEXT PRIMARY KEY,
            title TEXT,
            link TEXT,
            source_name TEXT,
            seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

def item_id(item: dict) -> str:
    return hashlib.md5(item["link"].encode()).hexdigest()

def filter_new_items(conn, items: list[dict]) -> list[dict]:
    new_items = []
    for item in items:
        iid = item_id(item)
        cur = conn.execute("SELECT 1 FROM seen_items WHERE id = ?", (iid,))
        if cur.fetchone() is None:
            new_items.append(item)
            conn.execute(
                "INSERT INTO seen_items (id, title, link, source_name) VALUES (?, ?, ?, ?)",
                (iid, item["title"], item["link"], item["source_name"])
            )
    conn.commit()
    return new_items
```

---

## 7. Gửi thông báo Telegram (`notifier.py`) — khung sườn

```python
import os
import requests

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

def send_telegram_message(text: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
    resp = requests.post(url, data=payload, timeout=10)
    resp.raise_for_status()

def notify_new_items(items: list[dict]):
    for item in items:
        msg = f"🎓 <b>{item['source_name']}</b>\n{item['title']}\n{item['link']}"
        send_telegram_message(msg)
```

**Cách tạo Telegram Bot (5 phút):**
1. Chat với `@BotFather` trên Telegram → gõ `/newbot` → làm theo hướng dẫn → nhận `TELEGRAM_BOT_TOKEN`.
2. Tạo 1 nhóm/kênh, add bot vào, lấy `CHAT_ID` bằng cách gọi `https://api.telegram.org/bot<TOKEN>/getUpdates` sau khi gửi thử 1 tin trong nhóm.

---

## 8. `main.py` — chạy toàn bộ

```python
from crawler import load_sources, crawl_all
from storage import init_db, filter_new_items
from notifier import notify_new_items

def main():
    sources = load_sources()
    conn = init_db()

    all_items = crawl_all(sources)
    new_items = filter_new_items(conn, all_items)

    if new_items:
        print(f"Tìm thấy {len(new_items)} tin mới.")
        notify_new_items(new_items)
    else:
        print("Không có tin mới.")

if __name__ == "__main__":
    main()
```

`requirements.txt`:
```
requests
beautifulsoup4
pyyaml
playwright   # optional, chỉ cần nếu có trang JS-render
```

---

## 9. Lịch chạy tự động (không cần server riêng)

**Cách khuyên dùng: GitHub Actions** (free, chạy định kỳ, không cần server):

```yaml
# .github/workflows/crawl.yml
name: Crawl Scholarship Bot
on:
  schedule:
    - cron: "0 */6 * * *"   # mỗi 6 tiếng
  workflow_dispatch: {}      # cho phép chạy tay

jobs:
  crawl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python main.py
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
      - uses: actions/upload-artifact@v4   # để lưu lại db/seen_items.db giữa các lần chạy
        with:
          name: seen-items-db
          path: db/seen_items.db
```

> Lưu ý: GitHub Actions không giữ file giữa các lần chạy mặc định — cần commit `db/seen_items.db` vào repo sau mỗi lần chạy, hoặc dùng cache/artifact, hoặc chuyển sang SQLite trên 1 VPS nhỏ / free tier như Render, Railway, Oracle Cloud Free Tier nếu muốn ổn định hơn.

---

## 10. Giai đoạn sau: tích hợp ESP32

Khi bot đã chạy ổn:
- Thêm 1 API endpoint nhỏ (Flask/FastAPI) trả về N tin mới nhất dạng JSON.
- ESP32 (dùng `WiFiClientSecure` + `HTTPClient` trong Arduino) gọi API định kỳ, hiển thị tiêu đề tin mới nhất lên màn hình OLED/LCD (SSD1306 qua I2C là lựa chọn phổ biến, rẻ, dễ lập trình).
- Hoặc dùng MQTT (broker miễn phí như HiveMQ) để đẩy tin theo thời gian thực thay vì polling.

---

## 11. Việc cần làm tiếp theo

1. Gửi danh sách URL cụ thể (UET, khoa ĐTVT, chính phủ, doanh nghiệp, CLB/Đoàn) → mình sẽ giúp xác định CSS selector từng trang.
2. Xác nhận có trang nào cần Playwright (JS-render) không.
3. Tạo Telegram Bot theo hướng dẫn mục 7, gửi token để test thử luồng end-to-end.
4. Sau khi chạy ổn định, quay lại phần ESP32.
