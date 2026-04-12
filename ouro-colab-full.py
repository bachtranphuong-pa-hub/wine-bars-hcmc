# OURO AREZ BOT - No quantization version (float16 only)
# Paste toàn bộ vào 1 cell, run

import subprocess, sys

print("Installing...")
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q",
    "transformers", "accelerate", "torch", "python-telegram-bot", "nest_asyncio"])
print("Done. Loading model (~5 min)...")

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_ID = "ByteDance/Ouro-2.6B-Thinking"
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    device_map="auto"
)
print("Model loaded OK")

SYSTEM_DEVIL = (
    "Ban la Arez - Devil's Advocate AI.\n"
    "Nhiem vu: Tim lo hong, dat cau hoi ve gia dinh, phan bien co ly, yeu cau bang chung.\n"
    "Ket thuc: Dieu kien de ket luan nay dung vung: [X]\n"
    "Ngon ngu: Tieng Viet."
)

SYSTEM_CHALLENGE = (
    "Specialist Devil's Advocate - linh vuc: {domain}\n"
    "Phan bien: dieu gi bo qua, benchmark sai, rui ro khong capture, ly do that bai?\n"
    "Ket thuc: De toi thay doi quan diem, toi can: [X]\n"
    "Ngon ngu: Tieng Viet."
)

def ouro_analyze(question, system_prompt=None, max_tokens=500):
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
        out = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.75,
            do_sample=True,
            repetition_penalty=1.1,
            pad_token_id=tokenizer.eos_token_id
        )
    return tokenizer.decode(
        out[0][len(inputs.input_ids[0]):], skip_special_tokens=True
    ).strip()

print("Test:")
print(ouro_analyze("ROI 15% resort 25M USD - rui ro?"))

from telegram.ext import Application, CommandHandler, MessageHandler, filters
import asyncio, nest_asyncio

BOT_TOKEN = "8747730907:AAFTAb7I6r7T36Da6bpX1eVT9mEfg-rOkrM"
BOT_USERNAME = "Arez_provocateur_bot"
AUTHORIZED_GROUPS = [-1003814611727]

async def start(update, ctx):
    await update.message.reply_text("Arez - Devil's Advocate. Tag toi de phan bien.")

async def handle_message(update, ctx):
    msg = update.message
    if not msg or not msg.text:
        return
    chat_id = msg.chat_id
    if msg.chat.type != "private" and chat_id not in AUTHORIZED_GROUPS:
        return
    text = msg.text.strip()
    mention = "@" + BOT_USERNAME
    if msg.chat.type != "private" and mention not in text:
        return
    query = text.replace(mention, "").strip()
    if not query:
        await msg.reply_text("Paste memo hoac cau hoi.")
        return
    await ctx.bot.send_chat_action(chat_id=chat_id, action="typing")
    if "/challenge" in query:
        prompt = "Output cua Zera - phan bien:\n\n" + query.replace("/challenge","").strip()
        system = SYSTEM_DEVIL
    elif "/specialize" in query:
        parts = query.replace("/specialize","").strip().split(None, 1)
        domain = parts[0] if parts else "general"
        system = SYSTEM_CHALLENGE.format(domain=domain)
        prompt = parts[1] if len(parts) > 1 else query
    else:
        system = SYSTEM_DEVIL
        prompt = query
    try:
        resp = ouro_analyze(prompt[:3000], system_prompt=system)
        reply = "Arez | Devil's Advocate\n\n" + resp
        await msg.reply_text(reply[:4000])
    except Exception as e:
        await msg.reply_text("Loi: " + str(e)[:100])

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Arez bot running - tag @Arez_provocateur_bot")
    await app.run_polling(drop_pending_updates=True)

nest_asyncio.apply()
asyncio.get_event_loop().run_until_complete(main())
