import os
import json
import subprocess
from datetime import datetime

THEMES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "themes")
POSTERS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "posters")
PYTHON_BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "maptoposter", "bin", "python")
SCRIPT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "create_map_poster.py")

def get_themes():
    themes = []
    if not os.path.exists(THEMES_DIR):
        return themes
    
    for file in sorted(os.listdir(THEMES_DIR)):
        if file.endswith('.json'):
            theme_id = file[:-5]
            theme_path = os.path.join(THEMES_DIR, file)
            try:
                with open(theme_path, 'r') as f:
                    data = json.load(f)
                    themes.append({
                        "id": theme_id,
                        "name": data.get("name", theme_id),
                        "description": data.get("description", "")
                    })
            except Exception:
                continue
    return themes

def get_posters():
    posters = []
    if not os.path.exists(POSTERS_DIR):
        return posters
    
    files = [f for f in os.listdir(POSTERS_DIR) if f.endswith('.png')]
    # Sort by creation time (newest first)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(POSTERS_DIR, x)), reverse=True)
    
    for file in files:
        posters.append({
            "filename": file,
            "url": f"/api/posters/img/{file}",
            "created_at": datetime.fromtimestamp(os.path.getmtime(os.path.join(POSTERS_DIR, file))).isoformat()
        })
    return posters

def run_script(city: str, country: str, theme: str, distance: int, layers, paper_size: str = "3:4"):
    cmd = [
        PYTHON_BIN,
        SCRIPT_PATH,
        "--city", city,
        "--country", country,
        "--theme", theme,
        "--distance", str(distance),
        "--paper-size", paper_size
    ]
    
    if layers:
        cmd.extend(["--layers", ",".join(layers)])
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Get current posters to find the new one
    old_posters = set(os.listdir(POSTERS_DIR)) if os.path.exists(POSTERS_DIR) else set()
    
    process = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
    
    if process.returncode != 0:
        raise Exception(f"Script error: {process.stderr}")
    
    # Find the newly created file
    new_posters = set(os.listdir(POSTERS_DIR))
    diff = new_posters - old_posters
    
    if not diff:
        # If no new file, find the most recently modified one matching city/theme
        files = [f for f in os.listdir(POSTERS_DIR) if f.endswith('.png') and city.lower().replace(' ', '_') in f.lower()]
        if not files:
            raise Exception("No poster was generated")
        files.sort(key=lambda x: os.path.getmtime(os.path.join(POSTERS_DIR, x)), reverse=True)
        filename = files[0]
    else:
        # Prefer the truly new file
        filename = list(diff)[0]
        
    return {
        "filename": filename,
        "url": f"/api/posters/img/{filename}",
        "output": process.stdout
    }
