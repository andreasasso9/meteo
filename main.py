from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
import httpx

app = FastAPI()

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
            f"&daily=temperature_2m_max,temperature_2m_min&timezone=auto"
        )
        w_res = await client.get(weather_url)
        w_data = w_res.json()
        curr = w_data["current"]
        daily = w_data["daily"]
        condizione, icona = WMO_CODES.get(curr["weather_code"], ("Sconosciuto", "help-circle"))

        return {
            "citta": name,
            "regione": admin,
            "paese": country,
            "temp": round(curr["temperature_2m"]),
            "percepita": round(curr["apparent_temperature"]),
            "umidita": curr["relative_humidity_2m"],
            "vento": curr["wind_speed_10m"],
            "condizione": condizione,
            "icona": icona,
            "max": round(daily["temperature_2m_max"][0]),
            "min": round(daily["temperature_2m_min"][0]),
            "lat": lat, "lon": lon
        }

@app.get("/")
async def read_index():
    return FileResponse('index.html')