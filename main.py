import os
import asyncio
import csv
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters
from openai import OpenAI

TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPENAI_KEY = os.getenv("OPENAI_KEY", "").strip()
MI_ID = int(os.getenv("MI_ID", "0") or 0)
PORT = int(os.getenv("PORT", "10000"))

client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
ELECCION, DESCRIPCION = range(2)

SYSTEM_PROMPT = """
Eres Molave AI, asistente tecnico comercial de Molave Vision Soluciones en Palmira, Valle del Cauca, Colombia.
Servicios: redes empresariales, cableado estructurado, camaras de seguridad (Hikvision, Dahua), electricidad industrial y residencial, ciberseguridad y soporte tecnico.
Objetivo: convertir la consulta en una visita tecnica.
Tono: profesional, cercano, colombiano.
"""

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Molave AI V2 activo 24/7")
    def log_message(self, format, *args):
        return

def run_health_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    server.serve_forever()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [['⚡ Instalaciones'], ['🛠 Mantenimiento'], ['📹 Cámaras'], ['Otro']]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("¡Hola! Soy *Molave AI* 🤖\n¿Que servicio necesitas hoy?", reply_markup=markup, parse_mode="Markdown")
    return ELECCION

async def elegir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['servicio'] = update.message.text
    await update.message.reply_text(f"Anotado: {update.message.text}.\nDescribe el problema y donde es (barrio/empresa).")
    return DESCRIPCION

async def descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    servicio = context.user_data.get('servicio', 'No especificado')
    problema = update.message.text
    await update.message.reply_text("Analizando con IA... 🤖")
    if client:
        resp = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":f"Servicio: {servicio}\nProblema: {problema}"}])
        respuesta = resp.choices[0].message.content
    else:
        respuesta = f"Gracias por reportar '{problema}' en {servicio}. Un tecnico te contactara pronto."
    await update.message.reply_text(respuesta)
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado. Escribe /start")
    return ConversationHandler.END

def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = ApplicationBuilder().token(TOKEN).build()
    conv = ConversationHandler(entry_points=[CommandHandler("start", start)], states={ELECCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, elegir)], DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, descripcion)]}, fallbacks=[CommandHandler("cancelar", cancelar)], allow_reentry=True)
    app.add_handler(conv)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
