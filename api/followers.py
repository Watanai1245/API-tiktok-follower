import os
import re, json, random, string, requests
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify

app = Flask(__name__)

TIKTOK_COOKIE = os.environ.get("TIKTOK_COOKIE")  # <— ใส่ใน Vercel Env

def _rand_webid(): return ''.join(random.choices('0123456789', k=19))

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
    # path ยอดนิยม
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

def _looks_like_login_wall(resp_text: str, final_url: str) -> bool:
    u = (final_url or "").lower()
    if "/login" in u or "/register" in u: 
        return True
    t = (resp_text or "").lower()
    # คีย์เวิร์ดที่ชอบเจอเวลาโดนล็อกอิน/verify/captcha
    markers = ["signup or login", "log in to tiktok", "verify it's you", "tiktok-captcha"]
    return any(m in t for m in markers)

def fetch_followers(username):
    url = f"https://www.tiktok.com/@{username}?lang=en"

    UA_DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    UA_MOBILE  = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"

    # ลอง 2 โปรไฟล์ (เดสก์ท็อป → โมบาย) เผื่อโมบายไม่ติดวอลล์
    for ua in (UA_DESKTOP, UA_MOBILE):
        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.google.com/",
            "Upgrade-Insecure-Requests": "1",
        }
        cookies = {"tt_webid_v2": _rand_webid()}

        # ถ้ามีคุกกี้ session ให้แนบแทน (มักผ่าน login-wall)
        if TIKTOK_COOKIE:
            headers["Cookie"] = TIKTOK_COOKIE
            cookies = {}  # ไม่ต้องส่ง cookies dict ซ้ำ

        r = requests.get(url, headers=headers, cookies=cookies, timeout=15, allow_redirects=True)

        # ถ้าเจอ login-wall ให้ลองโปรไฟล์ต่อไป
        if _looks_like_login_wall(r.text, r.url):
            continue

        if r.status_code != 200:
            # ถ้าสถานะ 403/401 เดาว่าติดวอลล์
            if r.status_code in (401, 403):
                return {"success": False, "status_code": r.status_code, "error": "Login required or cookie expired"}
            return {"success": False, "status_code": r.status_code, "error": f"HTTP {r.status_code} from TikTok"}

        html = r.text
        n = _extract(r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, username)
        if isinstance(n, int): return {"success": True, "username": username, "followers_int": n}
        n = _extract(r'<script[^>]+id="SIGI_STATE"[^>]*>(.*?)</script>', html, username)
        if isinstance(n, int): return {"success": True, "username": username, "followers_int": n}
        n = _extract_dom(html)
        if isinstance(n, int): return {"success": True, "username": username, "followers_int": n}

    # มาลงที่นี่ แปลว่าทั้งสองโปรไฟล์ยังเจอ login-wall/ไม่มีข้อมูล
    if TIKTOK_COOKIE:
        return {"success": False, "status_code": 401, "error": "Login required or cookie expired"}
    else:
        return {"success": False, "status_code": 401, "error": "Login required. Please set TIKTOK_COOKIE env var"}
    

@app.get("/api/followers")
def followers_route():
    username = (request.args.get("username") or "").strip().lstrip("@")
    if not username:
        return jsonify({"success": False, "error": "Please provide 'username'"}), 400
    try:
        data = fetch_followers(username)
        code = 200 if data.get("success") else data.get("status_code", 500)
        return jsonify(data), code
    except requests.RequestException as e:
        return jsonify({"success": False, "error": f"Network error: {e}"}), 502
    except Exception as e:
        return jsonify({"success": False, "error": f"Unexpected error: {e}"}), 500

@app.get("/")
def index():
    return "OK"
