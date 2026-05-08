"""
Telegram-бот: Oura Ring + план марафона + Claude агент + Strava скрины
Установка: pip install python-telegram-bot anthropic requests
Запуск:    python oura_bot.py
"""

import base64
import io
import logging
import requests
import anthropic
from datetime import date, timedelta
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters,
)

# ──────────────────────────────────────────────
# НАСТРОЙКИ
# ──────────────────────────────────────────────
OURA_TOKEN    = "YOUR_OURA_TOKEN"
ANTHROPIC_KEY = "YOUR_ANTHROPIC_KEY"
TG_BOT_TOKEN  = "YOUR_TELEGRAM_BOT_TOKEN"

MARATHON_DATE = date(2026, 9, 27)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)

claude = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

# ──────────────────────────────────────────────
# ПЛАН ТРЕНИРОВОК (полный, из предыдущего файла)
# ──────────────────────────────────────────────
FIXED_DAYS = {
    "2026-05-08": ("Лёгкий бег",        5,  "Z2, пульс 130-140"),
    "2026-05-09": ("Страйды",           5,  "8×100м в конце лёгкого бега"),
    "2026-05-10": ("Отдых",             0,  ""),
    "2026-05-11": ("Лёгкий бег",        5,  "Z2, очень легко"),
    "2026-05-12": ("Страйды",           6,  "6×100м страйды"),
    "2026-05-13": ("Отдых",             0,  ""),
    "2026-05-14": ("Лёгкий бег",        5,  "Z2, 30 мин"),
    "2026-05-15": ("Отдых",             0,  ""),
    "2026-05-16": ("Лёгкий бег",        3,  "15 мин, встряхнуть ноги"),
    "2026-05-17": ("СТАРТ — 10 км",    10,  "⚡ Забег #1! Разминка 10 мин"),
    "2026-05-18": ("Отдых",             0,  ""),
    "2026-05-19": ("Лёгкий бег",        6,  "Z1-Z2, очень легко"),
    "2026-05-20": ("Отдых",             0,  ""),
    "2026-05-21": ("Z2",                7,  "Пульс строго 130-145"),
    "2026-05-22": ("Лёгкий бег",        5,  ""),
    "2026-05-23": ("Лёгкий бег",        6,  ""),
    "2026-05-24": ("Длинный бег",       8,  "Лёгкий темп"),
    "2026-05-25": ("Лёгкий бег",        6,  "Z2"),
    "2026-05-26": ("Страйды",           6,  "6×100м"),
    "2026-05-27": ("Отдых",             0,  ""),
    "2026-05-28": ("Лёгкий бег",        5,  "Z2, 30 мин"),
    "2026-05-29": ("Отдых",             0,  ""),
    "2026-05-30": ("Лёгкий бег",        3,  "15 мин"),
    "2026-05-31": ("СТАРТ — 10 км",    10,  "⚡ Забег #2!"),
}

WEEKLY_TEMPLATES = {
    4:  [("Отдых",0,""),("Лёгкий бег",7,"Z2"),("Z2",8,""),("Лёгкий бег",6,""),("Отдых",0,""),("Длинный бег",14,"Z2 80-90 мин"),("Лёгкий бег",6,"")],
    5:  [("Z2",8,""),("Отдых",0,""),("Z2",9,""),("Лёгкий бег",7,""),("Отдых",0,""),("Длинный бег",16,"Z2 95-100 мин"),("Лёгкий бег",7,"")],
    6:  [("Z2",8,""),("Темповый бег",10,"5 км МТ + разминка/заминка"),("Отдых",0,""),("Z2",9,""),("Лёгкий бег",6,""),("Длинный бег",18,"Z2 + 3 км быстрее"),("Лёгкий бег",7,"")],
    7:  [("Z2",7,"Разгрузка"),("Лёгкий бег",6,""),("Отдых",0,""),("Z2",7,""),("Отдых",0,""),("Длинный бег",14,"Z2"),("Лёгкий бег",5,"")],
    8:  [("Z2",9,""),("Темповый бег",10,"6 км МТ"),("Отдых",0,""),("Z2",10,""),("Лёгкий бег",7,""),("Длинный бег",20,"Z2 2ч"),("Лёгкий бег",7,"")],
    9:  [("Z2",10,""),("Интервалы",12,"6×800м отдых 90с"),("Лёгкий бег",7,""),("Темповый бег",10,"6 км МТ"),("Отдых",0,""),("Длинный бег",22,"Z2 + 5 км МТ"),("Лёгкий бег",8,"")],
    10: [("Z2",10,""),("Интервалы",12,"5×1000м отдых 2м"),("Лёгкий бег",8,""),("МТ-темп",11,"8 км МТ"),("Отдых",0,""),("Длинный бег",24,"последние 8 км МТ"),("Лёгкий бег",8,"")],
    11: [("Z2",8,"Разгрузка"),("Лёгкий бег",7,""),("Отдых",0,""),("Темповый бег",9,"5 км МТ"),("Отдых",0,""),("Длинный бег",16,"Z2"),("Лёгкий бег",6,"")],
    12: [("Z2",11,""),("Интервалы",13,"6×1000м отдых 90с"),("Лёгкий бег",8,""),("МТ-темп",12,"10 км МТ"),("Лёгкий бег",6,""),("Длинный бег",27,"Z2 + 10 км МТ"),("Лёгкий бег",8,"")],
    13: [("Z2",11,""),("Интервалы",14,"5×1200м отдых 2м"),("Лёгкий бег",9,""),("МТ-темп",13,"10 км МТ"),("Лёгкий бег",6,""),("Длинный бег",30,"Z2 + 12 км МТ"),("Лёгкий бег",8,"")],
    14: [("Z2",12,""),("Интервалы",14,"6×1200м"),("Лёгкий бег",9,""),("МТ-темп",14,"12 км МТ"),("Лёгкий бег",7,""),("Длинный бег",32,"Z2 + 15 км МТ"),("Лёгкий бег",8,"")],
    15: [("Z2",9,"Разгрузка"),("Темповый бег",10,"6 км МТ"),("Отдых",0,""),("Z2",9,""),("Отдых",0,""),("Длинный бег",19,"Z2"),("Лёгкий бег",7,"")],
    16: [("Z2",11,""),("Интервалы",13,"4×1600м отдых 2:30"),("Лёгкий бег",8,""),("МТ-темп",13,"10 км МТ"),("Лёгкий бег",7,""),("Длинный бег",35,"ФИНАЛЬНЫЙ ДЛИННЫЙ 35 км"),("Лёгкий бег",8,"")],
    17: [("Z2",10,"Тейпер -20%"),("Темповый бег",11,"8 км МТ"),("Лёгкий бег",7,""),("Z2",10,""),("Отдых",0,""),("Длинный бег",24,"Z2"),("Лёгкий бег",6,"")],
    18: [("Z2",8,"Тейпер -40%"),("Страйды",8,"8×100м"),("Лёгкий бег",5,""),("МТ отрезки",9,"3×3км МТ"),("Отдых",0,""),("Длинный бег",16,"Z2"),("Лёгкий бег",5,"")],
    19: [("Лёгкий бег",6,"Тейпер -60%"),("Страйды",6,"6×100м"),("Отдых",0,""),("Лёгкий бег",5,"30 мин"),("Отдых",0,""),("Лёгкий бег",10,"10 км лёгко"),("Отдых",0,"")],
    20: [("Лёгкий бег",5,"30 мин"),("Страйды",4,"4×100м"),("Отдых",0,""),("Лёгкий бег",4,"20 мин"),("Отдых",0,"Углеводная загрузка"),("Отдых",0,"Последние приготовления"),("МАРАФОН 42.2 км",42,"ДЕНЬ МАРАФОНА!")],
}

TEMPLATE_START = date(2026, 6, 1)


def get_workout(d: date) -> dict:
    key = d.strftime("%Y-%m-%d")
    if key in FIXED_DAYS:
        t, km, desc = FIXED_DAYS[key]
        return {"type": t, "km": km, "description": desc}
    if d >= TEMPLATE_START:
        delta = (d - TEMPLATE_START).days
        week_num = delta // 7 + 4
        dow = delta % 7
        if week_num in WEEKLY_TEMPLATES:
            t, km, desc = WEEKLY_TEMPLATES[week_num][dow]
            return {"type": t, "km": km, "description": desc}
    return {"type": "Не запланировано", "km": 0, "description": ""}


def get_oura(endpoint: str, d: date) -> dict:
    try:
        r = requests.get(
            f"https://api.ouraring.com/v2/usercollection/{endpoint}",
            headers={"Authorization": f"Bearer {OURA_TOKEN}"},
            params={"start_date": str(d), "end_date": str(d)},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
        return data[0] if data else {}
    except Exception:
        return {}


def build_context(d: date) -> str:
    """Собирает контекст из Oura + плана для передачи в Claude."""
    yesterday = d - timedelta(days=1)
    sleep  = get_oura("daily_sleep",     d)
    sleep_y= get_oura("daily_sleep",     yesterday)
    ready  = get_oura("daily_readiness", d)
    workout= get_workout(d)
    days_left = (MARATHON_DATE - d).days

    return (
        f"Дата: {d.strftime('%d.%m.%Y')}\n"
        f"Oura сегодня — Sleep: {sleep.get('score','?')}/100, "
        f"Readiness: {ready.get('score','?')}/100\n"
        f"Oura вчера — Sleep: {sleep_y.get('score','?')}/100\n"
        f"Тренировка по плану: {workout['type']}, {workout['km']} км. {workout['description']}\n"
        f"До марафона (27 сент 2026): {days_left} дней\n"
    )


# ──────────────────────────────────────────────
# ИСТОРИЯ ДИАЛОГА (в памяти, на сессию)
# ──────────────────────────────────────────────
# chat_id → список сообщений для Claude
conversation_history: dict[int, list] = {}

SYSTEM_PROMPT = """Ты — персональный коуч по бегу и восстановлению. 
У тебя есть данные Oura Ring пользователя и его план подготовки к марафону 27 сентября 2026.
Старты по пути: 10 км 17 мая и 10 км 31 мая 2026.

Отвечай прямо, как тренер — без воды, конкретно.
Язык: русский. Используй данные Oura для персональных рекомендаций.
Если пользователь спрашивает о тренировке — учитывай его Readiness score.
Если Readiness < 60 — рекомендуй снизить нагрузку или взять отдых."""


# ──────────────────────────────────────────────
# КОМАНДЫ БОТА
# ──────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Привет! Я твой коуч по марафонской подготовке.\n\n"
        "Команды:\n"
        "/briefing — утренняя сводка дня\n"
        "/workout — тренировка на сегодня\n"
        "/stats — показатели Oura\n"
        "/tomorrow — тренировка на завтра\n"
        "/reset — сбросить историю диалога\n\n"
        "📸 После пробежки — просто пришли скрин из Strava, разберу тренировку.\n\n"
        "Или просто напиши вопрос — отвечу с учётом твоих данных."
    )
    await update.message.reply_text(text)


async def cmd_briefing(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Собираю данные...")
    today = date.today()
    context = build_context(today)
    workout = get_workout(today)

    response = claude.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"{context}\n\n"
                "Составь утреннюю сводку:\n"
                "1. Статус восстановления (одна фраза)\n"
                "2. Рекомендация по тренировке (выполнять / скорректировать / заменить)\n"
                "3. Один совет на день"
            )
        }],
    )
    briefing = response.content[0].text
    days_left = (MARATHON_DATE - today).days
    race_emoji = "⚡" if "СТАРТ" in workout["type"] or "МАРАФОН" in workout["type"] else "🌅"

    msg = (
        f"{race_emoji} *{today.strftime('%d.%m.%Y')}*\n\n"
        f"💤 Sleep ?  |  ⚡ Ready ?\n"
        f"🏃 {workout['type']}"
        + (f" · {workout['km']} км" if workout["km"] > 0 else "")
        + f"\n📅 До марафона: {days_left} дн\n\n"
        + briefing
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_workout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    w = get_workout(today)
    days_left = (MARATHON_DATE - today).days

    if w["km"] == 0:
        text = f"🛌 Сегодня *{w['type']}*\n📅 До марафона: {days_left} дн"
    else:
        text = (
            f"🏃 *{w['type']}*\n"
            f"Дистанция: {w['km']} км\n"
            f"{w['description']}\n\n"
            f"📅 До марафона: {days_left} дн"
        )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_tomorrow(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tomorrow = date.today() + timedelta(days=1)
    w = get_workout(tomorrow)

    if w["km"] == 0:
        text = f"🛌 Завтра ({tomorrow.strftime('%d.%m')}): *{w['type']}*"
    else:
        text = (
            f"📋 Завтра *{tomorrow.strftime('%d.%m')}*\n"
            f"🏃 {w['type']} · {w['km']} км\n"
            f"{w['description']}"
        )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Загружаю Oura...")
    today = date.today()
    yesterday = today - timedelta(days=1)

    sleep  = get_oura("daily_sleep",     today)
    sleep_y= get_oura("daily_sleep",     yesterday)
    ready  = get_oura("daily_readiness", today)

    def score_emoji(s):
        if s == "?": return "❓"
        s = int(s)
        if s >= 85: return "🟢"
        if s >= 70: return "🟡"
        return "🔴"

    ss = sleep.get("score", "?")
    rs = ready.get("score", "?")
    sy = sleep_y.get("score", "?")

    text = (
        f"📊 *Oura — {today.strftime('%d.%m.%Y')}*\n\n"
        f"{score_emoji(ss)} Sleep score: *{ss}*/100\n"
        f"{score_emoji(rs)} Readiness:   *{rs}*/100\n"
        f"💤 Sleep вчера: {sy}/100"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    conversation_history[chat_id] = []
    await update.message.reply_text("🔄 История диалога сброшена.")


# ──────────────────────────────────────────────
# СВОБОДНЫЙ ДИАЛОГ — агент с памятью
# ──────────────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_text = update.message.text

    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    # Добавляем контекст Oura в первое сообщение сессии
    context_prefix = ""
    if not conversation_history[chat_id]:
        context_prefix = build_context(date.today()) + "\n\n"

    conversation_history[chat_id].append({
        "role": "user",
        "content": context_prefix + user_text,
    })

    # Ограничиваем историю последними 20 сообщениями
    history = conversation_history[chat_id][-20:]

    await update.message.reply_text("⏳...")

    response = claude.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=history,
    )
    reply = response.content[0].text

    conversation_history[chat_id].append({
        "role": "assistant",
        "content": reply,
    })

    await update.message.reply_text(reply)


# ──────────────────────────────────────────────
# АНАЛИЗ СКРИНА STRAVA
# ──────────────────────────────────────────────

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    caption = update.message.caption or ""

    await update.message.reply_text("📸 Анализирую пробежку...")

    # Скачиваем фото в максимальном качестве
    photo = update.message.photo[-1]
    tg_file = await ctx.bot.get_file(photo.file_id)

    img_bytes = io.BytesIO()
    await tg_file.download_to_memory(img_bytes)
    img_b64 = base64.b64encode(img_bytes.getvalue()).decode("utf-8")

    # Контекст: план + Oura
    today = date.today()
    oura_ctx = build_context(today)
    workout_plan = get_workout(today)

    # Промпт для анализа скрина
    analysis_prompt = (
        f"{oura_ctx}\n"
        f"Запланированная тренировка: {workout_plan['type']}, {workout_plan['km']} км. "
        f"{workout_plan['description']}\n\n"
        + (f"Комментарий пользователя: {caption}\n\n" if caption else "")
        + """Пользователь прислал скрин пробежки из Strava. Проанализируй:

1. Извлеки из скрина: дистанция, время, темп, средний пульс, набор высоты — что видно
2. Сравни с планом на сегодня — выполнено / перебор / недобор
3. Оцени качество тренировки по пульсовым зонам (если виден пульс)
4. Один конкретный вывод: что это значит для следующей тренировки

Если на скрине не Strava или данных не видно — скажи об этом прямо.
Тон: тренер, кратко, без воды. Язык: русский."""
    )

    response = claude.messages.create(
        model="claude-opus-4-5",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img_b64,
                    },
                },
                {"type": "text", "text": analysis_prompt},
            ],
        }],
    )

    analysis = response.content[0].text

    # Сохраняем в историю диалога как текст (изображения не хранятся)
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    conversation_history[chat_id].append({
        "role": "user",
        "content": f"[Прислал скрин Strava{': ' + caption if caption else ''}]",
    })
    conversation_history[chat_id].append({
        "role": "assistant",
        "content": analysis,
    })

    await update.message.reply_text(f"🏃 *Разбор пробежки*\n\n{analysis}", parse_mode="Markdown")


# ──────────────────────────────────────────────
# ЗАПУСК
# ──────────────────────────────────────────────

def main():
    app = Application.builder().token(TG_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",    cmd_start))
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(CommandHandler("workout",  cmd_workout))
    app.add_handler(CommandHandler("tomorrow", cmd_tomorrow))
    app.add_handler(CommandHandler("stats",    cmd_stats))
    app.add_handler(CommandHandler("reset",    cmd_reset))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
