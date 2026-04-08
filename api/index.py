from fastapi import FastAPI
from fastapi.responses import FileResponse
import httpx

from google import genai
import json

import os
from dotenv import load_dotenv


app = FastAPI()

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

WMO_CODES = {
    0: ("Soleggiato", "sun"), 1: ("Quasi Sereno", "cloud-sun"), 2: ("Parz. Nuvoloso", "cloud-sun"),
    3: ("Nuvoloso", "cloud"), 45: ("Nebbia", "cloud-fog"), 48: ("Nebbia brinata", "cloud-fog"),
    51: ("Pioggerellina", "cloud-drizzle"), 61: ("Pioggia debole", "cloud-rain"),
    63: ("Pioggia", "cloud-rain"), 65: ("Pioggia forte", "cloud-showers-heavy"),
    71: ("Neve", "snowflake"), 80: ("Rovesci", "cloud-lightning-rain"), 95: ("Temporale", "cloud-lightning"),
}

@app.get("/api/search/{query}")
async def search_cities(query: str):
    async with httpx.AsyncClient() as client:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={query}&count=5&language=it&format=json"
        res = await client.get(url)
        data = res.json()
        results = data.get("results", [])
        return [{
            "name": r["name"],
            "admin": r.get("admin1", ""),
            "country": r.get("country", ""),
            "lat": r["latitude"],
            "lon": r["longitude"]
        } for r in results]

@app.get("/api/weather")
async def get_weather(lat: float, lon: float, name: str, admin: str = "", country: str = ""):
    async with httpx.AsyncClient() as client:
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
            f"&hourly=temperature_2m,weather_code"
            f"&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
        )
        w_res = await client.get(weather_url)
        w_data = w_res.json()
        curr = w_data["current"]
        hourly = w_data["hourly"]
        daily = w_data["daily"]
        condizione, icona = WMO_CODES.get(curr["weather_code"], ("Sconosciuto", "help-circle"))
        temperatura = round(curr["temperature_2m"])

        ora_attuale_citta = curr["time"]
        ora_attuale_citta = ora_attuale_citta[:13] + ":00"

        try:
            # Cerchiamo la posizione esatta della stringa dell'ora attuale 
            # all'interno della lista dei tempi orari
            start_index = hourly["time"].index(ora_attuale_citta)
        except ValueError:
            # Se per qualche motivo non la trova, partiamo dall'indice 0 
            # (ma con timezone=auto nell'URL è quasi impossibile)
            start_index = 0

        forecast_orario = []

        for i in range(start_index, start_index + 8):
            if i < len(hourly["time"]):
                time_str = hourly["time"][i]
                # Estraiamo solo l'ora (es. "11:00") dalla stringa ISO
                ora = time_str.split("T")[1][:5]
                
                codice_wmo = hourly["weather_code"][i]
                cond, ico = WMO_CODES.get(codice_wmo, ("Sereno", "sun"))
                
                forecast_orario.append({
                    "ora": ora,
                    "temp": round(hourly["temperature_2m"][i]),
                    "icona": ico
                })

        consigli = await get_ai_tips(name, condizione, temperatura, forecast_orario)

        return {
            "citta": name,
            "regione": admin,
            "paese": country,
            "temp": temperatura,
            "percepita": round(curr["apparent_temperature"]),
            "umidita": curr["relative_humidity_2m"],
            "vento": curr["wind_speed_10m"],
            "condizione": condizione,
            "icona": icona,
            "max": round(daily["temperature_2m_max"][0]),
            "min": round(daily["temperature_2m_min"][0]),
            "lat": lat, "lon": lon,
            "tips": consigli,
            "hourly": forecast_orario
        }

@app.get("/")
async def read_index():
    return FileResponse('index.html')


def get_tips(condition, temp):
    # Logica per suggerimenti basati sul meteo
    if "Pioggia" in condition or "Temporale" in condition or "Pioggerellina" in condition:
        return [
            {"icon": "library", "text": "Visita un museo o una mostra d'arte locale."},
            {"icon": "coffee", "text": "Momento perfetto per un caffè o una cioccolata calda."},
            {"icon": "clapperboard", "text": "Che ne dici di un film al cinema?"}
        ]
    elif temp > 25:
        return [
            {"icon": "palmtree", "text": "Fa caldo! Cerca un parco ombroso o una piscina."},
            {"icon": "ice-cream", "text": "È l'ora di un gelato artigianale."},
            {"icon": "droplets", "text": "Ricordati di bere molta acqua!"}
        ]
    elif temp < 10:
        return [
            {"icon": "home", "text": "Fa freddo. Meglio attività indoor o shopping al chiuso."},
            {"icon": "utensils", "text": "Goditi un piatto caldo tipico della zona."},
            {"icon": "thermometer-sun", "text": "Copriti bene prima di uscire!"}
        ]
    else: # Tempo mite / Sereno
        return [
            {"icon": "map", "text": "Tempo perfetto per una passeggiata in centro."},
            {"icon": "camera", "text": "La luce è ottima per fare delle foto ai monumenti."},
            {"icon": "bike", "text": "Noleggia una bici e goditi il panorama."}
        ]


    

async def get_ai_tips(citta, condizione, temp, hourly):
    prompt = f"""
    Meteo a {citta}: {condizione}, {temp}°C, {hourly}.
    REGOLE:
    1. Suggerisci esattamente 3 attività diverse e reali da fare in questa città.
    2. Rispondi SOLO con un array JSON.
    3. Usa solo queste icone: camera, shopping-bag, coffee, museum, palmtree, utensils, bike, library.

    FORMATO RICHIESTO:
    [
      {{"icon": "icona1", "text": "consiglio 1"}},
      {{"icon": "icona2", "text": "consiglio 2"}},
      {{"icon": "icona3", "text": "consiglio 3"}}
    ]
    """

    try:
        # Usiamo il sistema di configurazione per forzare un ARRAY di 3 oggetti
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                # Specifichiamo che vogliamo una LISTA di oggetti
                'response_schema': {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "icon": {"type": "string"},
                            "text": {"type": "string"}
                        },
                        "required": ["icon", "text"]
                    },
                    "minItems": 3,
                    "maxItems": 3
                }
            }
        )
        
        tips = json.loads(response.text)
        
        # Se per qualche motivo ne arrivano meno, aggiungiamo un controllo
        return tips if isinstance(tips, list) else [tips]
    
    except Exception as e:
        print(f"Errore AI: {e}")
        return get_tips(condizione, temp)
