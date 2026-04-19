import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timezone, timedelta
import asyncio
import sqlite3
import os
import re
import requests
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import base64
import json
from collections import deque

# ═══════════════════════════════════════════════════════════════════
# 🔧 FLASK SERVER (24/7 Keep-Alive)
# ═══════════════════════════════════════════════════════════════════

app = Flask('')
load_dotenv()

@app.route('/')
def home():
    return "🛡️ Guard Security & 𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 Pro Online!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    Thread(target=run, daemon=True).start()

# ═══════════════════════════════════════════════════════════════════
# 🔐 GUARD SECURITY BOT - Configuration
# ═══════════════════════════════════════════════════════════════════

# Use a single bot token from environment variables for deployment.
# Keep DISCORD_TOKEN set in production environments like GitHub or Render.
GUARD_TOKEN = os.environ.get("DISCORD_TOKEN") or os.environ.get("GUARD_TOKEN")

if not GUARD_TOKEN:
    raise RuntimeError("Missing Discord bot token. Set DISCORD_TOKEN environment variable.")

AUTO_ROLE_NAME = "『👥』𝔻ℂ 𝕄𝔼𝕄𝔹𝔼ℝ𝕊"
LOG_CHANNEL_NAME = "『⌛』𝕃𝕆𝔾"
AI_CHANNEL_NAME = "『💬』𝔸𝕀『』ℂℍ𝔸𝕋"
ADMIN_CHANNEL_NAME = "『💬』𝕋𝔼ℂ『』ℂℍ𝔸𝕋"
OWNER_ID = 1092920889189859349
RAID_THRESHOLD = 3
MASS_ACTION_THRESHOLD = 5
TIME_WINDOW = 10
NEW_USER_COOLDOWN = 7
TRUST_TIME_MINUTES = 1440

SCAM_PATTERNS = [
    r"nasewin", r"crypto", r"giveaway", r"promocode", r"usdt", r"claim", r"free money", r"bit\.ly", r"t\.me"
]

FORBIDDEN_EXTENSIONS = ['.svg', '.html', '.js', '.bat', '.scr', '.exe', '.com', '.zip', '.rar']

deletion_counter = {}
mass_action_counter = {}
daily_threats_blocked = 0

# ═══════════════════════════════════════════════════════════════════
# 🤖 𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 AI BOT - Configuration
# ═══════════════════════════════════════════════════════════════════

GEMINI_KEY = os.environ.get("GEMINI_KEY")
OPENAI_KEY = os.environ.get("OPENAI_KEY")
CLAUDE_KEY = os.environ.get("CLAUDE_KEY")
AI_CHANNEL_ID = int(os.environ.get("AI_CHANNEL_ID", "1349727143009189998"))
AI_CHANNEL_NAME = "『💬』𝔸𝕀『』ℂℍ𝔸𝕋"  # Channel name for multi-server support
ADMIN_CHANNEL_NAME = "『💬』𝕋𝔼ℂ『』ℂℍ𝔸𝕋"  # Admin commands channel (moderation/reports)
SYSTEM_PROMPT = "შენ ხარ '𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖'. ისაუბრე გამართული ქართულით."

# Voice Stats Configuration
VOICE_STATS_CHANNEL_ID = int(os.environ.get("VOICE_STATS_CHANNEL_ID", "1495491517136244878"))  # Voice channel ID for online count display
VOICE_STATS_UPDATE_INTERVAL = int(os.environ.get("VOICE_STATS_UPDATE_INTERVAL", "1"))  # Update interval in seconds
VOICE_STATS_INCLUDE_BOTS = os.environ.get("VOICE_STATS_INCLUDE_BOTS", "false").lower() == "true"  # Include bots in count
VOICE_STATS_STATUSES = os.environ.get("VOICE_STATS_STATUSES", "online,idle").split(",")  # Statuses to count as online

# In-memory per-channel AI mode (enabled/disabled for each channel)
channel_ai_modes = {}  # {channel_id: True/False}

# ═══════════════════════════════════════════════════════════════════
# 🤝 UNIFIED BOT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

intents = discord.Intents.all()

# Modern slash prefix (/)
def prefix_function(bot, message):
    return ['/']

bot = commands.Bot(command_prefix=prefix_function, intents=intents, help_command=None)

# ═══════════════════════════════════════════════════════════════════
# 💾 DATABASE SETUP (Enhanced with AI Features)
# ═══════════════════════════════════════════════════════════════════

conn = sqlite3.connect('guard_data.db', check_same_thread=False)
cursor = conn.cursor()

# Security tables
cursor.execute('CREATE TABLE IF NOT EXISTS bad_words (word TEXT PRIMARY KEY)')
cursor.execute('CREATE TABLE IF NOT EXISTS warnings (user_id INTEGER, count INTEGER DEFAULT 0)')

# 🤖 AI Enhancement Tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS conversation_history (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    channel_id INTEGER,
    role TEXT,
    message TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS custom_prompts (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    user_id INTEGER,
    prompt_name TEXT,
    prompt_content TEXT,
    language TEXT DEFAULT 'ka'
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS llm_settings (
    user_id INTEGER PRIMARY KEY,
    preferred_llm TEXT DEFAULT 'gemini',
    model_config TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS token_tracking (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    tokens_used INTEGER,
    api_used TEXT,
    date_time DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS georgian_preferences (
    user_id INTEGER PRIMARY KEY,
    georgian_mode BOOLEAN DEFAULT 1,
    formatting_style TEXT DEFAULT 'traditional'
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_warnings (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_mutes (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    duration_minutes INTEGER,
    reason TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_bans (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS user_reports (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    reporter_id INTEGER,
    reported_user_id INTEGER,
    reason TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS general_reports (
    id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    reporter_id INTEGER,
    report_type TEXT,
    description TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS channel_ai_settings (
    channel_id INTEGER PRIMARY KEY,
    guild_id INTEGER,
    ai_enabled BOOLEAN DEFAULT 1,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

conn.commit()

# In-memory conversation cache per channel (for faster access)
conversation_cache = {}

# ═══════════════════════════════════════════════════════════════════
# 🛠️ HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_readable_permissions(perms):
    """Convert permission tuples to readable format"""
    active_perms = [p_name for p_name, value in perms if value]
    if not active_perms:
        return "❌ უფლებების გარეშე"
    formatted_list = [f"✅ {p.replace('_', ' ').title()}" for p in active_perms]
    return "\n".join(formatted_list[:15]) + (f"\n...და კიდევ {len(formatted_list)-15} სხვა" if len(formatted_list) > 15 else "")

def has_role(user, role_name):
    """Check if user has a specific role by name"""
    return any(role.name == role_name for role in user.roles)

def is_admin(user):
    """Check if user has administrator permissions"""
    return user.guild_permissions.administrator

def get_log_channel(guild: discord.Guild) -> discord.TextChannel | None:
    """Find the logging channel by name in the guild."""
    if not guild:
        return None
    for channel in guild.text_channels:
        if channel.name == LOG_CHANNEL_NAME:
            return channel
    return None

async def send_log(title, member, reason, color=discord.Color.blue(), extra_info=None, guild=None):
    """Send log message to log channel"""
    if guild is None and member is not None:
        guild = member.guild if hasattr(member, 'guild') else None
    channel = get_log_channel(guild) if guild else None
    if not channel:
        return
    embed = discord.Embed(title=title, color=color, timestamp=datetime.now(timezone.utc))
    if member:
        embed.add_field(name="შემსრულებელი:", value=f"{member.mention} ({member.id})", inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="ქმედება/მიზეზი:", value=reason, inline=False)
    if extra_info:
        embed.add_field(name="დეტალები:", value=extra_info, inline=False)
    await channel.send(embed=embed)

async def handle_violation(member, reason, message_content=None, is_scam=False):
    """Handle security violations"""
    global daily_threats_blocked
    daily_threats_blocked += 1
    user_id = member.id
    cursor.execute("SELECT count FROM warnings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    count = (row[0] + 1) if row else 1
    cursor.execute("INSERT OR REPLACE INTO warnings (user_id, count) VALUES (?, ?)", (user_id, count))
    conn.commit()
    mins = 1440 if is_scam else (60 if count >= 3 else (10 if count == 2 else 1))
    try:
        await member.timeout(timedelta(minutes=mins), reason=reason)
        await send_log("🛑 SECURITY ALERT", member, reason, color=discord.Color.red(), extra_info=f"ვარნი #{count} | სასჯელი: {mins} წთ\nტექსტი: {message_content}")
    except:
        pass

# ═══════════════════════════════════════════════════════════════════
# 🔍 CHANNEL & MODERATION HELPERS
# ═══════════════════════════════════════════════════════════════════

def is_ai_chat_channel(channel) -> bool:
    """Check if channel is AI chat by name"""
    return channel.name == AI_CHANNEL_NAME

def is_admin_channel(channel) -> bool:
    """Check if channel is admin channel by name"""
    return channel.name == ADMIN_CHANNEL_NAME

def is_channel_ai_enabled(channel_id: int) -> bool:
    """Check if AI is enabled for a specific channel"""
    global channel_ai_modes
    # First check if it's the main AI channel by name
    channel = bot.get_channel(channel_id)
    if channel and is_ai_chat_channel(channel):
        return True
    # Then check custom settings
    if channel_id in channel_ai_modes:
        return channel_ai_modes[channel_id]
    return False

def set_channel_ai_mode(channel_id: int, guild_id: int, enabled: bool):
    """Set AI mode for a specific channel"""
    global channel_ai_modes
    channel_ai_modes[channel_id] = enabled
    cursor.execute(
        "INSERT OR REPLACE INTO channel_ai_settings (channel_id, guild_id, ai_enabled) VALUES (?, ?, ?)",
        (channel_id, guild_id, enabled)
    )
    conn.commit()

def add_warning(guild_id: int, user_id: int, moderator_id: int, reason: str) -> int:
    """Add warning to user and return total warns"""
    cursor.execute(
        "INSERT INTO user_warnings (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
        (guild_id, user_id, moderator_id, reason)
    )
    cursor.execute("SELECT COUNT(*) FROM user_warnings WHERE guild_id = ? AND user_id = ?", (guild_id, user_id))
    total = cursor.fetchone()[0]
    conn.commit()
    return total

def add_mute(guild_id: int, user_id: int, moderator_id: int, minutes: int, reason: str):
    """Add mute record"""
    cursor.execute(
        "INSERT INTO user_mutes (guild_id, user_id, moderator_id, duration_minutes, reason) VALUES (?, ?, ?, ?, ?)",
        (guild_id, user_id, moderator_id, minutes, reason)
    )
    conn.commit()

def add_ban(guild_id: int, user_id: int, moderator_id: int, reason: str):
    """Add ban record"""
    cursor.execute(
        "INSERT INTO user_bans (guild_id, user_id, moderator_id, reason) VALUES (?, ?, ?, ?)",
        (guild_id, user_id, moderator_id, reason)
    )
    conn.commit()

def add_report(guild_id: int, reporter_id: int, reported_user_id: int, reason: str):
    """Add user report"""
    cursor.execute(
        "INSERT INTO user_reports (guild_id, reporter_id, reported_user_id, reason) VALUES (?, ?, ?, ?)",
        (guild_id, reporter_id, reported_user_id, reason)
    )
    conn.commit()

def add_general_report(guild_id: int, reporter_id: int, report_type: str, description: str):
    """Add general report (bug, help request, etc.)"""
    cursor.execute(
        "INSERT INTO general_reports (guild_id, reporter_id, report_type, description) VALUES (?, ?, ?, ?)",
        (guild_id, reporter_id, report_type, description)
    )
    conn.commit()

def get_user_warnings(guild_id: int, user_id: int) -> list:
    """Get all warnings for a user"""
    cursor.execute(
        "SELECT reason, timestamp FROM user_warnings WHERE guild_id = ? AND user_id = ? ORDER BY timestamp DESC",
        (guild_id, user_id)
    )
    return cursor.fetchall()

def get_user_mutes(guild_id: int, user_id: int) -> list:
    """Get all mutes for a user"""
    cursor.execute(
        "SELECT reason, duration_minutes, timestamp FROM user_mutes WHERE guild_id = ? AND user_id = ?",
        (guild_id, user_id)
    )
    return cursor.fetchall()

def get_all_warnings(guild_id: int) -> list:
    """Get all warnings in a guild"""
    cursor.execute(
        "SELECT user_id, COUNT(*) as count FROM user_warnings WHERE guild_id = ? GROUP BY user_id ORDER BY count DESC",
        (guild_id,)
    )
    return cursor.fetchall()

def get_all_mutes(guild_id: int) -> list:
    """Get all mutes in a guild"""
    cursor.execute(
        "SELECT user_id, reason, duration_minutes, timestamp FROM user_mutes WHERE guild_id = ? ORDER BY timestamp DESC",
        (guild_id,)
    )
    return cursor.fetchall()

def get_all_bans(guild_id: int) -> list:
    """Get all bans in a guild"""
    cursor.execute(
        "SELECT user_id, reason, timestamp FROM user_bans WHERE guild_id = ? ORDER BY timestamp DESC",
        (guild_id,)
    )
    return cursor.fetchall()

def get_moderation_stats(guild_id: int) -> dict:
    """Get moderation statistics for guild"""
    cursor.execute("SELECT COUNT(*) FROM user_warnings WHERE guild_id = ?", (guild_id,))
    total_warns = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM user_mutes WHERE guild_id = ?", (guild_id,))
    total_mutes = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM user_bans WHERE guild_id = ?", (guild_id,))
    total_bans = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM user_reports WHERE guild_id = ?", (guild_id,))
    total_reports = cursor.fetchone()[0] or 0
    
    return {
        "warns": total_warns,
        "mutes": total_mutes,
        "bans": total_bans,
        "reports": total_reports
    }

def get_ai_stats(guild_id: int) -> dict:
    """Get AI statistics for guild"""
    # Count total AI messages in conversation history
    cursor.execute(
        "SELECT COUNT(*) FROM conversation_history WHERE role = 'assistant'"
    )
    total_ai_messages = cursor.fetchone()[0] or 0
    
    # Count total user messages in conversation history
    cursor.execute(
        "SELECT COUNT(*) FROM conversation_history WHERE role = 'user'"
    )
    total_user_messages = cursor.fetchone()[0] or 0
    
    # Count unique users who have used AI
    cursor.execute(
        "SELECT COUNT(DISTINCT user_id) FROM conversation_history"
    )
    unique_users = cursor.fetchone()[0] or 0
    
    # Count AI-enabled channels
    cursor.execute(
        "SELECT COUNT(*) FROM channel_ai_settings WHERE ai_enabled = 1"
    )
    ai_channels = cursor.fetchone()[0] or 0
    
    return {
        "ai_messages": total_ai_messages,
        "user_messages": total_user_messages,
        "unique_users": unique_users,
        "ai_channels": ai_channels
    }

def get_online_count(guild: discord.Guild) -> int:
    """Count online members based on configuration"""
    online_count = 0
    for member in guild.members:
        if not VOICE_STATS_INCLUDE_BOTS and member.bot:
            continue
        if str(member.status) in VOICE_STATS_STATUSES:
            online_count += 1
    return online_count

async def update_voice_stats_channel(guild: discord.Guild):
    """Update voice channel name with online count"""
    if VOICE_STATS_CHANNEL_ID == 0:
        return
    
    channel = guild.get_channel(VOICE_STATS_CHANNEL_ID)
    if not channel or not isinstance(channel, discord.VoiceChannel):
        return
    
    try:
        online_count = get_online_count(guild)
        new_name = f"🟢𝕆ℕ𝕃𝕀ℕ𝔼: {online_count}"
        await channel.edit(name=new_name)
    except Exception as e:
        print(f"Error updating voice stats channel: {e}")

# ═══════════════════════════════════════════════════════════════════
# 🤖 AI ENHANCEMENT FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_conversation_history(user_id: int, channel_id: int, limit: int = 5) -> list:
    """Retrieve conversation history for context awareness"""
    cursor.execute(
        '''
        SELECT role, message FROM conversation_history
        WHERE user_id = ? AND channel_id = ?
        ORDER BY timestamp DESC LIMIT ?
        ''',
        (user_id, channel_id, limit)
    )
    messages = cursor.fetchall()
    return list(reversed(messages))  # Return in chronological order

def save_conversation(user_id: int, channel_id: int, role: str, message: str):
    """Save message to conversation history"""
    cursor.execute(
        '''
        INSERT INTO conversation_history (user_id, channel_id, role, message)
        VALUES (?, ?, ?, ?)
        ''',
        (user_id, channel_id, role, message)
    )
    conn.commit()

def get_user_llm_preference(user_id: int) -> str:
    """Get user's preferred LLM"""
    cursor.execute("SELECT preferred_llm FROM llm_settings WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 'gemini'

def set_user_llm_preference(user_id: int, llm: str):
    """Set user's preferred LLM"""
    cursor.execute(
        "INSERT OR REPLACE INTO llm_settings (user_id, preferred_llm) VALUES (?, ?)",
        (user_id, llm)
    )
    conn.commit()

def get_custom_prompt(guild_id: int, prompt_name: str) -> str:
    """Retrieve custom system prompt"""
    cursor.execute(
        "SELECT prompt_content FROM custom_prompts WHERE guild_id = ? AND prompt_name = ?",
        (guild_id, prompt_name)
    )
    result = cursor.fetchone()
    return result[0] if result else None

def save_custom_prompt(guild_id: int, user_id: int, prompt_name: str, content: str):
    """Save custom system prompt"""
    cursor.execute(
        "INSERT OR REPLACE INTO custom_prompts (guild_id, user_id, prompt_name, prompt_content) VALUES (?, ?, ?, ?)",
        (guild_id, user_id, prompt_name, content)
    )
    conn.commit()

def track_token_usage(user_id: int, tokens: int, api_used: str):
    """Track API token usage"""
    cursor.execute(
        "INSERT INTO token_tracking (user_id, tokens_used, api_used) VALUES (?, ?, ?)",
        (user_id, tokens, api_used)
    )
    conn.commit()

def get_token_usage(user_id: int, days: int = 7) -> int:
    """Get token usage for past N days"""
    cursor.execute(
        '''
        SELECT SUM(tokens_used) FROM token_tracking
        WHERE user_id = ? AND date_time >= datetime('now', '-' || ? || ' days')
        ''',
        (user_id, days)
    )
    result = cursor.fetchone()
    return result[0] if result[0] else 0

def is_quality_response(response: str) -> bool:
    """Check if response meets quality standards"""
    if not response or len(response.strip()) < 10:
        return False
    if "Error" in response or "error" in response and len(response) < 50:
        return False
    return True

def optimize_prompt(original_prompt: str, history: list = None) -> str:
    """Optimize prompt with conversation context"""
    if not history:
        return original_prompt
    context = "\n".join([f"{role}: {msg[:100]}..." for role, msg in history[-3:]])
    return f"Previous context:\n{context}\n\nCurrent: {original_prompt}"

def georgian_format_response(text: str, style: str = 'traditional') -> str:
    """Apply Georgian language optimizations"""
    # Georgian punctuation and formatting
    georgian_patterns = {
        '!': '!',
        '?': '?',
        '.': '.',
    }
    # Add Georgian-friendly line breaks
    if style == 'traditional':
        text = text.replace('\n\n', '\n━━━━━━━━━━━━━\n')
    elif style == 'modern':
        text = text.replace('\n\n', '\n' + '─' * 20 + '\n')
    return text

def get_georgian_mode(user_id: int) -> bool:
    """Get user's Georgian mode preference"""
    cursor.execute("SELECT georgian_mode FROM georgian_preferences WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else True

async def retry_api_call(func, max_retries: int = 3, delay: float = 1.0):
    """Retry logic with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return await func() if asyncio.iscoroutinefunction(func) else func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(delay * (2 ** attempt))

async def enhanced_image_analysis(image_url: str, gemini_key: str) -> str:
    """Enhanced image analysis beyond OCR - object detection, scene description"""
    prompt = """ამ ფოტოს ეტიკეტიდან მიუთითეთ: 1. რა ობიექტები ხედავთ? 2. ფოტოს შინაარსი (სცენა, ადგილი, აქტივობა)? 3. ფერთა სქემა 4. ტექსტი (თუ აღსანიშნავი) პასუხი გაიცეთ სტრუქტურირებული ფორმატით."""
    parts = [{"text": prompt}]
    try:
        img_data = requests.get(image_url).content
        encoded_image = base64.b64encode(img_data).decode('utf-8')
        parts.append({"inline_data": {"mime_type": "image/jpeg", "data": encoded_image}})
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
        res = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=15)
        data = res.json()
        if 'candidates' in data:
            return data['candidates'][0]['content']['parts'][0]['text']
        return "ფოტოს ანალიზი ვერ მოხერხდა"
    except Exception as e:
        return f"❌ სურათის გამოანალიზება ვერ მოხერხდა: {str(e)[:50]}"

async def call_claude_api(messages: list, system_prompt: str = None) -> str:
    """Call Claude API for text generation"""
    try:
        headers = {
            "x-api-key": CLAUDE_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1024,
            "messages": messages
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        url = "https://api.anthropic.com/v1/messages"
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        data = res.json()
        
        if 'content' in data and data['content']:
            return data['content'][0]['text']
        return "Claude API ვერ გასცა პასუხი"
    except Exception as e:
        return f"❌ Claude API შეცდომა: {str(e)[:50]}"

# ═══════════════════════════════════════════════════════════════════
# 📊 VOICE STATS UPDATER
# ═══════════════════════════════════════════════════════════════════

@tasks.loop(seconds=VOICE_STATS_UPDATE_INTERVAL)
async def update_voice_stats():
    """Update voice channel with online count every configured interval"""
    for guild in bot.guilds:
        await update_voice_stats_channel(guild)

# ═══════════════════════════════════════════════════════════════════
# 🎯 READY EVENT (Unified)
# ═══════════════════════════════════════════════════════════════════

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    """Update voice stats when member status changes"""
    if before.status != after.status:
        await update_voice_stats_channel(after.guild)

# ═══════════════════════════════════════════════════════════════════
# 💬 HELP COMMANDS (Unified)
# ═══════════════════════════════════════════════════════════════════

@bot.tree.command(name="help", description="დახმარება Guard Security და 𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 Pro ფუნქციებისთვის")
async def help(interaction: discord.Interaction):
    """Combined help for both bots"""
    # Check permissions: only admins
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    embed = discord.Embed(
        title="🛡️ Guard Security & 𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 Pro - დახმარება",
        description="ორი ძლიერი ბოტი მოერთო! ამჟამად Slash ბრძანებები ხელმისაწვდომია.",
        color=0x3498db
    )
    # Guard Security Features
    embed.add_field(
        name="🛡️ Guard Security Features",
        value="• Anti-Raid Protection\n• Role Monitoring\n• Message Security\n• User Verification\n• Auto Logging",
        inline=False
    )
    # AI Features
    embed.add_field(
        name="🤖 𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 AI Features (Enhanced)",
        value="• 💬 AI Chat (Multi-LLM: Gemini, Claude)\n• 📝 OCR Recognition\n• 🌐 Link Summarization\n• 🎨 Image Generation\n• 🧠 Conversation Memory\n• 🔄 Token Optimization",
        inline=False
    )
    # Guard Commands
    embed.add_field(
        name="🔧 Slash Commands",
        value="/audit_search @user - User audit logs\n/get_snapshot - Server structure\n/set_llm - Choose AI model\n/help - This menu",
        inline=False
    )
    # AI Chat
    embed.add_field(
        name="💬 AI Chat",
        value="უბრალოდ AI ჩანელში დაწერე ან გამოიყენე /help ბრძანება",
        inline=False
    )
    # AI OCR
    embed.add_field(
        name="📝 OCR Analyzer",
        value="ჩააგდე ფოტო და დააწერე: **ამომიწერე ტექსტი**",
        inline=False
    )
    # AI Link Summarization
    embed.add_field(
        name="🌐 Link Summarization",
        value="ჩააგდე ლინკი - ბოტი ავტომატურად შეაჯამებს",
        inline=False
    )
    # Image Generation
    embed.add_field(
        name="🎨 Image Generation",
        value="დაწერე: **დამიგენერირე ფოტო [აღწერა]**",
        inline=False
    )
    # New Features
    embed.add_field(
        name="✨ New AI Enhancements",
        value="🧠 Conversation Memory - უახლოესი 5 შეტყობინება კონტექსტი\n🔄 Multi-LLM - Gemini, Claude მხარდაჭერა\n🎯 Image Analysis - ობიექტის აღმოჩენა и სცენის აღწერა\n📊 Token Tracking - API გამოყენების მონიტორინგი",
        inline=False
    )
    embed.set_footer(text="Guard Security & 𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 Pro Edition • 2026 | Powered by Modern Tech")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ═══════════════════════════════════════════════════════════════════
# 📝 SLASH COMMANDS - GUARD FEATURES
# ═══════════════════════════════════════════════════════════════════

@bot.tree.command(name="audit_search", description="მოდერატორის ბოლო 10 ქმედების ნახვა")
@app_commands.describe(user="რომელი მომხმარებლის ლოგები გაინტერესებს?")
async def audit_search(interaction: discord.Interaction, user: discord.Member):
    """Show user's recent audit log actions"""
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    if interaction.channel is None or interaction.channel.name != LOG_CHANNEL_NAME:
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {LOG_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    await interaction.response.defer(ephemeral=False)
    embed = discord.Embed(
        title=f"🔎 Audit Search: {user.display_name}",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_author(name=user.name, icon_url=user.display_avatar.url)
    logs_list = ""
    async for entry in interaction.guild.audit_logs(limit=10, user=user):
        action_name = str(entry.action).replace("AuditLogAction.", "").replace("_", " ").title()
        target = entry.target if entry.target else "უცნობი ობიექტი"
        time_ago = f"<t:{int(entry.created_at.timestamp())}:R>"
        logs_list += f"🔹 **{action_name}** | სამიზნე: {target} | {time_ago}\n"
    embed.description = logs_list if logs_list else "ამ მომხმარებლის ბოლო ქმედებები არ მოიძებნა."
    embed.set_footer(text="Guard Security Intelligence")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="get_snapshot", description="სერვერის სტრუქტურის შენახვა ტექსტურად")
async def get_snapshot(interaction: discord.Interaction):
    """Create and send server structure snapshot"""
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ ეს ბრძანება მხოლოჇ მფლობელისთვისაა!", ephemeral=True)
        return
    filename = f"snapshot_{interaction.guild.id}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"სერვერი: {interaction.guild.name}\n\n=== ჩანელები ===\n")
        for c in interaction.guild.channels:
            f.write(f"- {c.name} ({c.type})\n")
    await interaction.user.send("🛡️ სერვერის სნეპშოტი:", file=discord.File(filename))
    await interaction.response.send_message("✅ გამოგზავნილია DM-ში.", ephemeral=True)
    os.remove(filename)

@bot.tree.command(name="status", description="ბოტის სტატუსი, Gateway და AI ლიმიტები")
async def status(interaction: discord.Interaction):
    """Show bot status, gateway config, and AI limits"""
    # Only admins
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    # Only works in AI channel
    if not is_ai_chat_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {AI_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    await interaction.response.defer(ephemeral=True)
    
    latency = round(bot.latency * 1000)
    uptime_seconds = (datetime.now(timezone.utc) - bot.user.created_at).total_seconds()
    uptime_hours = int(uptime_seconds // 3600)
    uptime_mins = int((uptime_seconds % 3600) // 60)
    
    embed = discord.Embed(
        title="🤖 𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 AI Pro - სტატუსი",
        color=discord.Color.green(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="💚 ბოტი მდგომარეობა",
        value=f"🟢 Online | ⏱️ Ping: {latency}ms",
        inline=False
    )
    
    embed.add_field(
        name="🌐 Discord Gateway",
        value=f"Shard: 0 | Status: Connected | Latency: {latency}ms",
        inline=False
    )
    
    embed.add_field(
        name="🤖 AI მოდელი",
        value=f"Primary: Gemini 2.5 Flash\nSecondary: Claude 3.5 Sonnet\nTertiary: OpenAI DALL-E\nOCR: Enabled",
        inline=False
    )
    
    embed.add_field(
        name="📊 ლიმიტები",
        value=f"Requests/min: ∞\nToken limit: გამოწერილი\nChannels AI-enabled: Multiple",
        inline=False
    )
    
    embed.set_footer(text="Guard Security & 𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 Pro • v2.0")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="warn", description="მომხმარებელს გაფრთხოება")
@app_commands.describe(user="რომელი მომხმარებელი გავყავო?", reason="გაფრთხოების მიზეზი")
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str = "მიზეზი მითითებული არ არის"):
    """Warn a user"""
    # Only works in admin channel
    if not is_admin_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {ADMIN_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    warns = add_warning(interaction.guild.id, user.id, interaction.user.id, reason)
    
    embed = discord.Embed(
        title=f"⚠️ გაფრთხოება: {user.name}",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="მიზეზი:", value=reason, inline=False)
    embed.add_field(name="სულ გაფრთხოებები:", value=f"{warns}/3", inline=False)
    embed.set_footer(text=f"გაფრთხოებული: {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed)
    
    try:
        await user.send(f"⚠️ თქვენ გაფრთხოებული ხართ {interaction.guild.name}-ში!\nმიზეზი: {reason}\nმოსახლეობის გაფრთხოებები: {warns}/3")
    except:
        pass

@bot.tree.command(name="mute", description="მომხმარებელი დროებით და-mute")
@app_commands.describe(user="რომელი მომხმარებელი mute-ო?", minutes="რამდენი დღე? (1-40320)", reason="mute-ის მიზეზი")
async def mute(interaction: discord.Interaction, user: discord.Member, minutes: int = 60, reason: str = "მიზეზი მითითებული არ არის"):
    """Mute a user"""
    # Only works in admin channel
    if not is_admin_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {ADMIN_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    if minutes > 40320:
        minutes = 40320
    
    try:
        await user.timeout(timedelta(minutes=minutes), reason=reason)
        add_mute(interaction.guild.id, user.id, interaction.user.id, minutes, reason)
        
        embed = discord.Embed(
            title=f"🔇 Mute: {user.name}",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="ხანგრძლივობა:", value=f"{minutes} წთ", inline=False)
        embed.add_field(name="მიზეზი:", value=reason, inline=False)
        embed.set_footer(text=f"mute-ი: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
        await user.send(f"🔇 და-mute-ი ხართ {interaction.guild.name}-ში {minutes} წთ-ით!\nმიზეზი: {reason}")
    except Exception as e:
        await interaction.response.send_message(f"❌ შეცდომა: {str(e)}", ephemeral=True)

@bot.tree.command(name="ban", description="მომხმარებელი სერვერიდან ban-ი")
@app_commands.describe(user="რომელი მომხმარებელი ban-ი?", reason="ban-ის მიზეზი")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "მიზეზი მითითებული არ არის"):
    """Ban a user"""
    # Only works in admin channel
    if not is_admin_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {ADMIN_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    try:
        await interaction.guild.ban(user, reason=reason)
        add_ban(interaction.guild.id, user.id, interaction.user.id, reason)
        
        embed = discord.Embed(
            title=f"🚫 Ban: {user.name}",
            color=discord.Color.dark_red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="მიზეზი:", value=reason, inline=False)
        embed.set_footer(text=f"ban-ი: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ შეცდომა: {str(e)}", ephemeral=True)

@bot.tree.command(name="clear", description="წაშალე ჩატში ბოლო შეტყობინებები (მაქსიმუმ 300)")
@app_commands.describe(amount="რამდენი მესიჯი წაიშალოს? (1-300)")
async def clear(interaction: discord.Interaction, amount: int = 10):
    """Clear recent messages in the current channel"""
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    if amount < 1 or amount > 300:
        return await interaction.response.send_message(
            "❌ რაოდენობა უნდა იყოს 1-დან 300-მდე.",
            ephemeral=True
        )
    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ სერვერშია ხელმისაწვდომი.",
            ephemeral=True
        )

    await interaction.response.defer(ephemeral=True)
    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(
            f"✅ წაიშალა {len(deleted)} შეტყობინება(ა).",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"❌ წაშლა ვერ მოხერხდა: {str(e)}",
            ephemeral=True
        )

# Slash command group for reports
report_group = app_commands.Group(name="report", description="რეპორტი - მომხმარებელი ან საკითხი")

@report_group.command(name="user", description="მომხმარებელი რეპორტი")
@app_commands.describe(user="რომელი მომხმარებელი რეპორტი?", reason="რა მიზეზით?")
async def report_user(interaction: discord.Interaction, user: discord.Member, reason: str = "მიზეზი მითითებული არ არის"):
    """Report a user"""
    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ სერვერშია ხელმისაწვდომი.",
            ephemeral=True
        )

    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა.",
            ephemeral=True
        )

    add_report(interaction.guild.id, interaction.user.id, user.id, reason)
    
    embed = discord.Embed(
        title="📋 ახალი რეპორტი - მომხმარებელი",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="რეპორტირებული:", value=user.mention, inline=False)
    embed.add_field(name="რეპორტი მიერ:", value=interaction.user.mention, inline=False)
    embed.add_field(name="მიზეზი:", value=reason, inline=False)
    
    await interaction.response.send_message("✅ რეპორტი დაფიქსირდა!", ephemeral=True)
    
    # Send to admin channel
    admin_channel = None
    for channel in interaction.guild.text_channels:
        if channel.name == ADMIN_CHANNEL_NAME:
            admin_channel = channel
            break
    
    if admin_channel:
        await admin_channel.send(embed=embed)

@report_group.command(name="issue", description="საკითხი, ბაგი ან დახმარების მოთხოვნა")
@app_commands.describe(
    issue_type="რა ტიპის რეპორტი? (ბაგი/დახმარება/სხვა)",
    description="დეტალური აღწერა"
)
async def report_issue(interaction: discord.Interaction, issue_type: str, description: str):
    """Report a general issue, bug, or help request"""
    # Can be used from any channel
    add_general_report(interaction.guild.id, interaction.user.id, issue_type, description)
    
    embed = discord.Embed(
        title="📢 ახალი რეპორტი - საკითხი/ბაგი",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="რეპორტი მიერ:", value=interaction.user.mention, inline=False)
    embed.add_field(name="რეპორტის ტიპი:", value=issue_type, inline=False)
    embed.add_field(name="აღწერა:", value=description, inline=False)
    
    await interaction.response.send_message("✅ თქვენი რეპორტი გამოგზავნილია ადმინთან!", ephemeral=True)
    
    # Send to admin channel
    admin_channel = None
    for channel in interaction.guild.text_channels:
        if channel.name == ADMIN_CHANNEL_NAME:
            admin_channel = channel
            break
    
    if admin_channel:
        await admin_channel.send(embed=embed)

@bot.tree.command(name="ai_mode", description="AI რეჟიმის ჩართვა/გამორთვა ჩანელში")
@app_commands.describe(enabled="ჩართო (True) ან გამორთო (False)?")
async def ai_mode(interaction: discord.Interaction, enabled: bool = True):
    """Enable or disable AI in current channel"""
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    set_channel_ai_mode(interaction.channel.id, interaction.guild.id, enabled)
    
    status_text = "✅ ჩართული" if enabled else "❌ გამორთული"
    color = discord.Color.green() if enabled else discord.Color.red()
    
    embed = discord.Embed(
        title="🤖 AI რეჟიმი",
        description=f"ამ ჩანელში AI: {status_text}",
        color=color,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"ჩანელი: {interaction.channel.name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="set_llm", description="მომხმარებლის სასურველი AI მოდელის დაყენება")
@app_commands.describe(llm="აირჩიეთ AI მოდელი: gemini, claude")
@app_commands.choices(llm=[
    app_commands.Choice(name="Gemini 2.5 Flash", value="gemini"),
    app_commands.Choice(name="Claude 3.5 Sonnet", value="claude")
])
async def set_llm(interaction: discord.Interaction, llm: str):
    """Set user's preferred LLM"""
    # Only works in AI channel
    if not is_ai_chat_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {AI_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    # Validate LLM choice
    if llm not in ["gemini", "claude"]:
        return await interaction.response.send_message(
            "❌ არასწორი მოდელი. აირჩიეთ gemini ან claude.",
            ephemeral=True
        )
    
    # Check if API key is available
    if llm == "claude" and not CLAUDE_KEY:
        return await interaction.response.send_message(
            "❌ Claude API key არ არის დაყენებული.",
            ephemeral=True
        )
    elif llm == "gemini" and not GEMINI_KEY:
        return await interaction.response.send_message(
            "❌ Gemini API key არ არის დაყენებული.",
            ephemeral=True
        )
    
    set_user_llm_preference(interaction.user.id, llm)
    
    model_name = "Gemini 2.5 Flash" if llm == "gemini" else "Claude 3.5 Sonnet"
    embed = discord.Embed(
        title="🤖 AI მოდელი დაყენებულია",
        description=f"თქვენი სასურველი მოდელი: **{model_name}**",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"მომხმარებელი: {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stats", description="სერვერის მოდერირების სტატისტიკა")
async def stats(interaction: discord.Interaction):
    """Show moderation and AI statistics"""
    # Only works in admin channel
    if not is_admin_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {ADMIN_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    await interaction.response.defer(ephemeral=True)
    
    mod_stats = get_moderation_stats(interaction.guild.id)
    ai_stats = get_ai_stats(interaction.guild.id)
    
    embed = discord.Embed(
        title="📊 სერვერის სტატისტიკა",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.add_field(
        name="🛡️ მოდერირება",
        value=f"⚠️ გაფრთხოებული: {mod_stats['warns']}\n🔇 დამუტებული: {mod_stats['mutes']}\n🚫 დაბანული: {mod_stats['bans']}\n📋 რეპორტი: {mod_stats['reports']}",
        inline=False
    )
    
    embed.add_field(
        name="🤖 AI გამოყენება",
        value=f"💬 AI მესიჯი: {ai_stats['ai_messages']}\n🔋 Tokens გამოყენებული: {ai_stats['tokens_used']}",
        inline=False
    )
    
    embed.set_footer(text=f"სერვერი: {interaction.guild.name}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="warnlist", description="ყველა გაფრთხოებული მომხმარებელი")
async def warnlist(interaction: discord.Interaction):
    """Show all users with warnings"""
    # Only works in admin channel
    if not is_admin_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {ADMIN_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    await interaction.response.defer(ephemeral=True)
    
    warns = get_all_warnings(interaction.guild.id)
    
    if not warns:
        embed = discord.Embed(
            title="⚠️ გაფრთხოებული მომხმარებელი",
            description="გაფრთხოებული არავის არ აქვს!",
            color=discord.Color.green()
        )
        return await interaction.followup.send(embed=embed)
    
    embed = discord.Embed(
        title="⚠️ გაფრთხოებული მომხმარებელი",
        color=discord.Color.orange(),
        timestamp=datetime.now(timezone.utc)
    )
    
    for user_id, count in warns[:15]:  # Show top 15
        user = await bot.fetch_user(user_id)
        embed.add_field(
            name=f"{user.name}",
            value=f"🔔 {count} გაფრთხოება",
            inline=False
        )
    
    if len(warns) > 15:
        embed.add_field(
            name="...",
            value=f"+ კიდევ {len(warns) - 15} მომხმარებელი",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="mutelist", description="ყველა დამუტებული მომხმარებელი")
async def mutelist(interaction: discord.Interaction):
    """Show all muted users"""
    # Only works in admin channel
    if not is_admin_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {ADMIN_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    await interaction.response.defer(ephemeral=True)
    
    mutes = get_all_mutes(interaction.guild.id)
    
    if not mutes:
        embed = discord.Embed(
            title="🔇 დამუტებული მომხმარებელი",
            description="დამუტებული არავის არ აქვს!",
            color=discord.Color.green()
        )
        return await interaction.followup.send(embed=embed)
    
    embed = discord.Embed(
        title="🔇 დამუტებული მომხმარებელი",
        color=discord.Color.red(),
        timestamp=datetime.now(timezone.utc)
    )
    
    for user_id, reason, duration, timestamp in mutes[:10]:  # Show top 10
        user = await bot.fetch_user(user_id)
        embed.add_field(
            name=f"{user.name}",
            value=f"⏱️ {duration} წთ\n💬 {reason[:50]}...",
            inline=False
        )
    
    if len(mutes) > 10:
        embed.add_field(
            name="...",
            value=f"+ კიდევ {len(mutes) - 10} მომხმარებელი",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="banlist", description="ყველა დაბანული მომხმარებელი")
async def banlist(interaction: discord.Interaction):
    """Show all banned users"""
    # Only works in admin channel
    if not is_admin_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {ADMIN_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    await interaction.response.defer(ephemeral=True)
    
    bans = get_all_bans(interaction.guild.id)
    
    if not bans:
        embed = discord.Embed(
            title="🚫 დაბანული მომხმარებელი",
            description="დაბანული არავის არ აქვს!",
            color=discord.Color.green()
        )
        return await interaction.followup.send(embed=embed)
    
    embed = discord.Embed(
        title="🚫 დაბანული მომხმარებელი",
        color=discord.Color.dark_red(),
        timestamp=datetime.now(timezone.utc)
    )
    
    for user_id, reason, timestamp in bans[:10]:  # Show top 10
        user = await bot.fetch_user(user_id)
        embed.add_field(
            name=f"{user.name}",
            value=f"💬 {reason[:100]}...",
            inline=False
        )
    
    if len(bans) > 10:
        embed.add_field(
            name="...",
            value=f"+ კიდევ {len(bans) - 10} მომხმარებელი",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="slowmode", description="ჩანელში slowmode-ის დაყენება (წამებში)")
@app_commands.describe(seconds="წამების რაოდენობა (0-21600)")
async def slowmode(interaction: discord.Interaction, seconds: int = 0):
    """Set slowmode in the current channel"""
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    if seconds < 0 or seconds > 21600:
        return await interaction.response.send_message(
            "❌ წამები უნდა იყოს 0-21600 შორის.",
            ephemeral=True
        )
    
    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ტექსტურ ჩანელებშია ხელმისაწვდომი.",
            ephemeral=True
        )
    
    try:
        await interaction.channel.edit(slowmode_delay=seconds)
        embed = discord.Embed(
            title="⏱️ Slowmode",
            description=f"Slowmode დაყენებულია {seconds} წამზე.",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ შეცდომა: {str(e)}", ephemeral=True)

@bot.tree.command(name="lock", description="ჩანელის დაბლოკვა (მომხმარებლებს ვერ დაწერენ)")
async def lock(interaction: discord.Interaction):
    """Lock the current channel"""
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ტექსტურ ჩანელებშია ხელმისაწვდომი.",
            ephemeral=True
        )
    
    try:
        # Deny send_messages for @everyone
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
        embed = discord.Embed(
            title="🔒 ჩანელი დაბლოკილია",
            description="მომხმარებლებს ვერ დაწერენ ამ ჩანელში.",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ შეცდომა: {str(e)}", ephemeral=True)

@bot.tree.command(name="unlock", description="ჩანელის განბლოკვა")
async def unlock(interaction: discord.Interaction):
    """Unlock the current channel"""
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ტექსტურ ჩანელებშია ხელმისაწვდომი.",
            ephemeral=True
        )
    
    try:
        # Reset permissions for @everyone
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
        embed = discord.Embed(
            title="🔓 ჩანელი განბლოკილია",
            description="მომხმარებლებს შეუძლიათ დაწერონ ამ ჩანელში.",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ შეცდომა: {str(e)}", ephemeral=True)

@bot.tree.command(name="purge_user", description="კონკრეტული მომხმარებლის მესიჯების წაშლა (მაქსიმუმ 50)")
@app_commands.describe(user="რომელი მომხმარებლის მესიჯები წაიშალოს?", amount="რამდენი მესიჯი (1-50)")
async def purge_user(interaction: discord.Interaction, user: discord.Member, amount: int = 10):
    """Purge messages from a specific user"""
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    if amount < 1 or amount > 50:
        return await interaction.response.send_message(
            "❌ რაოდენობა უნდა იყოს 1-50 შორის.",
            ephemeral=True
        )
    
    if not interaction.channel or not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ტექსტურ ჩანელებშია ხელმისაწვდომი.",
            ephemeral=True
        )
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        def check(message):
            return message.author == user
        
        deleted = await interaction.channel.purge(limit=amount, check=check)
        await interaction.followup.send(
            f"✅ წაიშალა {len(deleted)} მესიჯი მომხმარებლისგან {user.mention}.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(
            f"❌ წაშლა ვერ მოხერხდა: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="checkuser", description="მომხმარებლის დეტალური შემოწმება")
@app_commands.describe(user="რომელი მომხმარებლის შემოწმება?")
async def checkuser(interaction: discord.Interaction, user: discord.Member):
    """Detailed user check"""
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    await interaction.response.defer(ephemeral=True)
    
    embed = discord.Embed(
        title=f"👤 {user.name}#{user.discriminator} - შემოწმება",
        color=user.color if user.color != discord.Color.default() else discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="ID:", value=user.id, inline=True)
    embed.add_field(name="შემოქმედი:", value=f"<t:{int(user.created_at.timestamp())}:F>", inline=True)
    embed.add_field(name="სერვერში შემოსვლა:", value=f"<t:{int(user.joined_at.timestamp())}:F>" if user.joined_at else "უცნობი", inline=True)
    
    roles = [role.mention for role in user.roles[1:]]  # Exclude @everyone
    embed.add_field(name=f"როლები ({len(roles)}):", value=" ".join(roles) if roles else "არა აქვს", inline=False)
    
    permissions = get_readable_permissions(user.guild_permissions)
    embed.add_field(name="უფლებები:", value=permissions[:500] + "..." if len(permissions) > 500 else permissions, inline=False)
    
    # Get user warnings
    warnings = get_user_warnings(interaction.guild.id, user.id)
    if warnings:
        warn_text = "\n".join([f"• {reason} ({timestamp})" for reason, timestamp in warnings[:5]])
        embed.add_field(name=f"გაფრთხოებები ({len(warnings)}):", value=warn_text, inline=False)
    
    # Get user mutes
    mutes = get_user_mutes(interaction.guild.id, user.id)
    if mutes:
        mute_text = "\n".join([f"• {duration} წთ - {reason}" for reason, duration, timestamp in mutes[:3]])
        embed.add_field(name=f"მუტები ({len(mutes)}):", value=mute_text, inline=False)
    
    embed.set_footer(text=f"შემოწმებული: {interaction.user.name}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="modlog", description="მოდერაციული ლოგების ნახვა მომხმარებლისთვის")
@app_commands.describe(user="რომელი მომხმარებლის ლოგები?")
async def modlog(interaction: discord.Interaction, user: discord.Member):
    """Show moderation logs for a user"""
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    await interaction.response.defer(ephemeral=True)
    
    embed = discord.Embed(
        title=f"📋 მოდერაციული ლოგები: {user.name}",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    # Warnings
    warnings = get_user_warnings(interaction.guild.id, user.id)
    if warnings:
        warn_text = "\n".join([f"⚠️ {reason} - {timestamp}" for reason, timestamp in warnings])
        embed.add_field(name="გაფრთხოებები:", value=warn_text, inline=False)
    
    # Mutes
    mutes = get_user_mutes(interaction.guild.id, user.id)
    if mutes:
        mute_text = "\n".join([f"🔇 {duration} წთ - {reason} - {timestamp}" for reason, duration, timestamp in mutes])
        embed.add_field(name="მუტები:", value=mute_text, inline=False)
    
    # Bans (if any)
    bans = get_all_bans(interaction.guild.id)
    user_bans = [ban for ban in bans if ban[0] == user.id]
    if user_bans:
        ban_text = "\n".join([f"🚫 {reason} - {timestamp}" for _, reason, timestamp in user_bans])
        embed.add_field(name="ბანები:", value=ban_text, inline=False)
    
    if not warnings and not mutes and not user_bans:
        embed.description = "ამ მომხმარებელს მოდერაციული ლოგები არ აქვს."
    
    embed.set_footer(text=f"მოთხოვნილი: {interaction.user.name}")
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="kick", description="მომხმარებელი სერვერიდან kick-ი")
@app_commands.describe(user="რომელი მომხმარებელი kick-ი?", reason="kick-ის მიზეზი")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = "მიზეზი მითითებული არ არის"):
    """Kick a user"""
    # Only works in admin channel
    if not is_admin_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {ADMIN_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    if user == interaction.user:
        return await interaction.response.send_message(
            "❌ თავს ვერ გააგდებ!",
            ephemeral=True
        )
    
    try:
        await interaction.guild.kick(user, reason=reason)
        
        embed = discord.Embed(
            title=f"👢 Kick: {user.name}",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="მიზეზი:", value=reason, inline=False)
        embed.set_footer(text=f"kick-ი: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ შეცდომა: {str(e)}", ephemeral=True)

@bot.tree.command(name="unban", description="მომხმარებელი unban-ი (გამოიყენეთ User ID)")
@app_commands.describe(user_id="მომხმარებლის ID რომელიც unban-ი?", reason="unban-ის მიზეზი")
async def unban(interaction: discord.Interaction, user_id: str, reason: str = "მიზეზი მითითებული არ არის"):
    """Unban a user by ID"""
    # Only works in admin channel
    if not is_admin_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {ADMIN_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user, reason=reason)
        
        embed = discord.Embed(
            title=f"✅ Unban: {user.name}",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="მიზეზი:", value=reason, inline=False)
        embed.set_footer(text=f"unban-ი: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ შეცდომა: {str(e)}", ephemeral=True)

@bot.tree.command(name="unmute", description="მომხმარებელი unmute-ი")
@app_commands.describe(user="რომელი მომხმარებელი unmute-ი?", reason="unmute-ის მიზეზი")
async def unmute(interaction: discord.Interaction, user: discord.Member, reason: str = "მიზეზი მითითებული არ არის"):
    """Unmute a user"""
    # Only works in admin channel
    if not is_admin_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {ADMIN_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    try:
        await user.timeout(None, reason=reason)
        
        embed = discord.Embed(
            title=f"🔊 Unmute: {user.name}",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="მიზეზი:", value=reason, inline=False)
        embed.set_footer(text=f"unmute-ი: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ შეცდომა: {str(e)}", ephemeral=True)

@bot.tree.command(name="userinfo", description="მომხმარებლის ინფორმაცია")
@app_commands.describe(user="რომელი მომხმარებლის ინფორმაცია?")
async def userinfo(interaction: discord.Interaction, user: discord.Member = None):
    """Show user information"""
    if user is None:
        user = interaction.user
    
    embed = discord.Embed(
        title=f"👤 {user.name}#{user.discriminator}",
        color=user.color if user.color != discord.Color.default() else discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="ID:", value=user.id, inline=True)
    embed.add_field(name="შემოქმედი:", value=f"<t:{int(user.created_at.timestamp())}:F>", inline=True)
    embed.add_field(name="სერვერში შემოსვლა:", value=f"<t:{int(user.joined_at.timestamp())}:F>" if user.joined_at else "უცნობი", inline=True)
    
    roles = [role.mention for role in user.roles[1:]]  # Exclude @everyone
    embed.add_field(name=f"როლები ({len(roles)}):", value=" ".join(roles) if roles else "არა აქვს", inline=False)
    
    permissions = get_readable_permissions(user.guild_permissions)
    embed.add_field(name="უფლებები:", value=permissions[:500] + "..." if len(permissions) > 500 else permissions, inline=False)
    
    embed.set_footer(text=f"მოთხოვნილი: {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="serverinfo", description="სერვერის ინფორმაცია")
async def serverinfo(interaction: discord.Interaction):
    """Show server information"""
    guild = interaction.guild
    
    embed = discord.Embed(
        title=f"🏠 {guild.name}",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="ID:", value=guild.id, inline=True)
    embed.add_field(name="შემოქმედი:", value=f"<t:{int(guild.created_at.timestamp())}:F>", inline=True)
    embed.add_field(name="წევრები:", value=guild.member_count, inline=True)
    embed.add_field(name="ჩანელები:", value=len(guild.channels), inline=True)
    embed.add_field(name="როლები:", value=len(guild.roles), inline=True)
    embed.add_field(name="ემოჯები:", value=len(guild.emojis), inline=True)
    
    embed.add_field(name="დონე:", value=f"Level {guild.premium_tier}" if guild.premium_tier > 0 else "არა აქვს", inline=True)
    embed.add_field(name="ბუსტი:", value=guild.premium_subscription_count or 0, inline=True)
    
    embed.set_footer(text=f"მოთხოვნილი: {interaction.user.name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="nickname", description="მომხმარებლის nickname-ის შეცვლა")
@app_commands.describe(user="რომელი მომხმარებლის nickname?", nickname="ახალი nickname (დატოვეთ ცარიელი წასაშლელად)")
async def nickname(interaction: discord.Interaction, user: discord.Member, nickname: str = None):
    """Change a user's nickname"""
    # Only works in admin channel
    if not is_admin_channel(interaction.channel):
        return await interaction.response.send_message(
            f"❌ ეს ბრძანება მუშაობს მხოლოდ {ADMIN_CHANNEL_NAME} ჩანელში!",
            ephemeral=True
        )
    
    if not is_admin(interaction.user):
        return await interaction.response.send_message(
            "❌ ეს ბრძანება მხოლოდ ადმინისტრატორებისთვისაა!",
            ephemeral=True
        )
    
    try:
        old_nick = user.nick
        await user.edit(nick=nickname)
        
        embed = discord.Embed(
            title=f"📝 Nickname შეცვლა: {user.name}",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="ძველი nickname:", value=old_nick or "არ ჰქონდა", inline=False)
        embed.add_field(name="ახალი nickname:", value=nickname or "წაიშალა", inline=False)
        embed.set_footer(text=f"შეცვალა: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ შეცდომა: {str(e)}", ephemeral=True)

@bot.event
async def on_member_remove(member):
    """Monitor and prevent mass kicks"""
    now = datetime.now()
    async for entry in member.guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
        if entry.target.id == member.id and (now - entry.created_at.replace(tzinfo=None)).total_seconds() < 10:
            if entry.user.id == OWNER_ID:
                return
            uid = entry.user.id
            data = mass_action_counter.get(uid, {"count": 0, "start_time": now})
            if (now - data["start_time"]).total_seconds() > 60:
                data = {"count": 1, "start_time": now}
            else:
                data["count"] += 1
            mass_action_counter[uid] = data
            if data["count"] >= MASS_ACTION_THRESHOLD:
                admin = member.guild.get_member(uid)
                if admin:
                    try:
                        await admin.edit(roles=[], reason="Anti-Nuke: Mass Kick Detection")
                        owner = await bot.fetch_user(OWNER_ID)
                        await owner.send(f"🚨 **SECURITY ALERT:** ადმინმა {admin.mention} დაიწყო წევრების მასიური გაგდება. მას ჩამოერთვა ყველა როლი!")
                        await send_log("🛑 ADMIN ACCESS REVOKED", admin, "მასიური გაგდება (Mass Kick Detection)", color=discord.Color.dark_red())
                    except:
                        pass

@bot.event
async def on_guild_channel_delete(channel):
    """Anti-raid: Monitor channel deletions"""
    now = datetime.now()
    entry = None
    if channel.guild.me.guild_permissions.view_audit_log:
        async for e in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
            entry = e
    if entry and entry.user.id != OWNER_ID:
        uid = entry.user.id
        user_data = deletion_counter.get(uid, {"count": 0, "last_time": now})
        if (now - user_data["last_time"]).total_seconds() < TIME_WINDOW:
            user_data["count"] += 1
        else:
            user_data["count"] = 1
        user_data["last_time"] = now
        deletion_counter[uid] = user_data
        if user_data["count"] >= RAID_THRESHOLD:
            member = channel.guild.get_member(uid)
            if member:
                try:
                    await member.edit(roles=[], reason="Anti-Raid: Excessive Deletion")
                    owner = await bot.fetch_user(OWNER_ID)
                    await owner.send(f"🚨 **RAID ALERT!** {member.name}-მა სცადა სერვერის დაშლა.")
                except:
                    pass
        extra = f"სახელი: **{channel.name}**\nტიპი: {channel.type}"
        await send_log("⚠️ ჩანელი წაიშალა", entry.user if entry else None, "სერვერის სტრუქტურის ცვლილება", color=discord.Color.orange(), extra_info=extra)

@bot.event
async def on_guild_role_delete(role):
    """Monitor role deletions"""
    entry = None
    if role.guild.me.guild_permissions.view_audit_log:
        async for e in role.guild.audit_logs(action=discord.AuditLogAction.role_delete, limit=1):
            entry = e
    perms_text = get_readable_permissions(role.permissions)
    extra = (
        f"როლის სახელი: **{role.name}**\n"
        f"ID: {role.id}\n\n"
        f"**ჩართული უფლებები:**\n{perms_text}"
    )
    await send_log("🚫 როლი წაიშალა", entry.user if entry else None, "მნიშვნელოვანი როლის წაშლა", color=discord.Color.red(), extra_info=extra)

@bot.event
async def on_guild_role_update(before, after):
    """Monitor role permission changes"""
    if before.permissions != after.permissions:
        entry = None
        if after.guild.me.guild_permissions.view_audit_log:
            async for e in after.guild.audit_logs(action=discord.AuditLogAction.role_update, limit=1):
                entry = e
        added = [p for p, v in after.permissions if v and not dict(before.permissions)[p]]
        removed = [p for p, v in before.permissions if v and not dict(after.permissions)[p]]
        changes = ""
        if added:
            changes += "**✅ დაემატა:**\n" + "\n".join([f"➕ {a.replace('_', ' ').title()}" for a in added])
        if removed:
            changes += "\n**❌ ჩამოერთვა:**\n" + "\n".join([f"➖ {r.replace('_', ' ').title()}" for r in removed])
        extra = f"⚖️ როლი: **{after.name}**\n\n{changes if changes else 'პარამეტრები შეიცვალა'}"
        await send_log("🔄 როლის უფლებები შეიცვალა", entry.user if entry else None, "უსაფრთხოების მონიტორინგი", color=discord.Color.blue(), extra_info=extra)

@bot.event
async def on_message_delete(message):
    """Log deleted messages"""
    if message.author.bot:
        return
    await send_log("🗑️ მესიჯი წაიშალა", message.author, f"ჩანელი: {message.channel.mention}", extra_info=f"ტექსტი: {message.content or 'ფაილი'}")

@bot.event
async def on_voice_state_update(member, before, after):
    """Log voice channel changes"""
    if before.channel != after.channel:
        if after.channel:
            await send_log("🔊 ვოისში შესვლა", member, f"შევიდა: **{after.channel.name}**", color=discord.Color.green())
        else:
            await send_log("🔇 ვოისიდან გასვლა", member, f"გავიდა: **{before.channel.name}**", color=discord.Color.light_grey())

@bot.event
async def on_member_join(member):
    """Auto-assign role on member join"""
    role = discord.utils.get(member.guild.roles, name=AUTO_ROLE_NAME)
    if role:
        await member.add_roles(role)

async def generate_ai_response(message, preferred_llm: str, history: list, georgian_mode: bool) -> tuple[str, str]:
    """Generate AI response based on preferred LLM"""
    curr_time = datetime.now().strftime("%H:%M")
    
    # Determine the prompt type and build final prompt
    if message.attachments and "ამომიწერე ტექსტი" in message.content.lower():
        # OCR Mode
        final_prompt = "ამოიკითხე ამ ფოტოდან ყველა ნაწერი და გადმომიწერე სუფთა ტექსტის სახით. სხვა არაფერი დაწერო, მხოლოდ ნაწერი."
        mode = "ocr"
    elif "http" in message.content.lower():
        # Link Summarizer Mode
        final_prompt = f"ამ ლინკიდან ამოიღე მთავარი ინფორმაცია და შემიჯამე 3-4 წინადადებაში: {message.content}"
        mode = "link"
    else:
        # Standard Chat Mode with conversation context
        custom_prompt = get_custom_prompt(message.guild.id if message.guild else 0, "default") if message.guild else None
        system_prompt = custom_prompt or SYSTEM_PROMPT
        user_content = message.content if message.content else 'აღწერე ეს ფოტო'
        final_prompt = f"{system_prompt}\nამჟამინდელი დრო: {curr_time}\n\nმომხმარებელი: {user_content}"
        final_prompt = optimize_prompt(final_prompt, history)
        mode = "chat"
    
    reply_text = ""
    api_used = preferred_llm
    
    try:
        if preferred_llm == "claude":
            if not CLAUDE_KEY:
                return "❌ Claude API key არ არის დაყენებული", "error"
            
            # Build messages for Claude
            messages = []
            if mode == "chat" and history:
                for role, msg in history:
                    claude_role = "user" if role == "user" else "assistant"
                    messages.append({"role": claude_role, "content": msg})
            
            # Add current message
            if message.attachments and any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                # For images, we'd need to handle differently, but for now fallback to Gemini
                return await generate_ai_response(message, "gemini", history, georgian_mode)
            
            messages.append({"role": "user", "content": final_prompt})
            
            # System prompt for Claude
            system = SYSTEM_PROMPT if mode == "chat" else None
            
            reply_text = await call_claude_api(messages, system)
            
        elif preferred_llm == "gemini":
            if not GEMINI_KEY:
                return "❌ Gemini API key არ არის დაყენებული", "error"
            
            parts = [{"text": final_prompt}]
            
            # Process image if attached
            if message.attachments:
                attachment = message.attachments[0]
                if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.webp']):
                    try:
                        if mode == "ocr":
                            # Standard OCR
                            img_data = requests.get(attachment.url).content
                            encoded_image = base64.b64encode(img_data).decode('utf-8')
                            parts.append({"inline_data": {"mime_type": attachment.content_type, "data": encoded_image}})
                        else:
                            # Enhanced image analysis
                            enhanced_analysis = await enhanced_image_analysis(attachment.url, GEMINI_KEY)
                            parts[0]["text"] = enhanced_analysis
                    except Exception as e:
                        pass
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
            res = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=15)
            data = res.json()
            
            if 'candidates' in data:
                reply_text = data['candidates'][0]['content']['parts'][0]['text']
            else:
                return "🛡️ სისტემა გადატვირთულია ან ლიმიტი ამოიწურა.", "error"
        
        else:
            return f"❌ უცნობი LLM: {preferred_llm}", "error"
        
        # Quality check
        if not is_quality_response(reply_text):
            reply_text = "ბოტი დროებით გადატვირთული ან არასამკუთო პასუხი გამოიღო. გთხოვთ კიდევ ცადეთ." if georgian_mode else "Bot response quality issue. Please try again."
        
        return reply_text, mode
        
    except asyncio.TimeoutError:
        return "⏱️ API მოთხოვნა ჩავიდა დროის გამო. გთხოვთ კიდევ ცადეთ.", "error"
    except Exception as e:
        return f"🛡️ კავშირის შეცდომა: {str(e)[:50]}", "error"

# ═══════════════════════════════════════════════════════════════════
# 💬 MESSAGE HANDLER (Unified - Guard Security + AI)
# ═══════════════════════════════════════════════════════════════════

@bot.event
async def on_message(message):
    """Main message handler for both guard and AI features"""
    # Ignore bot messages
    if message.author.bot:
        return

    # ────────────────────────────────────────────────────────────
    # 🛡️ GUARD SECURITY CHECKS (Only for non-admin users)
    # ────────────────────────────────────────────────────────────
    if not message.author.guild_permissions.administrator:
        author = message.author
        now = datetime.now(timezone.utc)

        # New user attachment/link check
        if author.joined_at:
            join_diff = (now - author.joined_at).total_seconds() / 60
            if join_diff < TRUST_TIME_MINUTES:
                if message.attachments or "http" in message.content.lower():
                    await message.delete()
                    return

        # Forbidden file extensions check
        if message.attachments:
            for attachment in message.attachments:
                if os.path.splitext(attachment.filename)[1].lower() in FORBIDDEN_EXTENSIONS:
                    await message.delete()
                    await handle_violation(author, "აკრძალული ფაილი", attachment.filename)
                    return

        # Scam pattern detection
        content = message.content.lower()
        for pattern in SCAM_PATTERNS:
            if re.search(pattern, content):
                await message.delete()
                await handle_violation(author, "Scam Detection", message.content, is_scam=True)
                return

        # Bad words check
        cursor.execute("SELECT word FROM bad_words")
        if any(word[0] in content for word in cursor.fetchall()):
            await message.delete()
            await handle_violation(author, "უხამსი სიტყვები", message.content)
            return

    # ────────────────────────────────────────────────────────────
    # 🤖 𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 AI FEATURES (Execute after command processing)
    # ────────────────────────────────────────────────────────────
    await bot.process_commands(message)

    # AI features only work in AI channel or enabled channels
    if not is_ai_chat_channel(message.channel) and not is_channel_ai_enabled(message.channel.id):
        return

    if message.content.startswith("/"):
        # Process slash commands
        await bot.process_commands(message)
        return

    if not message.content and not message.attachments:
        return

    user_id = message.author.id
    georgian_mode = get_georgian_mode(user_id)

    # --- 🎨 Image Generation (DALL-E via OpenAI) ---
    if message.content.lower().startswith("დამიგენერირე ფოტო"):
        prompt = message.content.replace("დამიგენერირე ფოტო", "").strip()
        if not prompt:
            error_msg = "🛡️ გთხოვთ, მიუთითოთ ფოტოს აღწერა." if georgian_mode else "Please specify image description"
            await message.reply(error_msg)
            return
        async with message.channel.typing():
            try:
                headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
                payload = {
                    "prompt": f"{prompt}, high quality, cinematic lighting, 4k",
                    "n": 1,
                    "size": "1024x1024"
                }
                res = requests.post("https://api.openai.com/v1/images/generations", json=payload, headers=headers, timeout=30)
                data = res.json()
                if 'data' in data:
                    img_url = data['data'][0]['url']
                    embed = discord.Embed(title="🎨 გენერირებული ფოტო", description=prompt, color=0x9b59b6)
                    embed.set_image(url=img_url)
                    embed.set_footer(text="𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 • Powered by DALL-E")
                    await message.reply(embed=embed)
                    track_token_usage(user_id, 50, "openai_images")
                else:
                    error_msg = "🛡️ ვერ მოხერხდა ფოტოს გენერირება. შეამოწმეთ OpenAI ბალანსი." if georgian_mode else "Image generation failed. Check OpenAI balance."
                    await message.reply(error_msg)
            except Exception as e:
                error_msg = f"🛡️ კავშირის შეცდომა OpenAI-სთან: {str(e)[:30]}" if georgian_mode else f"Connection error with OpenAI: {str(e)[:30]}"
                await message.reply(error_msg)
        return

    # --- 💬 AI Chat, OCR, and Link Summarization (with Conversation Memory) ---
    async with message.channel.typing():
        # Get user's preferred LLM
        preferred_llm = get_user_llm_preference(user_id)

        # Retrieve conversation history for context
        history = get_conversation_history(user_id, message.channel.id, limit=5)

        # Generate AI response
        reply_text, mode = await generate_ai_response(message, preferred_llm, history, georgian_mode)

        if mode == "error":
            await message.reply(reply_text)
            return

        # Save to conversation history
        save_conversation(user_id, message.channel.id, "user", message.content[:200] if message.content else "image")
        save_conversation(user_id, message.channel.id, "assistant", reply_text[:200])

        # Track token usage (estimate)
        estimated_tokens = len(reply_text) // 4
        track_token_usage(user_id, estimated_tokens, preferred_llm)

        # Apply Georgian formatting if enabled
        if georgian_mode:
            reply_text = georgian_format_response(reply_text, style='modern')

        # Visual formatting based on feature
        color = 0x3498db
        footer_text = f"🛡️ 𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 Pro • {preferred_llm.title()}"
        if mode == "ocr":
            color = 0xf1c40f
            footer_text = f"📝 OCR სისტემა • {preferred_llm.title()}"
        elif mode == "link":
            color = 0x1abc9c
            footer_text = f"🌐 ლინკის შეჯამება • {preferred_llm.title()}"

        embed = discord.Embed(description=reply_text[:2000], color=color, timestamp=datetime.now(timezone.utc))
        embed.set_author(name="𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖", icon_url=bot.user.avatar.url if bot.user.avatar else None)
        embed.set_footer(text=footer_text)
        await message.reply(embed=embed)

# ═══════════════════════════════════════════════════════════════════
# 🎯 READY EVENT (Unified)
# ═══════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    """Bot startup handler"""
    await bot.tree.sync()
    if not update_voice_stats.is_running():
        update_voice_stats.start()
    # Set activity for AI bot features
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening,
        name="შენს კითხვებს 🛡️"
    ))
    print(f'🚀 Guard Security & 𝔸𝕖𝕘𝕚𝕤ℂ𝕠𝕣𝕖 Pro მზად არის!')
    print(f'🛡️ Guard Active. Whitelist: {OWNER_ID}')

# ═══════════════════════════════════════════════════════════════════
# 🚀 BOT STARTUP
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    keep_alive()
    bot.tree.add_command(report_group)
    bot.run(GUARD_TOKEN)