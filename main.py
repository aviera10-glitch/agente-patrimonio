import feedparser
import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.parse

# Configuraciones y secretos
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
HISTORIAL_FILE = "historial.json"

# --- CONFIGURACIÓN DE BÚSQUEDA ---
MUNICIPIO = "La Oliva"
PALABRAS_CLAVE = [
    "catálogo arquitectónico",
    "catalogo arquitectonico",
    "catálogo patrimonial",
    "catalogo patrimonial",
    "catálogo municipal",
    "catalogo municipal",
    "bienes patrimoniales",
    "patrimonio histórico",
    "patrimonio historico"
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
        print("Aviso: Falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID.")
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

def texto_relevante(texto):
    """Comprueba si el texto contiene el municipio Y alguna de las palabras clave"""
    if not texto:
        return False
    texto_lower = texto.lower()
    if MUNICIPIO.lower() not in texto_lower:
        return False
    for keyword in PALABRAS_CLAVE:
        if keyword in texto_lower:
            return True
    return False

def buscar_google_news():
    print("-> Buscando en Prensa (Google News) y Ministerio de Cultura (últimos 2 meses)...")
    nuevas = []
    
    # Búsqueda estricta que cubre prensa canaria y nacional, más el ministerio de cultura específicamente
    query = '("Catálogo Arquitectónico" OR "Catálogo Patrimonial" OR "Catálogo Municipal" OR "Bienes Patrimoniales" OR "Patrimonio Histórico") AND "La Oliva" when:2m'
    query_encoded = urllib.parse.quote(query)
    
    url = f"https://news.google.com/rss/search?q={query_encoded}&hl=es&gl=ES&ceid=ES:es"
    try:
        feed = feedparser.parse(url)
        for entrada in feed.entries:
            nuevas.append({
                "titulo": entrada.title,
                "link": entrada.link,
                "fecha": getattr(entrada, "published", "Fecha reciente"),
                "fuente": "Google News (Prensa / Ministerio)"
            })
    except Exception as e:
        print(f"Error leyendo Google News: {e}")
    return nuevas

def buscar_boletines():
    print("-> Buscando en Boletines Oficiales (BOE y BOC)...")
    nuevas = []
    
    # BOE RSS
    try:
        boe_feed = feedparser.parse("https://www.boe.es/rss/boe.php")
        for entry in boe_feed.entries:
            if texto_relevante(entry.title) or texto_relevante(getattr(entry, 'description', '')):
                nuevas.append({
                    "titulo": f"[BOE] {entry.title}",
                    "link": entry.link,
                    "fecha": "Hoy",
                    "fuente": "BOE"
                })
    except Exception as e:
        print(f"Error leyendo BOE: {e}")

    # BOC RSS
    try:
        boc_feed = feedparser.parse("http://www.gobiernodecanarias.org/boc/rss/index.html")
        for entry in boc_feed.entries:
            if texto_relevante(entry.title) or texto_relevante(getattr(entry, 'description', '')):
                nuevas.append({
                    "titulo": f"[BOC] {entry.title}",
                    "link": entry.link,
                    "fecha": "Hoy",
                    "fuente": "BOC"
                })
    except Exception as e:
        print(f"Error leyendo BOC: {e}")
        
    return nuevas

def scrap_html_links(url_base, url_noticias, fuente, requiere_filtro_estricto=True):
    nuevas = []
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url_noticias, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            enlaces = soup.find_all('a', href=True)
            for a in enlaces:
                titulo = a.get_text(strip=True)
                if len(titulo) < 15:
                    continue
                
                texto_lower = titulo.lower()
                es_relevante = False
                
                if requiere_filtro_estricto:
                    es_relevante = texto_relevante(titulo)
                else:
                    # Si ya estamos en la web de La Oliva, flexibilizamos la búsqueda
                    # asumiendo que todo es de La Oliva, solo buscamos las palabras clave
                    for keyword in PALABRAS_CLAVE:
                        if keyword in texto_lower:
                            es_relevante = True
                            break
                            
                if es_relevante:
                    link = a['href']
                    if not link.startswith('http'):
                        link = url_base + link if link.startswith('/') else f"{url_base}/{link}"
                    nuevas.append({
                        "titulo": f"[{fuente}] {titulo}",
                        "link": link,
                        "fecha": "Reciente",
                        "fuente": fuente
                    })
    except Exception as e:
        print(f"Error leyendo {fuente}: {e}")
    return nuevas

def buscar_ayuntamiento():
    print("-> Buscando en Ayuntamiento de La Oliva...")
    return scrap_html_links("https://laoliva.es", "https://laoliva.es/noticias", "Ayto. La Oliva", requiere_filtro_estricto=False)

def buscar_cabildo():
    print("-> Buscando en Cabildo de Fuerteventura...")
    # Buscamos en la pagina principal de noticias del cabildo, aquí sí aplicamos el filtro estricto (que mencione La Oliva)
    return scrap_html_links("https://www.cabildofuer.es", "https://www.cabildofuer.es/cabildo/noticias/", "Cabildo Fuerteventura", requiere_filtro_estricto=True)

def buscar_noticias():
    historial = cargar_historial()
    todas_las_noticias = []
    
    todas_las_noticias.extend(buscar_google_news())
    todas_las_noticias.extend(buscar_boletines())
    todas_las_noticias.extend(buscar_ayuntamiento())
    todas_las_noticias.extend(buscar_cabildo())
    
    noticias_filtradas = []
    
    for n in todas_las_noticias:
        if n['link'] not in historial:
            if not any(x['link'] == n['link'] for x in noticias_filtradas):
                noticias_filtradas.append(n)
            historial.add(n['link'])
    
    if noticias_filtradas:
        print(f"¡Se han encontrado {len(noticias_filtradas)} noticias nuevas!")
        mensaje = "🏛️ <b>Nuevas actualizaciones: Patrimonio de La Oliva</b>\n\n"
        for n in noticias_filtradas:
            mensaje += f"📰 <b>{n['titulo']}</b>\n📍 Fuente: {n['fuente']} | 📅 {n['fecha']}\n🔗 <a href='{n['link']}'>Leer noticia</a>\n\n"
        
        enviar_telegram(mensaje)
        guardar_historial(historial)
    else:
        print("No se han encontrado noticias nuevas.")

if __name__ == "__main__":
    print(f"Iniciando escáner integral a las {datetime.now().isoformat()}")
    buscar_noticias()
