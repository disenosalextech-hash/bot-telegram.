from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
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
NUMERO_VALIDO = "957297177" # Número Yape/Plin
NOMBRE_VALIDO = "josset diaz"
MONTO_MINIMO = 2.0

USUARIOS_OK = set()      # Usuarios validados
ENTREGADOS = set()       # Usuarios que ya recibieron pronóstico actual
TOTAL_RECAUDADO = 0.0
PRONOSTICOS = {}         # Diccionario: id -> {'imagen': path, 'lista': [partidos], 'fecha': fecha}
PRONOSTICO_ID = 0
# ---------------------------------------

# ---------------- FUNCIONES OCR ----------------
def extraer_hora(texto):
    match = re.search(r'(\d{1,2}:\d{2})', texto)
    return match.group(1) if match else None

def extraer_monto(texto):
    match = re.search(r'(s\/\s*)?(\d+(\.\d{1,2})?)', texto)
    return float(match.group(2)) if match else None
# -----------------------------------------------

# --------------- ADMIN PANEL -------------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [
        [InlineKeyboardButton("📤 Subir pronóstico", callback_data="admin_subir")],
        [InlineKeyboardButton("🗑 Borrar pronósticos", callback_data="admin_borrar")],
        [InlineKeyboardButton("📋 Ver recaudación", callback_data="admin_recaudacion")],
        [InlineKeyboardButton("📆 Ver historial pronósticos", callback_data="admin_historial")],
        [InlineKeyboardButton("💰 Ver pagos recibidos", callback_data="admin_pagos")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👑 Panel de administración", reply_markup=reply_markup)

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if query.from_user.id != ADMIN_ID:
        return

    global PRONOSTICOS, PRONOSTICO_ID

    if data == "admin_subir":
        await query.message.reply_text("📤 Envía la imagen del pronóstico y la lista de partidos en el mensaje.")
        context.user_data["modo_subir"] = True

    elif data == "admin_borrar":
        PRONOSTICOS.clear()
        ENTREGADOS.clear()
        await query.message.reply_text("🗑 Todos los pronósticos han sido borrados.")

    elif data == "admin_recaudacion":
        await query.message.reply_text(f"💰 Total recaudado: S/ {TOTAL_RECAUDADO}\nUsuarios validados: {len(USUARIOS_OK)}")

    elif data == "admin_historial":
        if not PRONOSTICOS:
            await query.message.reply_text("❌ No hay pronósticos en el historial.")
        else:
            texto = "📆 Historial de pronósticos:\n"
            for pid, info in PRONOSTICOS.items():
                texto += f"{pid}. {', '.join(info['lista'])} ({info['fecha']})\n"
            await query.message.reply_text(texto)

    elif data == "admin_pagos":
        await query.message.reply_text(f"Usuarios validados: {len(USUARIOS_OK)}\nIDs: {', '.join(str(u) for u in USUARIOS_OK)}")

# --------------- USUARIO / MENU -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📋 Ver lista", callback_data="ver_lista")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Bienvenido al bot de pronósticos de Benson.\n"
        "Aquí puedes acceder a los pronósticos disponibles.",
        reply_markup=reply_markup
    )

async def usuario_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "ver_lista":
        if not PRONOSTICOS:
            await query.message.reply_text("❌ No se encontraron listas disponibles por el admin.")
        else:
            texto = "📋 Lista de pronósticos disponibles:\n"
            for pid, info in PRONOSTICOS.items():
                texto += f"{pid}. {', '.join(info['lista'])}\n"
            await query.message.reply_text(texto)

        # Después de mostrar lista, mostramos botón de ver pago
        keyboard = [[InlineKeyboardButton("💰 Ver pago", callback_data="ver_pago")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Si quieres recibir un pronóstico, revisa el pago:", reply_markup=reply_markup)

    elif data == "ver_pago":
        await query.message.reply_text(
            f"💰 Pago mínimo: S/ 2\n"
            f"📱 Yape/Plin: +51 957 297 177\n"
            f"👤 Nombre: Josset Diaz\n"
            f"📸 Envía tu comprobante"
        )

# ---------------- COMPROBANTE --------------------
async def leer_comprobante(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global TOTAL_RECAUDADO
    user = update.effective_user

    if not update.message.photo:
        await update.message.reply_text("❌ Por favor envía una imagen del comprobante.")
        return

    foto = update.message.photo[-1]
    path = f"comp_{user.id}.jpg"
    await foto.get_file().download_to_drive(path)
    texto = pytesseract.image_to_string(Image.open(path)).lower()

    # Validaciones
    if NOMBRE_VALIDO not in texto:
        await update.message.reply_text("❌ Nombre no válido.")
        os.remove(path)
        return
    if NUMERO_VALIDO not in texto.replace(" ", ""):
        await update.message.reply_text("❌ Número Yape/Plin no válido.")
        os.remove(path)
        return
    monto = extraer_monto(texto)
    if not monto or monto < MONTO_MINIMO:
        await update.message.reply_text(f"❌ Monto insuficiente (mín. S/ {MONTO_MINIMO}).")
        os.remove(path)
        return
    hora_str = extraer_hora(texto)
    if not hora_str:
        await update.message.reply_text("❌ No se detectó la hora.")
        os.remove(path)
        return
    ahora = datetime.datetime.now()
    hora_pago = datetime.datetime.strptime(hora_str, "%H:%M").replace(
        year=ahora.year, month=ahora.month, day=ahora.day
    )
    if abs((ahora - hora_pago).total_seconds())/60 > 15:
        await update.message.reply_text("❌ Pago fuera del tiempo (15 min).")
        os.remove(path)
        return

    # Pago validado
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

    # Enviar pronóstico activo
    if PRONOSTICOS:
        for pid, info in PRONOSTICOS.items():
            if user.id not in ENTREGADOS:
                await context.bot.send_photo(
                    chat_id=user.id,
                    photo=open(info['imagen'], "rb"),
                    caption="🔥 PRONÓSTICO OFICIAL 🔥"
                )
                ENTREGADOS.add(user.id)
                break
    os.remove(path)

# ----------------- SUBIR PRONOSTICO ----------------
async def subir_pronostico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    if update.message.photo and user_data.get("modo_subir"):
        global PRONOSTICO_ID
        PRONOSTICO_ID += 1
        photo = update.message.photo[-1]
        path = f"pron_{PRONOSTICO_ID}.jpg"
        await photo.get_file().download_to_drive(path)
        # Lista de partidos en caption
        lista = update.message.caption.split(",") if update.message.caption else ["Sin descripción"]
        PRONOSTICOS[PRONOSTICO_ID] = {
            "imagen": path,
            "lista": lista,
            "fecha": datetime.datetime.now().strftime("%d/%m/%Y")
        }
        ENTREGADOS.clear()
        await update.message.reply_text(f"✅ Pronóstico subido: {', '.join(lista)}")
        user_data["modo_subir"] = False

# ----------------- EJECUCIÓN -------------------
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    # Comandos
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))

    # Callbacks de botones
    app.add_handler(CallbackQueryHandler(usuario_callback, pattern="ver_.*"))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="admin_.*"))

    # Fotos
    app.add_handler(MessageHandler(filters.PHOTO, leer_comprobante))
    app.add_handler(MessageHandler(filters.PHOTO & filters.User(ADMIN_ID), subir_pronostico))

    print("🤖 Bot activo...")
    app.run_polling()

if __name__ == "__main__":
    main()
