import osmnx as ox
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import matplotlib.colors as mcolors
import numpy as np
from geopy.geocoders import Nominatim
from tqdm import tqdm
import time
import json
import os
from datetime import datetime
import argparse
from PIL import Image, ImageFilter
from io import BytesIO

THEMES_DIR = "themes"
FONTS_DIR = "fonts"
POSTERS_DIR = "posters"

def load_fonts():
    """
    Load Roboto fonts from the fonts directory.
    Returns dict with font paths for different weights.
    """
    fonts = {
        'bold': os.path.join(FONTS_DIR, 'Roboto-Bold.ttf'),
        'regular': os.path.join(FONTS_DIR, 'Roboto-Regular.ttf'),
        'light': os.path.join(FONTS_DIR, 'Roboto-Light.ttf')
    }
    
    # Verify fonts exist
    for weight, path in fonts.items():
        if not os.path.exists(path):
            print(f"⚠ Font not found: {path}")
            return None
    
    return fonts

FONTS = load_fonts()

def add_grain_effect(image, intensity=0.08):
    """
    Add film grain/noise effect to an image.
    
    Args:
        image: PIL Image object
        intensity: Grain intensity (0.0 to 1.0, default 0.08 for subtle effect)
    
    Returns:
        PIL Image with grain applied
    """
    img_array = np.array(image).astype(np.float32)
    
    # Generate noise
    noise = np.random.normal(0, intensity * 255, img_array.shape)
    
    # Add noise to image
    noisy = img_array + noise
    noisy = np.clip(noisy, 0, 255).astype(np.uint8)
    
    return Image.fromarray(noisy)

def add_blur_fade_top(image, fade_height_ratio=0.35, max_blur=8):
    """
    Add a graduated blur effect at the top of the image that fades to sharp.
    Perfect for iPhone lock screen to blend with widgets.
    
    Args:
        image: PIL Image object
        fade_height_ratio: How much of the image height to apply the effect (0.0 to 1.0)
        max_blur: Maximum blur radius at the very top
    
    Returns:
        PIL Image with blur fade applied
    """
    width, height = image.size
    fade_height = int(height * fade_height_ratio)
    
    # Create a fully blurred version
    blurred = image.filter(ImageFilter.GaussianBlur(radius=max_blur))
    
    # Create the output image starting with the original
    result = image.copy()
    
    # Blend gradually from blurred (top) to sharp (bottom of fade zone)
    # We'll do this in horizontal strips for a smooth transition
    num_steps = min(fade_height, 50)  # Limit steps for performance
    step_height = fade_height // num_steps
    
    for i in range(num_steps):
        y_start = i * step_height
        y_end = (i + 1) * step_height if i < num_steps - 1 else fade_height
        
        # Calculate blend factor (1.0 at top = full blur, 0.0 at bottom = no blur)
        blend = 1.0 - (i / num_steps)
        
        # Get strips from both images
        original_strip = image.crop((0, y_start, width, y_end))
        blurred_strip = blurred.crop((0, y_start, width, y_end))
        
        # Blend the strips
        blended_strip = Image.blend(original_strip, blurred_strip, blend)
        
        # Paste into result
        result.paste(blended_strip, (0, y_start))
    
    return result

def apply_post_processing(fig, output_file, paper_size='3:4', grain=False, bg_color='#FFFFFF', dpi=300):
    """
    Apply post-processing effects and save the final image.
    
    Args:
        fig: matplotlib figure
        output_file: output file path
        paper_size: paper size for determining effects
        grain: whether to add grain effect
        bg_color: background color for the image
        dpi: dots per inch for the output image (default: 300)
    """
    # Save figure to buffer first
    buf = BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, facecolor=bg_color)
    buf.seek(0)
    
    # Load with PIL
    image = Image.open(buf)
    image = image.convert('RGB')
    
    # Apply blur fade for iPhone wallpaper
    if paper_size == '9:19.5':
        print("Applying blur fade effect for iPhone wallpaper...")
        image = add_blur_fade_top(image, fade_height_ratio=0.35, max_blur=12)
    
    # Apply grain if enabled
    if grain:
        print("Adding grain effect...")
        image = add_grain_effect(image, intensity=0.12)
    
    # Save final image
    image.save(output_file, 'PNG', quality=95)
    buf.close()

def generate_output_filename(city, theme_name):
    """
    Generate unique output filename with city, theme, and datetime.
    """
    if not os.path.exists(POSTERS_DIR):
        os.makedirs(POSTERS_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city.lower().replace(' ', '_')
    filename = f"{city_slug}_{theme_name}_{timestamp}.png"
    return os.path.join(POSTERS_DIR, filename)

def get_available_themes():
    """
    Scans the themes directory and returns a list of available theme names.
    """
    if not os.path.exists(THEMES_DIR):
        os.makedirs(THEMES_DIR)
        return []
    
    themes = []
    for file in sorted(os.listdir(THEMES_DIR)):
        if file.endswith('.json'):
            theme_name = file[:-5]  # Remove .json extension
            themes.append(theme_name)
    return themes

def load_theme(theme_name="feature_based"):
    """
    Load theme from JSON file in themes directory.
    """
    theme_file = os.path.join(THEMES_DIR, f"{theme_name}.json")
    
    if not os.path.exists(theme_file):
        print(f"⚠ Theme file '{theme_file}' not found. Using default feature_based theme.")
        # Fallback to embedded default theme
        return {
            "name": "Feature-Based Shading",
            "bg": "#FFFFFF",
            "text": "#000000",
            "gradient_color": "#FFFFFF",
            "water": "#C0C0C0",
            "parks": "#F0F0F0",
            "road_motorway": "#0A0A0A",
            "road_primary": "#1A1A1A",
            "road_secondary": "#2A2A2A",
            "road_tertiary": "#3A3A3A",
            "road_residential": "#4A4A4A",
            "road_default": "#3A3A3A",
            "subway": "#FF5722"
        }
    
    with open(theme_file, 'r') as f:
        theme = json.load(f)
        print(f"✓ Loaded theme: {theme.get('name', theme_name)}")
        if 'description' in theme:
            print(f"  {theme['description']}")
        return theme

# Load theme (can be changed via command line or input)
THEME = None  # Will be loaded later

AVAILABLE_LAYERS = ["roads", "water", "parks", "subway"]
DEFAULT_LAYERS = ["roads", "water", "parks"]

def parse_layers_arg(layers_arg):
    """
    Parse comma-separated layers list and filter to known layers.
    Returns a list preserving input order.
    """
    if not layers_arg:
        return DEFAULT_LAYERS.copy()
    
    raw_layers = [layer.strip().lower() for layer in layers_arg.split(",")]
    layers = [layer for layer in raw_layers if layer in AVAILABLE_LAYERS]
    
    if not layers:
        return []
    
    # De-duplicate while preserving order
    seen = set()
    return [layer for layer in layers if not (layer in seen or seen.add(layer))]

def create_gradient_fade(ax, color, location='bottom', zorder=10, extent_size=0.25):
    """
    Creates a fade effect at the top or bottom of the map.
    
    Args:
        ax: matplotlib axes
        color: gradient color
        location: 'bottom' or 'top'
        zorder: z-order for layering
        extent_size: fraction of the image height for the gradient (default 0.25 = 25%)
    """
    vals = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack((vals, vals))
    
    rgb = mcolors.to_rgb(color)
    my_colors = np.zeros((256, 4))
    my_colors[:, 0] = rgb[0]
    my_colors[:, 1] = rgb[1]
    my_colors[:, 2] = rgb[2]
    
    if location == 'bottom':
        my_colors[:, 3] = np.linspace(1, 0, 256)
        extent_y_start = 0
        extent_y_end = extent_size
    else:
        my_colors[:, 3] = np.linspace(0, 1, 256)
        extent_y_start = 1.0 - extent_size
        extent_y_end = 1.0

    custom_cmap = mcolors.ListedColormap(my_colors)
    
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    y_range = ylim[1] - ylim[0]
    
    y_bottom = ylim[0] + y_range * extent_y_start
    y_top = ylim[0] + y_range * extent_y_end
    
    ax.imshow(gradient, extent=[xlim[0], xlim[1], y_bottom, y_top], 
              aspect='auto', cmap=custom_cmap, zorder=zorder, origin='lower')

def get_edge_colors_by_type(G):
    """
    Assigns colors to edges based on road type hierarchy.
    Returns a list of colors corresponding to each edge in the graph.
    """
    edge_colors = []
    
    for u, v, data in G.edges(data=True):
        # Get the highway type (can be a list or string)
        highway = data.get('highway', 'unclassified')
        
        # Handle list of highway types (take the first one)
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        
        # Assign color based on road type
        if highway in ['motorway', 'motorway_link']:
            color = THEME['road_motorway']
        elif highway in ['trunk', 'trunk_link', 'primary', 'primary_link']:
            color = THEME['road_primary']
        elif highway in ['secondary', 'secondary_link']:
            color = THEME['road_secondary']
        elif highway in ['tertiary', 'tertiary_link']:
            color = THEME['road_tertiary']
        elif highway in ['residential', 'living_street', 'unclassified']:
            color = THEME['road_residential']
        else:
            color = THEME['road_default']
        
        edge_colors.append(color)
    
    return edge_colors

def get_edge_widths_by_type(G):
    """
    Assigns line widths to edges based on road type.
    Major roads get thicker lines.
    """
    edge_widths = []
    
    for u, v, data in G.edges(data=True):
        highway = data.get('highway', 'unclassified')
        
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        
        # Assign width based on road importance
        if highway in ['motorway', 'motorway_link']:
            width = 1.2
        elif highway in ['trunk', 'trunk_link', 'primary', 'primary_link']:
            width = 1.0
        elif highway in ['secondary', 'secondary_link']:
            width = 0.8
        elif highway in ['tertiary', 'tertiary_link']:
            width = 0.6
        else:
            width = 0.4
        
        edge_widths.append(width)
    
    return edge_widths

def get_coordinates(city, country):
    """
    Fetches coordinates for a given city and country using geopy.
    Includes rate limiting to be respectful to the geocoding service.
    """
    print("Looking up coordinates...")
    geolocator = Nominatim(user_agent="city_map_poster")
    
    # Add a small delay to respect Nominatim's usage policy
    time.sleep(1)
    
    location = geolocator.geocode(f"{city}, {country}")
    
    if location:
        print(f"✓ Found: {location.address}")
        print(f"✓ Coordinates: {location.latitude}, {location.longitude}")
        return (location.latitude, location.longitude)
    else:
        raise ValueError(f"Could not find coordinates for {city}, {country}")

def create_poster(city, country, point, dist, output_file, layers, paper_size='3:4', grain=False, bounds=None, dpi=300):
    print(f"\nGenerating map for {city}, {country} (Size: {paper_size}, DPI: {dpi})...")
    
    # Define aspect ratios (width, height)
    aspect_ratios = {
        '1:1': (12, 12),
        '2:3': (12, 18),
        '3:4': (12, 16),
        '4:5': (12, 15),
        'DIN': (12, 12 * 1.414),  # A-series
        '9:16': (9, 16),
        '9:19.5': (9, 19.5),
    }
    
    width, height = aspect_ratios.get(paper_size, aspect_ratios['3:4'])
    
    layers_set = set(layers)
    fetch_steps = []
    if "roads" in layers_set:
        fetch_steps.append("Downloading street network")
    if "water" in layers_set:
        fetch_steps.append("Downloading water features")
    if "parks" in layers_set:
        fetch_steps.append("Downloading parks/green spaces")
    if "subway" in layers_set:
        fetch_steps.append("Downloading subway lines")
    
    G = None
    water = None
    parks = None
    subway = None
    
    # Use exact bounds if provided, otherwise use center point + distance
    use_exact_bounds = bounds is not None and all(k in bounds for k in ['north', 'south', 'east', 'west'])
    
    # Progress bar for data fetching
    with tqdm(total=len(fetch_steps), desc="Fetching map data", unit="step", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:
        if "roads" in layers_set:
            pbar.set_description("Downloading street network")
            if use_exact_bounds:
                G = ox.graph_from_bbox(bounds['north'], bounds['south'], bounds['east'], bounds['west'], network_type='all')
            else:
                G = ox.graph_from_point(point, dist=dist, dist_type='bbox', network_type='all')
            pbar.update(1)
            time.sleep(0.5)  # Rate limit between requests
        
        if "water" in layers_set:
            pbar.set_description("Downloading water features")
            try:
                if use_exact_bounds:
                    water = ox.features_from_bbox(bounds['north'], bounds['south'], bounds['east'], bounds['west'], 
                                                  tags={'natural': 'water', 'waterway': 'riverbank'})
                else:
                    water = ox.features_from_point(point, tags={'natural': 'water', 'waterway': 'riverbank'}, dist=dist)
            except:
                water = None
            pbar.update(1)
            time.sleep(0.3)
        
        if "parks" in layers_set:
            pbar.set_description("Downloading parks/green spaces")
            try:
                if use_exact_bounds:
                    parks = ox.features_from_bbox(bounds['north'], bounds['south'], bounds['east'], bounds['west'],
                                                  tags={'leisure': 'park', 'landuse': 'grass'})
                else:
                    parks = ox.features_from_point(point, tags={'leisure': 'park', 'landuse': 'grass'}, dist=dist)
            except:
                parks = None
            pbar.update(1)
            time.sleep(0.3)
        
        if "subway" in layers_set:
            pbar.set_description("Downloading subway lines")
            try:
                if use_exact_bounds:
                    subway = ox.features_from_bbox(bounds['north'], bounds['south'], bounds['east'], bounds['west'],
                                                   tags={'railway': ['subway', 'light_rail', 'tram']})
                else:
                    subway = ox.features_from_point(point, tags={'railway': ['subway', 'light_rail', 'tram']}, dist=dist)
            except:
                subway = None
            pbar.update(1)
    
    print("✓ All data downloaded successfully!")
    
    # 2. Setup Plot
    print("Rendering map...")
    fig, ax = plt.subplots(figsize=(width, height), facecolor=THEME['bg'])
    ax.set_facecolor(THEME['bg'])
    ax.set_position([0, 0, 1, 1])
    
    # 3. Plot Layers
    # Layer 1: Polygons
    if "water" in layers_set and water is not None and not water.empty:
        water.plot(ax=ax, facecolor=THEME['water'], edgecolor='none', zorder=1)
    if "parks" in layers_set and parks is not None and not parks.empty:
        parks.plot(ax=ax, facecolor=THEME['parks'], edgecolor='none', zorder=2)
    if "subway" in layers_set and subway is not None and not subway.empty:
        subway_color = THEME.get('subway', THEME.get('road_primary', '#111111'))
        subway.plot(ax=ax, color=subway_color, linewidth=0.6, zorder=3)
    
    # Layer 2: Roads with hierarchy coloring
    if "roads" in layers_set and G is not None:
        print("Applying road hierarchy colors...")
        edge_colors = get_edge_colors_by_type(G)
        edge_widths = get_edge_widths_by_type(G)
        
        ox.plot_graph(
            G, ax=ax, bgcolor=THEME['bg'],
            node_size=0,
            edge_color=edge_colors,
            edge_linewidth=edge_widths,
            show=False, close=False
        )
    
    # Preserve geographic aspect ratio and crop to fill the paper format
    ax.set_aspect('equal')
    
    # When using exact bounds, only do minimal cropping to match aspect ratio
    # Otherwise, crop more aggressively to fill the paper format
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    
    data_width = xlim[1] - xlim[0]
    data_height = ylim[1] - ylim[0]
    data_center_x = (xlim[0] + xlim[1]) / 2
    data_center_y = (ylim[0] + ylim[1]) / 2
    
    # Target aspect ratio from paper size (width / height)
    target_ratio = width / height
    current_ratio = data_width / data_height
    
    # If using exact bounds, be less aggressive with cropping (allow 5% tolerance)
    if use_exact_bounds:
        tolerance = 0.05
        ratio_diff = abs(current_ratio - target_ratio) / target_ratio
        
        if ratio_diff > tolerance:
            if current_ratio > target_ratio:
                # Data is slightly wider - crop width minimally
                new_width = data_height * target_ratio
                ax.set_xlim(data_center_x - new_width / 2, data_center_x + new_width / 2)
            else:
                # Data is slightly taller - crop height minimally
                new_height = data_width / target_ratio
                ax.set_ylim(data_center_y - new_height / 2, data_center_y + new_height / 2)
    else:
        # Original behavior for center+distance mode
        if current_ratio > target_ratio:
            # Data is wider than target - crop width to fit
            new_width = data_height * target_ratio
            ax.set_xlim(data_center_x - new_width / 2, data_center_x + new_width / 2)
        else:
            # Data is taller than target - crop height to fit
            new_height = data_width / target_ratio
            ax.set_ylim(data_center_y - new_height / 2, data_center_y + new_height / 2)
    
    # Layer 3: Gradients (Top and Bottom)
    create_gradient_fade(ax, THEME['gradient_color'], location='bottom', zorder=10)
    
    # For iPhone lock screen (9:19.5), use a taller top gradient to blend with 
    # the time display and widgets
    if paper_size == '9:19.5':
        create_gradient_fade(ax, THEME['gradient_color'], location='top', zorder=10, extent_size=0.40)
    else:
        create_gradient_fade(ax, THEME['gradient_color'], location='top', zorder=10)
    
    # 4. Typography using Roboto font
    if FONTS:
        font_main = FontProperties(fname=FONTS['bold'], size=60)
        font_top = FontProperties(fname=FONTS['bold'], size=40)
        font_sub = FontProperties(fname=FONTS['light'], size=22)
        font_coords = FontProperties(fname=FONTS['regular'], size=14)
    else:
        # Fallback to system fonts
        font_main = FontProperties(family='monospace', weight='bold', size=60)
        font_top = FontProperties(family='monospace', weight='bold', size=40)
        font_sub = FontProperties(family='monospace', weight='normal', size=22)
        font_coords = FontProperties(family='monospace', size=14)
    
    spaced_city = "  ".join(list(city.upper()))

    # --- BOTTOM TEXT ---
    ax.text(0.5, 0.14, spaced_city, transform=ax.transAxes,
            color=THEME['text'], ha='center', fontproperties=font_main, zorder=11)
    
    ax.text(0.5, 0.10, country.upper(), transform=ax.transAxes,
            color=THEME['text'], ha='center', fontproperties=font_sub, zorder=11)
    
    lat, lon = point
    coords = f"{lat:.4f}° N / {lon:.4f}° E" if lat >= 0 else f"{abs(lat):.4f}° S / {lon:.4f}° E"
    if lon < 0:
        coords = coords.replace("E", "W")
    
    ax.text(0.5, 0.07, coords, transform=ax.transAxes,
            color=THEME['text'], alpha=0.7, ha='center', fontproperties=font_coords, zorder=11)
    
    ax.plot([0.4, 0.6], [0.125, 0.125], transform=ax.transAxes, 
            color=THEME['text'], linewidth=1, zorder=11)

    # --- ATTRIBUTION (bottom right) ---
    if FONTS:
        font_attr = FontProperties(fname=FONTS['light'], size=8)
    else:
        font_attr = FontProperties(family='monospace', size=8)
    
    ax.text(0.98, 0.02, "© OpenStreetMap contributors", transform=ax.transAxes,
            color=THEME['text'], alpha=0.5, ha='right', va='bottom', 
            fontproperties=font_attr, zorder=11)

    # 5. Save with post-processing
    print(f"Saving to {output_file}...")
    apply_post_processing(fig, output_file, paper_size=paper_size, grain=grain, bg_color=THEME['bg'], dpi=dpi)
    plt.close()
    print(f"✓ Done! Poster saved as {output_file}")

def print_examples():
    """Print usage examples."""
    print("""
City Map Poster Generator
=========================

Usage:
  python create_map_poster.py --city <city> --country <country> [options]

Examples:
  # Iconic grid patterns
  python create_map_poster.py -c "New York" -C "USA" -t noir -d 12000           # Manhattan grid
  python create_map_poster.py -c "Barcelona" -C "Spain" -t warm_beige -d 8000   # Eixample district grid
  
  # Waterfront & canals
  python create_map_poster.py -c "Venice" -C "Italy" -t blueprint -d 4000       # Canal network
  python create_map_poster.py -c "Amsterdam" -C "Netherlands" -t ocean -d 6000  # Concentric canals
  python create_map_poster.py -c "Dubai" -C "UAE" -t midnight_blue -d 15000     # Palm & coastline
  
  # Radial patterns
  python create_map_poster.py -c "Paris" -C "France" -t pastel_dream -d 10000   # Haussmann boulevards
  python create_map_poster.py -c "Moscow" -C "Russia" -t noir -d 12000          # Ring roads
  
  # Organic old cities
  python create_map_poster.py -c "Tokyo" -C "Japan" -t japanese_ink -d 15000    # Dense organic streets
  python create_map_poster.py -c "Marrakech" -C "Morocco" -t terracotta -d 5000 # Medina maze
  python create_map_poster.py -c "Rome" -C "Italy" -t warm_beige -d 8000        # Ancient street layout
  
  # Coastal cities
  python create_map_poster.py -c "San Francisco" -C "USA" -t sunset -d 10000    # Peninsula grid
  python create_map_poster.py -c "Sydney" -C "Australia" -t ocean -d 12000      # Harbor city
  python create_map_poster.py -c "Mumbai" -C "India" -t contrast_zones -d 18000 # Coastal peninsula
  
  # River cities
  python create_map_poster.py -c "London" -C "UK" -t noir -d 15000              # Thames curves
  python create_map_poster.py -c "Budapest" -C "Hungary" -t copper_patina -d 8000  # Danube split
  
  # List themes
  python create_map_poster.py --list-themes

Options:
  --city, -c        City name (required)
  --country, -C     Country name (required)
  --theme, -t       Theme name (default: feature_based)
  --distance, -d    Map radius in meters (default: 29000)
  --list-themes     List all available themes

Distance guide:
  4000-6000m   Small/dense cities (Venice, Amsterdam old center)
  8000-12000m  Medium cities, focused downtown (Paris, Barcelona)
  15000-20000m Large metros, full city view (Tokyo, Mumbai)

Available themes can be found in the 'themes/' directory.
Generated posters are saved to 'posters/' directory.
""")

def list_themes():
    """List all available themes with descriptions."""
    available_themes = get_available_themes()
    if not available_themes:
        print("No themes found in 'themes/' directory.")
        return
    
    print("\nAvailable Themes:")
    print("-" * 60)
    for theme_name in available_themes:
        theme_path = os.path.join(THEMES_DIR, f"{theme_name}.json")
        try:
            with open(theme_path, 'r') as f:
                theme_data = json.load(f)
                display_name = theme_data.get('name', theme_name)
                description = theme_data.get('description', '')
        except:
            display_name = theme_name
            description = ''
        print(f"  {theme_name}")
        print(f"    {display_name}")
        if description:
            print(f"    {description}")
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate beautiful map posters for any city",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python create_map_poster.py --city "New York" --country "USA"
  python create_map_poster.py --city Tokyo --country Japan --theme midnight_blue
  python create_map_poster.py --city Paris --country France --theme noir --distance 15000
  python create_map_poster.py --list-themes
        """
    )
    
    parser.add_argument('--city', '-c', type=str, help='City name')
    parser.add_argument('--country', '-C', type=str, help='Country name')
    parser.add_argument('--theme', '-t', type=str, default='feature_based', help='Theme name (default: feature_based)')
    parser.add_argument('--distance', '-d', type=int, default=29000, help='Map radius in meters (default: 29000)')
    parser.add_argument('--list-themes', action='store_true', help='List all available themes')
    parser.add_argument('--layers', type=str, help='Comma-separated layers (roads,water,parks,subway)')
    parser.add_argument('--paper-size', '-s', type=str, default='3:4', choices=['1:1', '2:3', '3:4', '4:5', 'DIN', '9:16', '9:19.5'], help='Paper size / aspect ratio (default: 3:4)')
    parser.add_argument('--lat', type=float, help='Latitude for the map center')
    parser.add_argument('--lng', type=float, help='Longitude for the map center')
    parser.add_argument('--grain', action='store_true', help='Add film grain/noise effect to the image')
    parser.add_argument('--bounds', type=str, help='Exact map bounds as north,south,east,west (e.g., 40.7589,-74.0060,40.7489,-74.0160)')
    parser.add_argument('--dpi', type=int, default=300, choices=[72, 150, 300], help='Output resolution in DPI (default: 300)')
    
    args = parser.parse_args()
    
    # If no arguments provided, show examples
    if len(os.sys.argv) == 1:
        print_examples()
        os.sys.exit(0)
    
    # List themes if requested
    if args.list_themes:
        list_themes()
        os.sys.exit(0)
    
    # Validate required arguments
    if not args.city or not args.country:
        print("Error: --city and --country are required.\n")
        print_examples()
        os.sys.exit(1)
    
    # Validate theme exists
    available_themes = get_available_themes()
    if args.theme not in available_themes:
        print(f"Error: Theme '{args.theme}' not found.")
        print(f"Available themes: {', '.join(available_themes)}")
        os.sys.exit(1)
    
    print("=" * 50)
    print("City Map Poster Generator")
    print("=" * 50)
    
    # Load theme
    THEME = load_theme(args.theme)
    layers = parse_layers_arg(args.layers)
    
    # Parse bounds if provided
    bounds = None
    if args.bounds:
        try:
            parts = [float(x.strip()) for x in args.bounds.split(',')]
            if len(parts) == 4:
                bounds = {
                    'north': parts[0],
                    'south': parts[1],
                    'east': parts[2],
                    'west': parts[3]
                }
                print(f"✓ Using provided bounds: N={bounds['north']}, S={bounds['south']}, E={bounds['east']}, W={bounds['west']}")
            else:
                print("⚠ Invalid bounds format. Expected: north,south,east,west")
        except ValueError:
            print("⚠ Invalid bounds values. Expected numeric values.")
    
    # Get coordinates and generate poster
    try:
        if args.lat is not None and args.lng is not None:
            coords = (args.lat, args.lng)
            print(f"✓ Using provided coordinates: {coords}")
        else:
            coords = get_coordinates(args.city, args.country)
            
        output_file = generate_output_filename(args.city, args.theme)
        create_poster(args.city, args.country, coords, args.distance, output_file, layers, args.paper_size, args.grain, bounds, args.dpi)
        
        print("\n" + "=" * 50)
        print("✓ Poster generation complete!")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        os.sys.exit(1)
