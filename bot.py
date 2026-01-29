from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from PIL import Image
import pytesseract
import datetime
import re
import os

# ---------------- CONFIG ----------------
TOKEN = "8503129170:AAHC4HDiWC_YWEED6VwCfwV2fBUU9c50ul4"
ADMIN_ID = 5880343185
NUMERO_VALIDO = "957297177"  # Número Yape/Plin
NOMBRE_VALIDO = "josset diaz"
MONTO_MINIMO = 2.0
PRONOSTICO_IMG = "pronostico.jpg"

USUARIOS_OK = set()          # Usuarios validados
ENTREGADOS = set()           # Usuarios que ya recibieron pronóstico actual
TOTAL_RECAUDADO = 0.0
PRONOSTICO_ID = 1
# ---------------------------------------

# ---------------- FUNCIONES OCR ----------------
def extraer_hora(texto):
    match = re.search(r'(\d{1,2}:\d{2})', texto)
    return match.group(1) if match else None

def extraer_monto(texto):
    match = re.search(r'(s\/\s*)?(\d+(\.\d{1,2})?)', texto)
    return float(match.group(2)) if match else None
# -----------------------------------------------

# ---------------- COMANDOS ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 BOT DE PRONÓSTICOS\n\n"
        "Aquí solo se entregan los pronósticos disponibles.\n"
        "No se dan detalles ni explicaciones.\n\n"
        f"💰 Pago mínimo: S/ {MONTO_MINIMO}\n"
        f"📱 Yape/Plin: +51 957 297 177\n"
        f"👤 Nombre: Josset Diaz\n\n"
        "📸 Envía tu comprobante y espera confirmación."
    )

async def leer_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TOTAL_RECAUDADO

    user = update.effective_user
    foto = update.message.photo[-1]
    path = f"comp_{user.id}.jpg"
    await foto.get_file().download_to_drive(path)

    texto = pytesseract.image_to_string(Image.open(path)).lower()

    # 1) Nombre
    if NOMBRE_VALIDO not in texto:
        await update.message.reply_text("❌ Nombre no válido.")
        os.remove(path)
        return

    # 2) Número
    if NUMERO_VALIDO not in texto.replace(" ", ""):
        await update.message.reply_text("❌ Número Yape/Plin no válido.")
        os.remove(path)
        return

    # 3) Monto
    monto = extraer_monto(texto)
    if not monto or monto < MONTO_MINIMO:
        await update.message.reply_text(f"❌ Monto insuficiente (mín. S/ {MONTO_MINIMO}).")
        os.remove(path)
        return

    # 4) Hora
    hora_str = extraer_hora(texto)
    if not hora_str:
        await update.message.reply_text("❌ No se detectó la hora.")
        os.remove(path)
        return

    ahora = datetime.datetime.now()
    hora_pago = datetime.datetime.strptime(hora_str, "%H:%M").replace(
        year=ahora.year, month=ahora.month, day=ahora.day
    )
    if abs((ahora - hora_pago).total_seconds()) / 60 > 15:
        await update.message.reply_text("❌ Pago fuera del tiempo (15 min).")
        os.remove(path)
        return

    # ✅ Pago validado
    USUARIOS_OK.add(user.id)
    TOTAL_RECAUDADO += monto

    await update.message.reply_text(f"✅ Pago confirmado (S/ {monto})")

    # Notificar admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"💰 Nuevo pago validado\n"
             f"👤 Usuario: {user.full_name}\n"
             f"🆔 ID: {user.id}\n"
             f"💵 Monto: S/ {monto}\n"
             f"💰 Total recaudado: S/ {TOTAL_RECAUDADO}"
    )

    # Entregar pronóstico si existe y no lo recibió
    if os.path.exists(PRONOSTICO_IMG) and user.id not in ENTREGADOS:
        await context.bot.send_photo(
            chat_id=user.id,
            photo=open(PRONOSTICO_IMG, "rb"),
            caption="🔥 PRONÓSTICO OFICIAL 🔥"
        )
        ENTREGADOS.add(user.id)

    os.remove(path)

async def subir_pronostico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PRONOSTICO_ID, ENTREGADOS
    if update.effective_user.id != ADMIN_ID:
        return

    foto = update.message.photo[-1]
    await foto.get_file().download_to_drive(PRONOSTICO_IMG)
    PRONOSTICO_ID += 1
    ENTREGADOS.clear()

    await update.message.reply_text(
        "📌 Pronóstico cargado. Se entregará automáticamente a los usuarios que pagaron."
    )

async def estado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(
        f"💰 Total recaudado: S/ {TOTAL_RECAUDADO}\n"
        f"👤 Usuarios validados: {len(USUARIOS_OK)}"
    )

# ---------------- CHAT PRIVADO --------------------
async def hablar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    mensaje = update.message.text.replace("/hablar", "").strip()

    if not mensaje:
        await update.message.reply_text("✍️ Escribe tu mensaje así:\n/hablar Hola, tengo una duda")
        return

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📩 MENSAJE PRIVADO\n👤 Usuario: {user.full_name}\n🆔 ID: {user.id}\n💬 {mensaje}\nResponder con: /responder {user.id} MENSAJE"
    )
    await update.message.reply_text("✅ Mensaje enviado al administrador.")

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        respuesta = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=user_id, text=f"📩 Mensaje del admin:\n{respuesta}")
        await update.message.reply_text("✅ Respuesta enviada.")
    except:
        await update.message.reply_text("❌ Uso correcto: /responder ID mensaje")

# ------------------ EJECUCIÓN BOT -----------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subir", subir_pronostico))
    app.add_handler(CommandHandler("estado", estado))
    app.add_handler(CommandHandler("hablar", hablar))
    app.add_handler(CommandHandler("responder", responder))
    app.add_handler(MessageHandler(filters.PHOTO, leer_comprobante))

    print("🤖 Bot activo...")
    app.run_polling()

if __name__ == "__main__":
    main()
