import sys
from crawler import load_sources, crawl_all
from storage import filter_new_items
from notifier import notify_new_items, send_email_digest

# Ensure UTF-8 output on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def main():
    print("==================================================")
    print("🚀 BẮT ĐẦU CHẠY CRAWLER HỌC BỔNG & TIN TỨC UET/FET")
    print("==================================================")
    
    # 1. Load sources configurations
    try:
        sources = load_sources("sources.yaml")
        print(f"Đã nạp {len(sources)} nguồn crawl từ sources.yaml.")
    except Exception as e:
        print(f"[CRITICAL ERROR] Không thể đọc file sources.yaml: {e}")
        sys.exit(1)
        
    # 2. Run crawl on all sources
    print("\n🔍 Đang cào dữ liệu từ các nguồn...")
    crawled_items = crawl_all(sources)
    print(f"Tổng số tin tìm thấy trên web/FB: {len(crawled_items)} tin.")
    
    # 3. Filter out previously notified links
    print("\n💾 Đang kiểm tra trùng lặp và lưu trữ...")
    new_items = filter_new_items(crawled_items)
    
    # 4. Notify new items
    if new_items:
        print(f"\n✨ Phát hiện {len(new_items)} TIN MỚI!")
        print("📨 Đang gửi email digest...")
        send_email_digest(new_items)
        print("📨 Đang gửi tin Telegram...")
        notify_new_items(new_items)
        print("Gửi thông báo thành công!")
    else:
        print("\n💤 Không tìm thấy tin tức nào mới.")
        
    print("\n==================================================")
    print("🏁 HOÀN THÀNH CHU KỲ CRAWL!")
    print("==================================================")

if __name__ == "__main__":
    main()
