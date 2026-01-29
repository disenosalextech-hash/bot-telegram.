from telegram import Update # type: ignore
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters # type: ignore
from datetime import datetime
import json
import pytesseract # type: ignore
from PIL import Image # type: ignore
import io

# ---------------- CONFIG ----------------
TOKEN = '8503129170:AAHC4HDiWC_YWEED6VwCfwV2fBUU9c50ul4'
abonados_file = 'abonados.json'
bloque_file = 'bloque.json'
pago_minimo = 2
max_bloque = 500
mi_id = 5880343185

# ---------------- CARGAR DATOS ----------------
try:
    with open(abonados_file, 'r') as f:
        abonados = json.load(f)
except:
    abonados = {}

try:
    with open(bloque_file, 'r') as f:
        bloque = json.load(f)
except:
    bloque = {"contador": 0}

usuarios_activos = set(abonados.keys())
esperando_partido = set()  # Usuarios que deben enviar partido

# ---------------- COMANDOS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"¡Hola {update.message.from_user.first_name}! Soy tu bot de pronósticos ⚽\n"
        "Comandos disponibles:\n"
        "/pago - Enviar comprobante de pago\n"
        "/pronostico - Solicitar pronóstico"
    )

async def pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Envía tu comprobante de pago (foto o mensaje) a este chat.\n"
        "Yape/Plin: +51 957 297 177 a nombre de Josset Díaz\n"
        "Pago mínimo: 2 soles"
    )

# ---------------- VALIDACIÓN ----------------
def validar_texto(texto: str) -> bool:
    return "josset díaz" in texto.lower()

async def validar_foto(update: Update):
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        img = Image.open(io.BytesIO(photo_bytes))
        texto_extraido = pytesseract.image_to_string(img, lang='spa')  # type: ignore
        valido = "josset díaz" in texto_extraido.lower()
        return texto_extraido, valido
    except:
        return "", False

# ---------------- REGISTRAR PAGO ----------------
async def registrar_pago(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    # Procesar foto o texto
    valido = False
    texto_detectado = ""
    if update.message.photo:
        texto_detectado, valido = await validar_foto(update)
    else:
        texto_detectado = update.message.text
        valido = validar_texto(texto_detectado)

    if not valido:
        await update.message.reply_text(
            "❌ El comprobante no es válido. Debe estar dirigido a Josset Díaz.\n"
            "No se entregará pronóstico hasta que envíes un pago correcto."
        )
        return

    # Registrar pago
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    abonados[user_id] = {
        "nombre": update.message.from_user.full_name,
        "fecha_pago": fecha,
        "comprobante": texto_detectado
    }
    with open(abonados_file, 'w') as f:
        json.dump(abonados, f, indent=2)

    # Bloques de 500 pagos
    bloque["contador"] += 1
    if bloque["contador"] >= max_bloque:
        total_monto_bloque = bloque["contador"] * pago_minimo
        await context.bot.send_message(chat_id=mi_id,
            text=f"🎉 Se registraron {bloque['contador']} pagos.\n💰 Total recaudado: {total_monto_bloque} soles")
        bloque["contador"] = 0
    with open(bloque_file, 'w') as f:
        json.dump(bloque, f, indent=2)

    # Agregar usuario activo y esperando partido
    usuarios_activos.add(user_id)
    esperando_partido.add(user_id)

    # ✅ Mensaje amigable después del pago
    await update.message.reply_text(
        f"✅ Gracias {update.message.from_user.first_name}, tu pago ha sido registrado correctamente.\n"
        "Ahora puedes solicitar tu pronóstico enviando el partido (ej: Alianza Lima vs Universitario)."
    )

# ---------------- ENVIAR PRONÓSTICO ----------------
async def enviar_pronostico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in esperando_partido:
        return  # Ignorar mensajes fuera de flujo

    partido = update.message.text
    esperando_partido.remove(user_id)

    pronostico_texto = (
        f"🎯 Pronóstico para {partido} (Betsson):\n"
        "- Ganador probable: Equipo A 55%\n"
        "- Total de goles: 2-3\n"
        "- Corners: 9-12\n"
        "- Primer goleador: Jugador X\n"
        "- Tarjetas amarillas: 2-3\n"
        "- Tarjetas rojas: 0-1\n"
        "\n¡Buena suerte con tu apuesta!"
    )

    await update.message.reply_text(pronostico_texto)

# ---------------- COMANDO /PRONOSTICO ----------------
async def pronostico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in usuarios_activos:
        await update.message.reply_text("No estás registrado. Usa /pago para pagar primero.")
        return
    esperando_partido.add(user_id)
    await update.message.reply_text("Escribe el partido para el pronóstico (ej: Alianza Lima vs Universitario):")

# ---------------- INICIALIZAR BOT ----------------
app = ApplicationBuilder().token(TOKEN).build()

# Comandos
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('pago', pago))
app.add_handler(CommandHandler('pronostico', pronostico))

# Registrar pagos y partidos
app.add_handler(MessageHandler(filters.PHOTO | filters.TEXT, registrar_pago))
app.add_handler(MessageHandler(filters.TEXT & filters.USER, enviar_pronostico))

# Ejecutar bot
app.run_polling()
PS C:\Users\USER\OneDrive\Apps> & C:/Users/USER/OneDrive/Apps/.venv/Scripts/Activate.ps1                                      
(.venv) PS C:\Users\USER\OneDrive\Apps> & C:/Users/USER/OneDrive/Apps/.venv/Scripts/python.exe "c:/Users/USER/OneDrive/Apps/bot de telegram.py.py"


