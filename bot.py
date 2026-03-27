import random
import asyncio
import requests
import datetime
import os
import json
import time
from telegram import Bot
from PIL import Image, ImageDraw

# =========================
# 🔐 ENV
# =========================
TOKEN = os.getenv("TOKEN")
CHANNELS = os.getenv("CHANNELS")
CRIC_API_KEY = os.getenv("CRIC_API_KEY")

bot = Bot(token=TOKEN)

# =========================
# ⚙️ CONFIG
# =========================
POST_INTERVAL = 600
LIVE_POLL_INTERVAL = 900

# =========================
# 🕒 IST TIME
# =========================
from datetime import timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30))

# =========================
# 💾 DATABASE
# =========================
DB_FILE = "db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

db = load_db()

# =========================
# 📡 CHANNEL SYSTEM
# =========================
def get_channels():
    return [c.strip() for c in CHANNELS.split(",") if c.strip()]

async def send_all_message(text):
    for ch in get_channels():
        try:
            await bot.send_message(ch, text)
        except Exception as e:
            print("Msg error:", e)

async def send_all_photo(path):
    for ch in get_channels():
        try:
            with open(path, "rb") as p:
                await bot.send_photo(ch, p)
        except Exception as e:
            print("Photo error:", e)

async def send_all_poll(q, options):
    for ch in get_channels():
        try:
            await bot.send_poll(ch, question=q, options=options, is_anonymous=False)
        except Exception as e:
            print("Poll error:", e)

# =========================
# 🌍 IPL FILTER
# =========================
def is_ipl_match(m):
    return "IPL" in m.get("series", "") or "Indian Premier League" in m.get("series", "")

# =========================
# 🌍 MATCH FETCH
# =========================
def get_today_matches():
    try:
        url = f"https://api.cricapi.com/v1/cricScore?apikey={CRIC_API_KEY}"
        data = requests.get(url).json()

        today = str(datetime.date.today())
        matches = []

        for m in data.get("data", []):
            dt = m.get("dateTimeGMT")
            t1 = m.get("t1")
            t2 = m.get("t2")

            if not (dt and t1 and t2):
                continue
            if today not in dt:
                continue
            if not is_ipl_match(m):
                continue

            mt = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")

            matches.append({
                "t1": t1,
                "t2": t2,
                "time": mt
            })

        return matches

    except Exception as e:
        print("Fetch error:", e)
        return []

# =========================
# 🎨 POSTER
# =========================
def create_poster(t1, t2, title):
    img = Image.new("RGB", (900, 900), (10, 10, 30))
    draw = ImageDraw.Draw(img)

    draw.text((200, 250), f"{t1} vs {t2}", fill="white")
    draw.text((250, 400), title, fill="yellow")

    path = f"{t1}_{t2}_{int(time.time())}.png"
    img.save(path)
    return path

# =========================
# 🧠 CONTEXT POSTS
# =========================
def contextual_post(t1, t2, phase):
    if phase == "early":
        return f"🏏 {t1} vs {t2} — Big IPL clash today."
    if phase == "mid":
        return f"📊 {t1} vs {t2} — Match depends on batting."
    if phase == "final":
        return f"🚨 {t1} vs {t2} — Final moments before toss."
    if phase == "live":
        return f"🔥 {t1} vs {t2} LIVE now!"

# =========================
# 🔥 ENGAGEMENT POSTS
# =========================
def engagement_post(t1, t2, phase):

    if phase == "early":
        return random.choice([
            f"👀 {t1} vs {t2}\n\nKaun strong lag raha hai?\n\n👍 {t1}\n🔥 {t2}",
            f"📊 {t1} vs {t2}\n\nMatch kispe depend karega?\n\n👍 Batting\n🔥 Bowling"
        ])

    if phase == "mid":
        return random.choice([
            f"📈 {t1} vs {t2}\n\nKaun dominate karega?\n\n👍 {t1}\n🔥 {t2}",
            f"👀 Match interesting ho raha hai...\n\n👍 {t1}\n🔥 {t2}"
        ])

    if phase == "final":
        return random.choice([
            f"🚨 FINAL CALL\n\n🏏 {t1} vs {t2}\n\n👍 {t1}\n🔥 {t2}",
            f"💣 Public ek side ja rahi hai...\n\n👍 {t1}\n🔥 {t2}"
        ])

    if phase == "live":
        return random.choice([
            f"🔥 LIVE: {t1} vs {t2}\n\nAb kaun jeetega?\n\n👍 {t1}\n🔥 {t2}",
            f"📊 Turning point!\n\n👍 {t1}\n🔥 {t2}"
        ])

# =========================
# 🔒 MEMORY
# =========================
announced = db.get("announced", {})
live_sent = db.get("live_sent", {})
last_post = {}
last_poll = {}

# =========================
# 🚀 MAIN LOOP
# =========================
async def run_bot():
    global db

    while True:
        try:
            now = datetime.datetime.now(IST)
            matches = get_today_matches()

            if not matches:
                await asyncio.sleep(1800)
                continue

            for m in matches:
                t1, t2 = m["t1"], m["t2"]
                mt = m["time"] + timedelta(hours=5, minutes=30)
                key = f"{t1}_{t2}"

                # 🟡 ANNOUNCEMENT
                if key not in announced:
                    time_str = mt.strftime("%I:%M %p IST")

                    await send_all_message(
                        f"🔥 TODAY IPL MATCH\n🏏 {t1} vs {t2}\n🕒 {time_str}"
                    )

                    await send_all_photo(create_poster(t1, t2, "Match Day"))

                    announced[key] = True
                    db["announced"] = announced
                    save_db(db)

                # ⏳ BEFORE MATCH
                if now < mt:
                    last = last_post.get(key)

                    if not last or (now - last).total_seconds() > POST_INTERVAL:

                        mins = int((mt - now).total_seconds() / 60)

                        if mins > 60:
                            phase = "early"
                        elif mins > 20:
                            phase = "mid"
                        else:
                            phase = "final"

                        # context + engagement combo
                        await send_all_message(contextual_post(t1, t2, phase))
                        await send_all_message(engagement_post(t1, t2, phase))

                        await send_all_photo(create_poster(t1, t2, "Starting Soon"))

                        if mins <= 30:
                            await send_all_poll(
                                f"{t1} vs {t2} — Who will win?",
                                [t1, t2]
                            )

                        last_post[key] = now

                # 🔥 LIVE MATCH
                if now >= mt:

                    if key not in live_sent:
                        await send_all_message(f"🔥 MATCH LIVE\n🏏 {t1} vs {t2}")

                        live_sent[key] = True
                        db["live_sent"] = live_sent
                        save_db(db)

                    last = last_poll.get(key)

                    if not last or (now - last).total_seconds() > LIVE_POLL_INTERVAL:

                        await send_all_message(engagement_post(t1, t2, "live"))

                        await send_all_poll(
                            f"{t1} vs {t2}",
                            ["Who will win?", "High scoring?"]
                        )

                        last_poll[key] = now

            await asyncio.sleep(60)

        except Exception as e:
            print("Error:", e)
            await asyncio.sleep(60)

# =========================
# ▶️ START
# =========================
if __name__ == "__main__":
    asyncio.run(run_bot())
