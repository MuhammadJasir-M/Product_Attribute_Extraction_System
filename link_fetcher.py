import requests
from urllib.parse import urlparse
from genuineness_checker import check_urls  # Your existing validator

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ' +
                  'AppleWebKit/537.36 (KHTML, like Gecko) ' +
                  'Chrome/94.0.4606.81 Safari/537.36'
}

def fetch_product_links(user_query, google_api_key, google_cse_id, max_results=20):
    all_urls = []
    for start in range(1, max_results + 1, 10):
        params = {
            "key": google_api_key,
            "cx": google_cse_id,
            "q": user_query,
            "num": 10,
            "start": start
        }
        try:
            response = requests.get("https://www.googleapis.com/customsearch/v1", params=params, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            print(f"Search API request failed: {e}")
            break

        if "items" not in data:
            print("No search results or API error:")
            print(data)
            break

        urls = [item['link'] for item in data['items']]
        all_urls.extend(urls)

        if len(data['items']) < 10:
            break

    return all_urls

def is_excluded_link(url: str) -> bool:
    exclude_keywords = [
        "review", "forum", "reddit", "community", "support",
        "blog", "help", "question", "comment", "news", 
        "gsmarena", "quora", "manual", "guide", "tutorial", "howto", "tips", "tricks",
        "youtube", "facebook", "twitter", "instagram", "linkedin", "pinterest",
        "tiktok", "tumblr", "vimeo", "snapchat", "discord", "imgur", "9gag",
        "cnn", "bbc", "reuters", "bloomberg", "forbes", "cnbc", "nytimes", "guardian",
        "techcrunch", "theverge", "wired", "engadget", "gizmodo", "arstechnica",
        "digitaltrends", "pcmag", "tomshardware", "slashdot", "slashgear", "sfgate",
        "xda-developers", "digitalspy", "gamespot", "ign", "kotaku", "gamefaqs",
        "metacritic", "polygon", "vg247", "rockpapershotgun", "lifehacker", "howtogeek",
        "phonearena", "androidcentral", "imore", "9to5mac", "macrumors",
        "androidpolice", "droidlife", "phonedog", "pocketnow", "techradar", "stuff",
        "trustedreviews", "expertreviews", "whathifi", "eurogamer", "gamesindustry",
        "destructoid", "gameinformer", "giantbomb", "github", "gitlab", "bitbucket",
        "stackoverflow", "stackexchange", "codepen", "jsbin", "jsfiddle", "codesandbox",
        "yelp", "tripadvisor", "trustpilot", "glassdoor", "indeed", "bbb",
        "angieslist", "consumerreports", "trustradius", "g2", "capterra",
        "wikipedia", "wikihow", "fandom", "wikia", "britannica", "dictionary",
        "medium", "wordpress", "blogspot", "blogger", "livejournal", "substack",
        "slack", "zoom", "teams", "skype", "dropbox", "trello", "asana",
        "spotify", "netflix", "hulu", "disney", "twitch", "soundcloud", "bandcamp",
        "coursera", "udemy", "edx", "khan", "lynda", "pluralsight", "skillshare",
        "mega", "mediafire", "rapidshare", "4shared", "zippyshare", "wetransfer",
        "pricerunner", "pricegrabber", "shopping", "compare", "comparison",
        "deals", "coupons", "vouchers", "discounts", "cashback", "documentation",
        "docs", "api", "sdk", "spec", "specification", "readme", "changelog",
        "recipe", "cooking", "food", "travel", "hotel", "flight", "weather",
        "fashion", "beauty", "health", "fitness", "sports", "auto", "cars",
        "ifixit", "discussions", "answers", "edu", "university", "college", "school",
        "answers", "viewtopic", "thread", "post", "topic"
    ]
    
    url_lower = url.lower()
    # Exclude based on keywords
    if any(keyword in url_lower for keyword in exclude_keywords):
        return True
    # Exclude specific domains like youtube.com
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    excluded_domains = ["youtube.com", "www.youtube.com"]
    if domain in excluded_domains:
        return True
    return False

def filter_out_non_buying(urls):
    filtered = []
    for url in urls:
        if is_excluded_link(url):
            print(f"Excluded non-buy link: {url}")
            continue
        filtered.append(url)
    return filtered

if __name__ == "__main__":
    GOOGLE_API_KEY = "AIzaSyD7v44XdLKTUkuHMrj4MRNLntzc2s_wtpY"
    GOOGLE_CSE_ID = "17187382183ab433f"

    query = input("Enter product search query: ").strip()
    fetched_urls = fetch_product_links(query, GOOGLE_API_KEY, GOOGLE_CSE_ID)
    print(f"Fetched {len(fetched_urls)} URLs.")

    filtered_urls = filter_out_non_buying(fetched_urls)
    print(f"Filtered to {len(filtered_urls)} URLs after excluding non-buying sites.")

    valid_products_queue = check_urls(filtered_urls)

    print("\n---- Genuine Products Queue ----")
    for product in valid_products_queue:
        print(f"{product['title']} | {product['url']}")