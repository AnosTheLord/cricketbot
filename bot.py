import requests
import time
import random
import os
from datetime import datetime, timedelta
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont

# 🔐 ENV VARIABLES (IMPORTANT FOR RAILWAY)
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CRIC_API_KEY = os.getenv("CRIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 🤖 GEMINI SETUP
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# 📡 API
url = f"https://api.cricapi.com/v1/currentMatches?apikey={CRIC_API_KEY}&offset=0"

# 🧠 MEMORY (ANTI-SPAM)
sent_results = set()
sent_toss = set()
sent_prematch = set()
last_score = {}

# 📢 SEND MESSAGE (BOLD ENABLED)
def send_telegram(message):
    send_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(send_url, data=data)

# 📢 SEND PHOTO
def send_photo(photo_path, caption=""):
    send_url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    data = {
        "chat_id": CHAT_ID,
        "caption": caption,
        "parse_mode": "Markdown"
    }
    files = {"photo": open(photo_path, "rb")}
    requests.post(send_url, data=data, files=files)

# 🤖 GEMINI TEXT
def generate_text(prompt):
    try:
        res = model.generate_content(prompt)
        return res.text.strip()
    except:
        return prompt

# 🎨 POSTER TEXT
def generate_poster_text(team1, team2, result):
    prompt = f"Create a bold short cricket headline: {team1} vs {team2}, {result}"
    return generate_text(prompt)

# 🎨 CREATE POSTER
def create_poster(team1, team2, result):
    headline = generate_poster_text(team1, team2, result)

    img = Image.new('RGB', (900, 500), color=(15, 15, 40))
    draw = ImageDraw.Draw(img)

    try:
        big = ImageFont.truetype("arial.ttf", 60)
        mid = ImageFont.truetype("arial.ttf", 40)
        small = ImageFont.truetype("arial.ttf", 28)
    except:
        big = mid = small = ImageFont.load_default()

    draw.text((50, 50), "MATCH RESULT", font=small, fill="gray")
    draw.text((50, 150), f"{team1} vs {team2}", font=mid, fill="white")
    draw.text((50, 250), headline, font=big, fill="yellow")
    draw.text((50, 380), result, font=small, fill="lightgreen")

    filename = "poster.png"
    img.save(filename)
    return filename

# 🎯 MATCH FILTER (INDIA PRIORITY)
def select_matches(matches):
    india = []
    others = []

    for m in matches:
        teams = m.get("teams", [])
        if "India" in teams:
            india.append(m)
        else:
            others.append(m)

    return india if india else others

# 😴 ENGAGEMENT (NO MATCH)
def post_engagement():
    msg = generate_text("Create short engaging cricket content")
    send_telegram(f"🔥 {msg}")

# 🕒 TIME CONVERT
def get_time(match):
    dt = match.get("dateTimeGMT")
    if not dt:
        return "Time not available"

    try:
        utc = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
        ist = utc + timedelta(hours=5, minutes=30)
        return ist.strftime("%I:%M %p IST")
    except:
        return "Time error"

# 🚨 PRE MATCH
def post_prematch(match):
    mid = match["id"]
    if mid in sent_prematch:
        return

    t1, t2 = match["teams"]
    time_str = get_time(match)

    caption = generate_text(f"Hype cricket match: {t1} vs {t2}")

    msg = f"""
🚨 *MATCH STARTING*

🏏 *{t1}* 🆚 *{t2}*
🕒 *{time_str}*

🔥 {caption}
"""
    send_telegram(msg)
    sent_prematch.add(mid)

# 🎯 TOSS
def post_toss(match):
    mid = match["id"]
    if mid in sent_toss:
        return

    toss = match.get("tossWinner")
    choice = match.get("tossChoice")

    if toss:
        msg = generate_text(f"{toss} won toss and chose to {choice}")
        send_telegram(f"🎯 *TOSS UPDATE*\n\n{msg}")
        sent_toss.add(mid)

# 📊 LIVE SCORE (STYLE 3 + BOLD)
def post_live_score(match):
    mid = match["id"]
    score = match.get("score", [])

    if not score:
        return

    formatted = ""

    for inning in score:
        name = inning.get("inning", "")
        runs = inning.get("r", 0)
        wickets = inning.get("w", 0)
        overs = inning.get("o", 0)

        formatted += f"🏏 *{name}*\n"
        formatted += f"📊 *{runs}/{wickets}* • {overs} ov\n\n"

    if last_score.get(mid) != formatted:
        msg = f"""
📡 *LIVE UPDATE*

🏏 *{match['teams'][0].upper()}* 🆚 *{match['teams'][1].upper()}*

━━━━━━━━━━━━━━
{formatted}━━━━━━━━━━━━━━

🔥 *Stay tuned for next update!*
"""
        send_telegram(msg)
        last_score[mid] = formatted

# 🏆 RESULT (TEXT + POSTER)
def post_result(match):
    mid = match["id"]
    if mid in sent_results:
        return

    status = match.get("status", "")

    if "won" in status.lower():
        t1, t2 = match["teams"]

        send_telegram(f"🏆 *{status}*")

        poster = create_poster(t1, t2, status)
        caption = generate_text(f"{status} make exciting caption")

        send_photo(poster, f"🔥 {caption}")

        sent_results.add(mid)

# 🔁 MAIN LOOP
while True:
    try:
        res = requests.get(url).json()
        matches = res.get("data", [])

        selected = select_matches(matches)

        if not selected:
            post_engagement()

        for match in selected:
            post_prematch(match)
            post_toss(match)
            post_live_score(match)
            post_result(match)

        time.sleep(60)

    except Exception as e:
        print("Error:", e)
        time.sleep(60)