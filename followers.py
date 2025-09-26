# Vercel Python Serverless Function
# Path: /api/followers?username=blackpinkofficial
import re, json, random, string, requests
from bs4 import BeautifulSoup

def _rand_webid():
    return ''.join(random.choices('0123456789', k=19))

def format_follower_count(v):
    if v is None: return None
    if isinstance(v, (int, float)): return int(v)
    s = str(v).strip().upper()
    if s.endswith('K'): return int(float(s[:-1]) * 1_000)
    if s.endswith('M'): return int(float(s[:-1]) * 1_000_000)
    if s.endswith('B'): return int(float(s[:-1]) * 1_000_000_000)
    return int(re.sub(r'[, ]', '', s))

def _extract(id_regex, html, username):
    m = re.search(id_regex, html, re.DOTALL | re.IGNORECASE)
    if not m: return None
    data = json.loads(m.group(1))
    # try a few common paths
    try:
        scope = data.get("__DEFAULT_SCOPE__", {})
        wad = scope.get("webapp.user-detail", {})
        userInfo = wad.get("userInfo", {})
        st = (userInfo.get("user") or {}).get("stats") or userInfo.get("stats") or {}
        if "followerCount" in st: return int(st["followerCount"])
    except: pass
    try:
        um = data.get("UserModule", {}).get("users", {})
        ukey = username.lower()
        for k, v in um.items():
            if k.lower() == ukey:
                st = v.get("stats", {})
                if "followerCount" in st: return int(st["followerCount"])
    except: pass
    return None

def _extract_dom(html):
    soup = BeautifulSoup(html, "html.parser")
    el = soup.find("strong", {"data-e2e": "followers-count"})
    if el: return format_follower_count(el.get_text(strip=True))
    lab = soup.find("span", string=re.compile(r"Followers", re.I))
    if lab:
        prev = lab.find_previous_sibling("strong")
        if prev: return format_follower_count(prev.get_text(strip=True))
    return None

def fetch_followers(username):
    url = f"https://www.tiktok.com/@{username}?lang=en"
    cookies = {"tt_webid_v2": _rand_webid()}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Upgrade-Insecure-Requests": "1",
    }
    r = requests.get(url, headers=headers, cookies=cookies, timeout=15)
    if r.status_code != 200:
        return {"success": False, "status_code": r.status_code, "error": f"HTTP {r.status_code} from TikTok"}
    html = r.text
    n = _extract(r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, username)
    if isinstance(n, int): return {"success": True, "username": username, "followers_int": n}
    n = _extract(r'<script[^>]+id="SIGI_STATE"[^>]*>(.*?)</script>', html, username)
    if isinstance(n, int): return {"success": True, "username": username, "followers_int": n}
    n = _extract_dom(html)
    if isinstance(n, int): return {"success": True, "username": username, "followers_int": n}
    return {"success": False, "error": "Followers not found in page JSON/DOM"}

def handler(request):
    # Vercel’s Python runtime passes a WSGI-like request; use query string
    try:
        qs = request.get("queryStringParameters") or {}
        username = (qs.get("username") or "").strip().lstrip("@")
        if not username:
            return {"statusCode": 400, "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"success": False, "error": "Please provide 'username'"})}
        data = fetch_followers(username)
        code = 200 if data.get("success") else data.get("status_code", 500)
        return {"statusCode": code, "headers": {"Content-Type": "application/json"}, "body": json.dumps(data)}
    except Exception as e:
        return {"statusCode": 500, "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"success": False, "error": f"Unexpected error: {e}"})}

# Vercel expects a module-level variable named "app" or a callable named "handler"
app = handler
