import feedparser
import json
import os
import requests
from datetime import datetime

# Configuraciones y secretos (usaremos variables de entorno en la nube)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HISTORIAL_FILE = "historial.json"

# URLs de búsqueda (Noticias de España)
FEEDS = [
    # Búsqueda general en Google News para la zona y el tema
    "https://news.google.com/rss/search?q=%22cat%C3%A1logo+patrimonial%22+%22la+oliva%22+fuerteventura&hl=es&gl=ES&ceid=ES:es",
    # Búsqueda más amplia sobre bienes patrimoniales en el municipio
    "https://news.google.com/rss/search?q=%22bienes+patrimoniales%22+%22la+oliva%22&hl=es&gl=ES&ceid=ES:es"
]

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
            try:
                return set(json.load(f))
            except json.JSONDecodeError:
                return set()
    return set()

def guardar_historial(urls_conocidas):
    with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(urls_conocidas), f, indent=4)

def enviar_telegram(mensaje):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Aviso: Falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID. No se puede enviar el mensaje real a Telegram.")
        print("============ MENSAJE SIMULADO ============")
        print(mensaje)
        print("==========================================")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": mensaje,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("Mensaje de Telegram enviado con éxito.")
    except Exception as e:
        print(f"Error enviando mensaje de Telegram: {e}")

def buscar_noticias():
    historial = cargar_historial()
    nuevas_noticias = []
    
    for feed_url in FEEDS:
        print(f"Consultando feed: {feed_url}")
        feed = feedparser.parse(feed_url)
        
        for entrada in feed.entries:
            link = entrada.link
            titulo = entrada.title
            
            # Filtro básico: comprobar si ya lo hemos visto
            if link not in historial:
                nuevas_noticias.append({
                    "titulo": titulo,
                    "link": link,
                    "fecha": getattr(entrada, "published", "Fecha desconocida (reciente)")
                })
                historial.add(link)
    
    if nuevas_noticias:
        mensaje = "🏛️ <b>Nuevas actualizaciones: Catálogo Patrimonial de La Oliva</b>\n\n"
        for n in nuevas_noticias:
            mensaje += f"📰 <b>{n['titulo']}</b>\n📅 {n['fecha']}\n🔗 <a href='{n['link']}'>Leer noticia completa</a>\n\n"
        
        # Enviar alerta unificada a Telegram
        enviar_telegram(mensaje)
        # Guardar que ya hemos visto estas noticias para no repetir mañana
        guardar_historial(historial)
    else:
        print("No se han encontrado noticias nuevas.")

if __name__ == "__main__":
    print(f"Iniciando escáner a las {datetime.now().isoformat()}")
    buscar_noticias()
