import random
import asyncio
import os
import datetime
import requests
from telegram import Bot
from google import genai

# =========================
# 🔐 ENV
# =========================
TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CRIC_API_KEY = os.getenv("CRIC_API_KEY")

# ✅ MULTI CHANNEL SUPPORT
CHANNELS = [
    "@The3rdUmpire",
    "@+nf9XmHWubCJhYzI1"
]

bot = Bot(token=TOKEN)
client = genai.Client(api_key=GEMINI_API_KEY)

# =========================
# ⚙️ CONFIG
# =========================
FAST_INTERVAL = 1800   # 30 min (match day)
SLOW_INTERVAL = 5400   # 90 min (no match)

# =========================
# 🌍 MATCH CHECK
# =========================
def has_match_today():
    try:
        url = f"https://api.cricapi.com/v1/cricScore?apikey={CRIC_API_KEY}"
        data = requests.get(url).json()

        today = str(datetime.date.today())

        for m in data.get("data", []):
            if today in m.get("dateTimeGMT", ""):
                return True
        return False
    except:
        return False

# =========================
# 🧠 TIME PHASE
# =========================
def get_phase():
    hour = datetime.datetime.now().hour

    if 6 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "afternoon"
    elif 18 <= hour < 23:
        return "evening"
    else:
        return "night"

# =========================
# 🔥 CONTENT SYSTEM
# =========================

def hook_curiosity():
    return random.choice([
        "👀 Aaj kuch alag hone wala hai...",
        "⚠️ Aaj ka match simple nahi hai...",
        "💣 Hidden factor hai...",
        "🔥 Aaj ka game predictable nahi hai...",
        "👀 Sirf 1% log samjhenge...",
        "💭 Result shock kar sakta hai...",
        "🚨 Clue mil chuka hai...",
        "👀 Repeat karo aur samajho..."
    ])

def hook_fomo():
    return random.choice([
        "🚨 LAST MOMENT UPDATE 🚨",
        "⚡ Final decision time!",
        "🔥 Abhi decide karo...",
        "⏳ Time khatam ho raha hai...",
        "🚨 Last chance...",
        "💣 Final signal mil gaya..."
    ])

def hook_controversy():
    return random.choice([
        "👀 Yeh match suspicious lag raha hai...",
        "💣 Public ek side ja rahi hai… risky 👀",
        "⚠️ Kuch toh gadbad hai...",
        "🧠 Smart users opposite ja rahe hain...",
        "🔥 Itna easy match kabhi hota hai kya?"
    ])

def hook_authority():
    return random.choice([
        "📊 Data kuch aur keh raha hai...",
        "🧠 Experts ka signal aa gaya...",
        "📈 Stats strong side dikha rahe...",
        "⚡ Pattern repeat ho raha hai..."
    ])

def reaction_post():
    return random.choice([
        "👍 Like karo agar confident ho",
        "🔥 Fire drop karo agar ready ho",
        "💯 Real players react karenge",
        "⚡ Silent mat rehna… react karo"
    ])

def fake_poll_post():
    return random.choice([
        "🏏 Winner?\n\n👍 Team A\n🔥 Team B",
        "⚡ Match?\n\n❤️ Easy\n😱 Tough",
        "📊 Score?\n\n🔥 High\n🧊 Low"
    ])

def trap_post():
    return random.choice([
        "👀 Jo samajh gaya wahi jeetega",
        "⚠️ Sabko samajh nahi aayega",
        "💣 Yeh normal match nahi hai",
        "🧠 Sirf smart log pakdenge"
    ])

# =========================
# 🤖 AI POST
# =========================
def ai_post(phase):
    prompt = f"""
Create a short cricket Telegram engagement post.
Time: {phase}
Make it engaging and human.
1-2 lines only.
"""

    try:
        res = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return res.text.strip()
    except:
        return "🔥 Aaj ka match interesting lag raha hai..."

# =========================
# 🎨 STYLE SYSTEM
# =========================
def style_text(text):
    styles = [
        lambda t: t,
        lambda t: f"🔥 {t}",
        lambda t: f"{t}\n\n⚡",
        lambda t: t.upper(),
        lambda t: f"\n{t}\n",
        lambda t: f"🚨 {t} 🚨",
        lambda t: f"💬 {t}",
        lambda t: f"🔥🔥 {t} 🔥🔥",
        lambda t: f"👇 {t}",
    ]
    return random.choice(styles)(text)

# =========================
# 🎭 GENERATOR
# =========================
def generate_post(phase):

    pool = [
        hook_curiosity,
        hook_fomo,
        hook_controversy,
        hook_authority,
        reaction_post,
        fake_poll_post,
        trap_post
    ]

    if random.random() < 0.85:
        raw = random.choice(pool)()
    else:
        raw = ai_post(phase)

    return style_text(raw)

# =========================
# 📤 SEND MULTI CHANNEL
# =========================
async def send_all(msg):
    for ch in CHANNELS:
        try:
            await bot.send_message(chat_id=ch, text=msg)
        except Exception as e:
            print(f"❌ Failed {ch}: {e}")

# =========================
# 🚀 MAIN LOOP
# =========================
async def run_bot():
    while True:
        try:
            phase = get_phase()
            match_today = has_match_today()

            msg = generate_post(phase)

            await send_all(msg)

            print(f"✅ Posted ({phase})")

            if match_today:
                await asyncio.sleep(FAST_INTERVAL)
            else:
                await asyncio.sleep(SLOW_INTERVAL)

        except Exception as e:
            print("❌ Error:", e)
            await asyncio.sleep(60)

# =========================
# ▶️ START
# =========================
if __name__ == "__main__":
    asyncio.run(run_bot())
