# OURO AREZ BOT - Full Colab Script
# Usage: paste toàn bộ script này vào 1 cell duy nhất và run

# Step 1: Install
import subprocess
import sys

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", pkg])

print("Installing dependencies...")
install("transformers")
install("accelerate")
install("torch")
install("bitsandbytes>=0.46.1")
install("python-telegram-bot")
install("nest_asyncio")
print("Install done. Importing...")

# Step 2: Load model
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

try:
    from transformers import BitsAndBytesConfig
    import bitsandbytes
    USE_4BIT = True
    print("4-bit quantization available")
except Exception:
    USE_4BIT = False
    print("4-bit not available, using float16")

MODEL_ID = "ByteDance/Ouro-2.6B-Thinking"
print("Loading model (this takes 5-7 min)...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

if USE_4BIT:
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto"
    )
else:
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16,
        device_map="auto"
    )

print("Model loaded OK")

# Step 3: Prompts
SYSTEM_DEVIL = (
    "Ban la Arez - Devil's Advocate AI, doi trong phan tich voi Zera (AI Advisor RCC).\n"
    "Nhiem vu:\n"
    "1. Tim lo hong trong moi phan tich, de xuat, ket luan\n"
    "2. Dat cau hoi ve gia dinh - Du lieu nay lay tu dau?\n"
    "3. Phan bien co ly - dua ra rui ro thuc te\n"
    "4. Yeu cau bang chung - khong co data: noi thang day la gia dinh\n"
    "5. Kiem tra logic - circular reasoning, confirmation bias\n"
    "Phong cach: Truc tiep, ngan gon.\n"
    "Ket thuc: Dieu kien de ket luan nay dung vung: [X]\n"
    "Ngon ngu: Tieng Viet."
)

SYSTEM_CHALLENGE = (
    "Ban la Specialist Devil's Advocate trong linh vuc: {domain}\n"
    "Phan bien tu goc nhin chuyen gia {domain}:\n"
    "1. Dieu gi bi bo qua?\n"
    "2. Benchmark nao dung sai?\n"
    "3. Rui ro thuc te khong capture?\n"
    "4. Neu that bai - nguyen nhan so 1?\n"
    "Ket thuc: De toi thay doi quan diem, toi can thay: [X]\n"
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
    return tokenizer.decode(
        output[0][len(inputs.input_ids[0]):],
        skip_special_tokens=True
    ).strip()

# Quick test
print("Testing inference...")
print(ouro_analyze("ROI 15% resort 25M USD - rui ro chinh?"))

# Step 4: Telegram Bot
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
AUTHORIZED_GROUPS = [-1003814611727]
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
    bot_mention = "@" + BOT_USERNAME
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
    print("Arez bot running - tag @Arez_provocateur_bot in group")
    await app.run_polling(drop_pending_updates=True)


nest_asyncio.apply()
asyncio.get_event_loop().run_until_complete(main())
