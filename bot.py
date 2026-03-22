import requests
import time
import random
import os
from datetime import datetime, timedelta
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont

# 🔐 ENV VARIABLES
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
CRIC_API_KEY = os.getenv("CRIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 🤖 GEMINI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# 📡 API
url = f"https://api.cricapi.com/v1/currentMatches?apikey={CRIC_API_KEY}&offset=0"

# 🧠 MEMORY
sent_results = set()
sent_toss = set()
sent_prematch = set()
last_score = {}
last_live_time = {}

# ⏱️ ENGAGEMENT CONTROL
last_engagement_time = 0
used_posts = []

# 📢 SEND MESSAGE
def send_telegram(message):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    )

# 📢 SEND PHOTO
def send_photo(path, caption=""):
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
        data={"chat_id": CHAT_ID, "caption": caption, "parse_mode": "Markdown"},
        files={"photo": open(path, "rb")}
    )

# 🤖 AI TEXT
def generate_text(prompt):
    try:
        return model.generate_content(prompt).text.strip()
    except:
        return prompt

# 🎨 POSTER
def create_poster(t1, t2, result):
    headline = generate_text(f"Short cricket headline: {t1} vs {t2}, {result}")

    img = Image.new('RGB', (900, 500), color=(15, 15, 40))
    draw = ImageDraw.Draw(img)

    try:
        big = ImageFont.truetype("arial.ttf", 60)
        mid = ImageFont.truetype("arial.ttf", 40)
        small = ImageFont.truetype("arial.ttf", 28)
    except:
        big = mid = small = ImageFont.load_default()

    draw.text((50, 50), "MATCH RESULT", font=small, fill="gray")
    draw.text((50, 150), f"{t1} vs {t2}", font=mid, fill="white")
    draw.text((50, 250), headline, font=big, fill="yellow")
    draw.text((50, 380), result, font=small, fill="lightgreen")

    img.save("poster.png")
    return "poster.png"

# 🎯 FILTER
def select_matches(matches):
    india = [m for m in matches if "India" in m.get("teams", [])]
    return india if india else matches

# 😴 ENGAGEMENT (2 HOURS + UNIQUE)
def post_engagement():
    global last_engagement_time, used_posts

    if time.time() - last_engagement_time < 7200:
        return

    prompts = [
        "Create a viral cricket debate under 15 words with emojis",
        "Create a cricket quiz question with emojis",
        "Create a bold cricket opinion",
        "Create a hype cricket post",
        "Create a controversial cricket take"
    ]

    msg = generate_text(random.choice(prompts))

    if msg in used_posts:
        return

    used_posts.append(msg)
    if len(used_posts) > 10:
        used_posts.pop(0)

    send_telegram(f"🔥 {msg}")
    last_engagement_time = time.time()

# 🕒 TIME
def get_time(match):
    dt = match.get("dateTimeGMT")
    if not dt:
        return "Time N/A"
    try:
        ist = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S") + timedelta(hours=5, minutes=30)
        return ist.strftime("%I:%M %p IST")
    except:
        return "Time error"

# 🚨 PREMATCH
def post_prematch(match):
    mid = match["id"]
    if mid in sent_prematch:
        return

    t1, t2 = match["teams"]
    msg = generate_text(f"Hype cricket match: {t1} vs {t2}")

    send_telegram(f"🚨 *MATCH STARTING*\n\n🏏 *{t1}* 🆚 *{t2}*\n🕒 *{get_time(match)}*\n\n🔥 {msg}")
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

# 📊 LIVE SCORE (5 MIN DELAY)
def post_live_score(match):
    mid = match["id"]
    score = match.get("score", [])

    if not score:
        return

    if mid in last_live_time and time.time() - last_live_time[mid] < 300:
        return

    formatted = ""
    for i in score:
        formatted += f"🏏 *{i.get('inning','')}*\n📊 *{i.get('r',0)}/{i.get('w',0)}* • {i.get('o',0)} ov\n\n"

    if last_score.get(mid) != formatted:
        send_telegram(f"📡 *LIVE UPDATE*\n\n🏏 *{match['teams'][0].upper()}* 🆚 *{match['teams'][1].upper()}*\n\n━━━━━━━━━━━━━━\n{formatted}━━━━━━━━━━━━━━")
        last_score[mid] = formatted
        last_live_time[mid] = time.time()

# 🏆 RESULT
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

# 🔁 LOOP
while True:
    try:
        matches = requests.get(url).json().get("data", [])

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
