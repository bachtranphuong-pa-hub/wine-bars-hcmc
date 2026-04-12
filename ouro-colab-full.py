# ============================================================
# OURO AREZ BOT - Full Colab Script
# Run: !wget -q https://raw.githubusercontent.com/bachtranphuong-pa-hub/wine-bars-hcmc/main/ouro-colab-full.py
# Then run each cell in order
# ============================================================

# ============================================================
# CELL 1 - Install (run once, then restart runtime)
# ============================================================
# Uncomment and run:
# !pip install -U transformers accelerate torch bitsandbytes>=0.46.1 python-telegram-bot nest_asyncio -q

# ============================================================
# CELL 2 - Load model (~5 min)
# ============================================================
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

MODEL_ID = "ByteDance/Ouro-2.6B-Thinking"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto"
)
print("Model loaded OK")

# ============================================================
# CELL 3 - Prompts + Inference
# ============================================================
SYSTEM_DEVIL = (
    "Ban la Arez - Devil's Advocate AI, doi trong phan tich voi Zera (AI Advisor RCC).\n"
    "Nhiem vu:\n"
    "1. Tim lo hong trong moi phan tich, de xuat, ket luan\n"
    "2. Dat cau hoi ve gia dinh - Du lieu nay lay tu dau? Tai sao tin con so nay?\n"
    "3. Phan bien co ly, khong pha hoai - dua ra rui ro thuc te\n"
    "4. Yeu cau bang chung - khong co data thi noi thang: day la gia dinh\n"
    "5. Kiem tra logic - phat hien circular reasoning, confirmation bias, sunk cost\n"
    "Phong cach: Truc tiep, ngan gon, fair.\n"
    "Ket thuc bang: Dieu kien de ket luan nay dung vung: [X]\n"
    "Ngon ngu: Tieng Viet. English terms khi can."
)

SYSTEM_CHALLENGE = (
    "Ban la Specialist Devil's Advocate trong linh vuc: {domain}\n"
    "Phan bien phan tich sau tu goc nhin chuyen gia {domain}:\n"
    "1. Dieu gi bi bo qua hoac underestimated?\n"
    "2. Benchmark nao dang dung sai?\n"
    "3. Rui ro thuc te trong nganh ma phan tich khong capture?\n"
    "4. Neu that bai - nguyen nhan so 1 la gi?\n"
    "Ket thuc: De toi thay doi quan diem, toi can thay: [X, Y, Z]\n"
    "Ngon ngu: Tieng Viet."
)

def ouro_analyze(question, system_prompt=None, max_tokens=600):
    if system_prompt is None:
        system_prompt = SYSTEM_DEVIL
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]
    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.75,
            do_sample=True,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id
        )
    response = tokenizer.decode(
        output[0][len(inputs.input_ids[0]):],
        skip_special_tokens=True
    )
    return response.strip()

print("Inference ready")
print(ouro_analyze("ROI 15%/nam tu resort 25M USD - rui ro?"))

# ============================================================
# CELL 4 - Telegram Bot
# ============================================================
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import asyncio
import nest_asyncio

BOT_TOKEN = "8747730907:AAFTAb7I6r7T36Da6bpX1eVT9mEfg-rOkrM"
BOT_USERNAME = "Arez_provocateur_bot"
AUTHORIZED_GROUPS = [-1003814611727]  # replace with real group ID
MAX_INPUT_CHARS = 3000


async def start(update, ctx):
    await update.message.reply_text("Arez Devil's Advocate - san sang phan bien.")


async def handle_message(update, ctx):
    msg = update.message
    if not msg or not msg.text:
        return
    chat_id = msg.chat_id
    if msg.chat.type != "private" and chat_id not in AUTHORIZED_GROUPS:
        return
    text = msg.text.strip()
    bot_mention = f"@{BOT_USERNAME}"
    if msg.chat.type != "private" and bot_mention not in text:
        return
    query = text.replace(bot_mention, "").strip()
    if not query:
        await msg.reply_text("Paste memo hoac dat cau hoi.")
        return
    if len(query) > MAX_INPUT_CHARS:
        query = query[:MAX_INPUT_CHARS]
    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")
    if "/challenge" in query:
        content = query.replace("/challenge", "").strip()
        prompt = "Day la output cua Zera. Phan bien:\n\n" + content
        system = SYSTEM_DEVIL
    elif "/specialize" in query:
        parts = query.replace("/specialize", "").strip().split(None, 1)
        domain = parts[0] if parts else "general"
        content = parts[1] if len(parts) > 1 else query
        system = SYSTEM_CHALLENGE.format(domain=domain)
        prompt = content
    else:
        system = SYSTEM_DEVIL
        prompt = query
    try:
        response = ouro_analyze(prompt, system_prompt=system)
        full = "Arez | Devil's Advocate\n\n" + response
        if len(full) > 4000:
            full = full[:4000] + "\n\n[truncated]"
        await msg.reply_text(full)
    except Exception as e:
        await msg.reply_text("Loi: " + str(e)[:100])


async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    print("Arez bot running...")
    await app.run_polling(drop_pending_updates=True)


nest_asyncio.apply()
asyncio.get_event_loop().run_until_complete(main())
