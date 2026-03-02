import re, json, random, requests
from bs4 import BeautifulSoup
from flask import request, jsonify

def followers_route():
    username = (request.args.get("username") or "").strip().lstrip("@")

    if not username:
        return jsonify({"success": False, "error": "username required"}), 400

    result = fetch_followers(username)

    return jsonify(result)

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

def fetch_followers(username):
    url = f"https://www.tiktok.com/@{username}?lang=en"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }

    cookies = {
        "tt_webid_v2": ''.join(random.choices('0123456789', k=19))
    }

    r = requests.get(url, headers=headers, cookies=cookies, timeout=15)

    if r.status_code != 200:
        return {"success": False, "status_code": r.status_code}

    html = r.text

    # 🔥 ดึง JSON จาก script tag
    match = re.search(
        r'<script[^>]+id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL
    )

    if not match:
        return {"success": False, "error": "TikTok JSON not found (possibly blocked)"}

    data = json.loads(match.group(1))

    try:
        user_data = (
            data["__DEFAULT_SCOPE__"]
            ["webapp.user-detail"]
            ["userInfo"]
        )

        stats = user_data.get("stats") or user_data["user"].get("stats")

        return {
            "success": True,
            "username": username,
            "followers_int": stats["followerCount"],
            "following_int": stats["followingCount"],
            "likes_int": stats["heartCount"],
            "video_count": stats["videoCount"]
        }

    except Exception as e:
        return {"success": False, "error": f"Parse error: {e}"}