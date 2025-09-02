# Trail# main.py -- BATMAN Ultimate Machine (Groq only, no OpenAI)
import os, random, time, threading
from datetime import datetime

# ----- optional imports -----
import requests
try:
    import discord
    from discord.ext import commands
except Exception as e:
    print("Install discord.py: pip install discord.py")
    exit(1)

from flask import Flask

# ----------------------------
# Config / Globals
# ----------------------------
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

ONE_LINER_CHAR_LIMIT = 200
MEMORY_LIMIT = 10
AWAKEN_SECONDS = 120

memory = {}
blacklist = set()
awakening_until = 0
start_time = time.time()

EMOJI_BANK = ["🦇","😏","💀","🔥","😎","🙄","🤡","👀"]
ROASTS = [
    "Nice try. Next time bring better excuses.",
    "You mad? Cute.",
    "Leave the drama to Gotham.",
    "That's adorable. Truly."
]
CHILL_LINES = [
    "I hear you. Short answer: no.",
    "Do not test me.",
    "Got it. Move along."
]
DARK_LINES = [
    "Night decides. I obey.",
    "Shadows have votes, and they voted you off."
]

def now_ts():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

def store_memory(uid, text):
    arr = memory.setdefault(uid, [])
    arr.append(text[-ONE_LINER_CHAR_LIMIT:])
    if len(arr) > MEMORY_LIMIT:
        memory[uid] = arr[-MEMORY_LIMIT:]

def uptime_text():
    s = int(time.time() - start_time)
    h = s // 3600; m = (s % 3600) // 60; sec = s % 60
    return f"{h}h {m}m {sec}s"

# ----------------------------
# Groq API
# ----------------------------
def groq_query(prompt: str, max_tokens: int = 120) -> str:
    try:
        url = "https://api.groq.ai/v1/complete"
        headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
        payload = {"prompt": prompt, "max_tokens": max_tokens, "temperature": 0.8}
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if "completion" in data:
                return str(data["completion"]).strip()
            if "choices" in data and len(data["choices"])>0 and "text" in data["choices"][0]:
                return str(data["choices"][0]["text"]).strip()
            return str(data).strip()
        else:
            return f"🦇 (Groq error {r.status_code})"
    except Exception as e:
        return f"🦇 (Groq fail: {e})"

def local_generator(user_id, user_msg, awakened=False):
    store_memory(user_id, user_msg)
    mem = " | ".join(memory.get(user_id,[])[-3:])
    style = random.random()
    if awakened:
        pool = DARK_LINES + ROASTS
    elif style < 0.25:
        pool = ROASTS
    elif style < 0.6:
        pool = CHILL_LINES
    else:
        pool = [f"{random.choice(['I hear you','Look','Listen up'])}: {user_msg.split()[:5]}"] + CHILL_LINES
    base = random.choice(pool)
    suffix = random.choice(EMOJI_BANK) if random.random() < 0.6 else ""
    final = f"{base}{(' — '+mem) if random.random()<0.2 and mem else ''}{(' '+suffix) if suffix else ''}"
    return final[:ONE_LINER_CHAR_LIMIT]

async def generate_reply(user_id, user_msg, awakened=False):
    prompt = f"Batman dark-witty one-liner reply: \"{user_msg}\""
    if GROQ_KEY:
        out = groq_query(prompt, max_tokens=90)
        if out:
            return out.strip()[:ONE_LINER_CHAR_LIMIT]
    return local_generator(user_id, user_msg, awakened=awakened)

# ----------------------------
# Keep-alive server (Flask)
# ----------------------------
app = Flask("batman_alive")
@app.route("/")
def home(): return "Batman awake. " + now_ts()
def start_keepalive():
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True).start()
    print("Keep-alive server started on port 8080.")

# ----------------------------
# Discord Bot
# ----------------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

def is_owner_or_admin(member):
    try: return member.guild is not None and (member.id == member.guild.owner_id or member.guild_permissions.administrator)
    except: return False

@bot.event
async def on_ready():
    print(f"🦇 Batman online as {bot.user} — {now_ts()}")
    start_keepalive()

@bot.command(name="blacklist")
async def cmd_blacklist(ctx, member: discord.Member = None):
    if not is_owner_or_admin(ctx.author): return await ctx.send("🦇 Only admins.")
    if not member: return await ctx.send("🦇 Mention someone.")
    blacklist.add(member.id)
    await ctx.send(f"🚫 {member.mention} blacklisted.")

@bot.command(name="unblacklist")
async def cmd_unblacklist(ctx, member: discord.Member = None):
    if not is_owner_or_admin(ctx.author): return await ctx.send("🦇 Only admins.")
    if member.id in blacklist:
        blacklist.remove(member.id)
        await ctx.send(f"✅ {member.mention} unblacklisted.")
    else:
        await ctx.send("❌ Not blacklisted.")

@bot.command(name="awakening")
async def cmd_awakening(ctx):
    global awakening_until
    if not is_owner_or_admin(ctx.author): return await ctx.send("🦇 Only admins.")
    awakening_until = time.time() + AWAKEN_SECONDS
    await ctx.send("⚡🦇 Awakened mode activated for 2 minutes!")

@bot.command(name="shutdown")
async def cmd_shutdown(ctx):
    if ctx.author.id == ctx.guild.owner_id:
        await ctx.send("🦇 Disappearing into the night...")
        await bot.close()
    else:
        await ctx.send("🦇 Only the owner may shut me down.")

@bot.command(name="status")
async def cmd_status(ctx):
    mode = "AWAKENED" if time.time() < awakening_until else "normal"
    await ctx.send(f"🦇 Mode: {mode} | Uptime: {uptime_text()} | Blacklisted: {len(blacklist)}")

@bot.event
async def on_message(message):
    global awakening_until
    if message.author.bot: return
    if message.author.id in blacklist: return
    uid = str(message.author.id)
    awakened = (time.time() < awakening_until)
    triggered = message.content.strip().startswith("!batman") or bot.user.mentioned_in(message) or "batman" in message.content.lower()
    if triggered:
        reply = await generate_reply(uid, message.content, awakened=awakened)
        await message.channel.send(reply)
    await bot.process_commands(message)

print("Starting Discord bot...")
bot.run(DISCORD_TOKEN)
