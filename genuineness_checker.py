import requests
from bs4 import BeautifulSoup
import validators
from fake_useragent import UserAgent
from urllib.parse import urlparse
import ssl
import socket

SAFE_BROWSING_API_KEY = "YOUR_API_KEY"

def is_valid_url(url: str) -> bool:
    result = validators.url(url)
    return result is True

def get_user_agent() -> str:
    try:
        from fake_useragent import UserAgent
        ua = UserAgent()
        return ua.random
    except ImportError:
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

def check_ssl_certificate(url: str) -> bool:
    try:
        hostname = urlparse(url).hostname
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
        return True
    except Exception as e:
        print(f"SSL check failed for {url}: {e}")
        return False

def google_safe_browsing_check(url: str) -> bool:
    api_url = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={SAFE_BROWSING_API_KEY}"
    payload = {
        "client": {"clientId": "shopSage", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }
    try:
        r = requests.post(api_url, json=payload, timeout=5)
        r.raise_for_status()
        return not bool(r.json().get("matches"))
    except Exception as e:
        print(f"Safe Browsing check failed for {url}: {e}. Skipping this check.")
        return True  # Fail open

def scrape_website(url: str):
    headers = {'User-Agent': get_user_agent()}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None

def check_genuineness_keywords(text: str) -> bool:
    fake_keywords = ["replica", "copy", "fake", "counterfeit", "cheap quality"]
    text_lower = text.lower()
    return not any(word in text_lower for word in fake_keywords)

def check_urls(url_list: list) -> list:
    result_queue = []
    for url in url_list:
        if not is_valid_url(url):
            print(f"Invalid URL skipped: {url}")
            continue

        if not check_ssl_certificate(url):
            print(f"Site without valid SSL skipped: {url}")
            continue

        if not google_safe_browsing_check(url):
            print(f"Unsafe URL skipped: {url}")
            continue

        soup = scrape_website(url)
        if not soup:
            continue

        title_tag = soup.find('h1') or soup.find('title')
        meta_desc = soup.find("meta", attrs={"name": "description"})
        desc_tag = meta_desc["content"] if meta_desc and meta_desc.get("content") else soup.find('p') or soup.find('div')

        title = title_tag.get_text(strip=True) if title_tag else "N/A"
        description = desc_tag.get_text(strip=True) if hasattr(desc_tag, "get_text") else desc_tag or "N/A"

        if check_genuineness_keywords(title + " " + description):
            result_queue.append({
                "url": url,
                "title": title,
                "description": description
            })
        else:
            print(f"Suspicious keywords found in: {url}")

    return result_queue

# Example usage
if __name__ == "__main__":
    urls = [
        "https://www.amazon.in/Samsung-Galaxy-Graphite-Compatible-Android/dp/B0B99PC4RG?th=1",
        "https://www.amazon.in/Samsung-Smartphone-Titanium-Snapdragon-ProVisual/dp/B0DSKMKJV5",
        "http://example-fake-site.com/product"
    ]

    filtered_urls = check_urls(urls)
    print("\n---- Genuine Products Queue ----")
    for item in filtered_urls:

        print(f"{item['title']} | {item['url']}")
