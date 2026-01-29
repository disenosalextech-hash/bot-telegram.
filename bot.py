from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from datetime import datetime
import json
import os

# ---------------- CONFIG ----------------
TOKEN = os.getenv("8503129170:AAHC4HDiWC_YWEED6VwCfwV2fBUU9c50ul4")

abonados_file = "abonados.json"
bloque_file = "bloque.json"

pago_minimo = 2
max_bloque = 500

mi_id = 5880343185  # ID del dueño (Telegram)
dueno_numero = "+51 957 297 177"

jugada_actual = None
partido_actual = None

# ---------------- CARGAR DATOS ----------------
try:
    with open(abonados_file, "r") as f:
        abonados = json.load(f)
except:
    abonados = {}

try:
    with open(bloque_file, "r") as f:
        bloque = json.load(f)
except:
    bloque = {"contador": 0}

usuarios_activos = set(abonados.keys())

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if partido_actual:
        mensaje = (
            "👋 Bienvenido al bot de jugadas ⚽🔥\n\n"
            "📢 HAY JUGADA DISPONIBLE\n"
            f"⚽ Partido: {partido_actual}\n\n"
            "🔒 Las jugadas son solo para abonados.\n"
            f"👑 Dueño: {dueno_numero}\n\n"
            "Usa /pago para acceder."
        )
    else:
        mensaje = (
            "👋 Bienvenido al bot de jugadas ⚽🔥\n\n"
            "📢 Aún no hay jugadas disponibles.\n\n"
            f"👑 Dueño: {dueno_numero}\n"
            "Usa /pago para acceder cuando haya."
        )

    await update.message.reply_text(mensaje)

# ---------------- PAGO ----------------
async def pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💰 MÉTODO DE PAGO\n\n"
        f"Yape / Plin: {dueno_numero}\n"
        "Nombre: Josset Díaz\n"
        f"Pago mínimo: {pago_minimo} soles\n\n"
        "Luego de pagar, escribe /pronostico."
    )

# ---------------- REGISTRAR PAGO ----------------
async def registrar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    abonados[user_id] = {
        "nombre": update.message.from_user.full_name,
        "fecha_pago": fecha,
        "comprobante": update.message.text or "comprobante enviado"
    }

    with open(abonados_file, "w") as f:
        json.dump(abonados, f, indent=2)

    bloque["contador"] += 1
    if bloque["contador"] >= max_bloque:
        total = bloque["contador"] * pago_minimo
        await context.bot.send_message(
            chat_id=mi_id,
            text=f"🎉 {bloque['contador']} pagos registrados\n💰 Total: {total} soles"
        )
        bloque["contador"] = 0

    with open(bloque_file, "w") as f:
        json.dump(bloque, f, indent=2)

    usuarios_activos.add(user_id)

    await update.message.reply_text(
        "✅ Pago registrado correctamente.\n"
        "Ahora puedes usar /pronostico."
    )

# ---------------- JUGADA (SOLO DUEÑO) ----------------
async def jugada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global jugada_actual, partido_actual

    if update.message.from_user.id != mi_id:
        return

    texto = update.message.text.replace("/jugada", "").strip()

    if "|" not in texto:
        await update.message.reply_text(
            "⚠️ Usa el formato:\n"
            "/jugada Equipo A vs Equipo B | tu jugada"
        )
        return

    partido, jugada = texto.split("|", 1)
    partido_actual = partido.strip()
    jugada_actual = jugada.strip()

    await update.message.reply_text("✅ Jugada guardada.")

    for uid in usuarios_activos:
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=(
                    "📢 HAY UNA NUEVA JUGADA DISPONIBLE\n\n"
                    f"⚽ Partido: {partido_actual}\n"
                    "🔒 Usa /pronostico para verla."
                )
            )
        except:
            pass

# ---------------- PRONOSTICO ----------------
async def pronostico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if user_id not in usuarios_activos:
        await update.message.reply_text(
            "🔒 Las jugadas son solo para abonados.\n"
            "Usa /pago para pagar."
        )
        return

    if not jugada_actual:
        await update.message.reply_text("⚠️ Aún no hay jugadas disponibles.")
        return

    await update.message.reply_text(
        "🎯 JUGADA OFICIAL\n\n"
        f"⚽ Partido: {partido_actual}\n"
        f"📌 Jugada: {jugada_actual}\n\n"
        "🍀 ¡Buena suerte!"
    )

# ---------------- INICIAR BOT ----------------
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("pago", pago))
app.add_handler(CommandHandler("pronostico", pronostico))
app.add_handler(CommandHandler("jugada", jugada))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, registrar_pago))

app.run_polling()
