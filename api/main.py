from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import List
import os
import sys

# Añadir el directorio raíz al path para que los imports funcionen si se ejecuta desde el root o desde api/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services.poster_service import get_themes, get_posters, run_script

app = FastAPI(title="Map Poster API")

# Enable CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class GenerateRequest(BaseModel):
    city: str = ""
    country: str = ""
    location: str = ""  # New unified location field
    theme: str = "feature_based"
    distance: int = 29000
    layers: List[str] = Field(default_factory=lambda: ["roads", "water", "parks"])
    paper_size: str = "3:4"
    lat: float = None
    lng: float = None
    grain: bool = False

class GeocodeRequest(BaseModel):
    city: str
    country: str

class LocationSearchRequest(BaseModel):
    query: str

@app.get("/api/themes")
async def themes():
    return get_themes()

@app.get("/api/posters")
async def posters():
    return get_posters()

@app.post("/api/geocode")
async def geocode(request: GeocodeRequest):
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="city_map_poster")
    location = geolocator.geocode(f"{request.city}, {request.country}")
    if location:
        return {
            "lat": location.latitude,
            "lng": location.longitude,
            "display_name": location.address
        }
    raise HTTPException(status_code=404, detail="Location not found")

@app.post("/api/location-search")
async def location_search(request: LocationSearchRequest):
    """Search for locations and return suggestions"""
    from geopy.geocoders import Nominatim
    geolocator = Nominatim(user_agent="city_map_poster")
    
    if len(request.query) < 2:
        return []
    
    try:
        # Search for multiple locations
        locations = geolocator.geocode(
            request.query,
            exactly_one=False,
            limit=5,
            addressdetails=True
        )
        
        if not locations:
            return []
        
        results = []
        for loc in locations:
            # Extract city and country from address details
            address = loc.raw.get('address', {})
            city = address.get('city') or address.get('town') or address.get('village') or address.get('municipality') or address.get('state') or ''
            country = address.get('country', '')
            
            # Create a clean display name
            display_name = loc.address
            # Simplify to "City, Country" format if possible
            if city and country:
                simple_name = f"{city}, {country}"
            else:
                # Use first two parts of address
                parts = display_name.split(', ')
                simple_name = ', '.join(parts[:2]) if len(parts) >= 2 else display_name
            
            results.append({
                "display_name": simple_name,
                "full_name": loc.address,
                "lat": loc.latitude,
                "lng": loc.longitude,
                "city": city,
                "country": country
            })
        
        return results
    except Exception as e:
        print(f"Location search error: {e}")
        return []

@app.post("/api/generate")
async def generate(request: GenerateRequest):
    try:
        # Use city if provided, otherwise extract from location
        city = request.city
        if not city and request.location:
            # Extract first part of location as city name
            city = request.location.split(',')[0].strip()
        
        country = request.country
        if not country and request.location and ',' in request.location:
            # Extract last part as country
            country = request.location.split(',')[-1].strip()
        
        result = run_script(
            city=city or "Map",
            country=country or "",
            theme=request.theme,
            distance=request.distance,
            layers=request.layers,
            paper_size=request.paper_size,
            lat=request.lat,
            lng=request.lng,
            grain=request.grain
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve the posters directory statically
if not os.path.exists("posters"):
    os.makedirs("posters")
app.mount("/api/posters/img", StaticFiles(directory="posters"), name="posters")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
