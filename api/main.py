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
    city: str
    country: str
    theme: str = "feature_based"
    distance: int = 29000
    layers: List[str] = Field(default_factory=lambda: ["roads", "water", "parks"])
    paper_size: str = "3:4"

@app.get("/api/themes")
async def themes():
    return get_themes()

@app.get("/api/posters")
async def posters():
    return get_posters()

@app.post("/api/generate")
async def generate(request: GenerateRequest):
    try:
        result = run_script(
            city=request.city,
            country=request.country,
            theme=request.theme,
            distance=request.distance,
            layers=request.layers,
            paper_size=request.paper_size
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
