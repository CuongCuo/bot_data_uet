import os

DEFAULT_DB_PATH = "db/seen_urls.txt"

def ensure_db_exists(path=DEFAULT_DB_PATH):
    """Ensures the parent directory and the database file exist."""
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            pass

def load_seen_urls(path=DEFAULT_DB_PATH) -> set[str]:
    """Loads the set of previously notified URLs from the text file."""
    ensure_db_exists(path)
    seen = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if url:
                seen.add(url)
    return seen

def add_seen_url(url: str, path=DEFAULT_DB_PATH):
    """Appends a new URL to the seen database file."""
    ensure_db_exists(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def filter_new_items(items: list[dict], path=DEFAULT_DB_PATH) -> list[dict]:
    """
    Filters a list of crawled items, returning only new ones.
    Updates the database with the newly seen URLs.
    """
    seen_urls = load_seen_urls(path)
    new_items = []
    
    for item in items:
        link = item.get("link", "").strip()
        if not link:
            continue
        
        # Check if URL is in the seen set
        if link not in seen_urls:
            new_items.append(item)
            seen_urls.add(link)
            add_seen_url(link, path)
            
    return new_items
