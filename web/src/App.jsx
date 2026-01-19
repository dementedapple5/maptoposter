import React, { useState, useEffect, useRef } from 'react';
import { MapContainer, TileLayer, useMap, useMapEvents, Marker } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import './index.css';

// Fix Leaflet marker icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const MapEvents = ({ onBoundsChange }) => {
  const map = useMapEvents({
    moveend: () => {
      const center = map.getCenter();
      const bounds = map.getBounds();
      onBoundsChange(center, bounds);
    },
    zoomend: () => {
      const center = map.getCenter();
      const bounds = map.getBounds();
      onBoundsChange(center, bounds);
    },
  });
  return null;
};

const ChangeMapView = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    if (center) {
      map.setView(center, zoom);
    }
  }, [center, zoom, map]);
  return null;
};

const MapResizer = ({ aspectRatio }) => {
  const map = useMap();
  useEffect(() => {
    // Small delay to allow the container to resize first
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 100);
    return () => clearTimeout(timer);
  }, [aspectRatio, map]);
  return null;
};

const LocationAutocomplete = ({ value, onChange, onNavigate }) => {
  const [query, setQuery] = useState(value || '');
  const [suggestions, setSuggestions] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    const normalizeNominatimResult = (result) => {
      const address = result.address || {};
      const city = address.city
        || address.town
        || address.village
        || address.municipality
        || address.state
        || '';
      const country = address.country || '';
      const displayName = result.display_name || '';
      const simpleName = city && country
        ? `${city}, ${country}`
        : displayName.split(', ').slice(0, 2).join(', ');

      return {
        display_name: simpleName || displayName,
        full_name: displayName,
        lat: parseFloat(result.lat),
        lng: parseFloat(result.lon),
        city,
        country
      };
    };

    const searchLocations = async () => {
      if (query.length < 2) {
        setSuggestions([]);
        return;
      }

      setIsLoading(true);
      try {
        const response = await fetch('/api/location-search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query })
        });

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('Location search endpoint not available');
          }
          const errorText = await response.text();
          throw new Error(errorText || 'Location search failed');
        }

        const data = await response.json();
        setSuggestions(data);
        setIsOpen(data.length > 0);
      } catch (error) {
        try {
          const nominatimResponse = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&limit=5&q=${encodeURIComponent(query)}`,
            { headers: { Accept: 'application/json' } }
          );
          const nominatimData = await nominatimResponse.json();
          const normalized = nominatimData.map(normalizeNominatimResult);
          setSuggestions(normalized);
          setIsOpen(normalized.length > 0);
        } catch (fallbackError) {
          console.error('Location search error:', error, fallbackError);
          setSuggestions([]);
        }
      } finally {
        setIsLoading(false);
      }
    };

    const timer = setTimeout(searchLocations, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (location) => {
    setQuery(location.display_name);
    setSelectedLocation(location);
    setIsOpen(false);
    onChange(location);
  };

  const handleNavigate = (e, location) => {
    e.stopPropagation();
    if (location || selectedLocation) {
      onNavigate(location || selectedLocation);
    }
  };

  const handleInputChange = (e) => {
    setQuery(e.target.value);
    setSelectedLocation(null);
  };

  return (
    <div className="form-group location-autocomplete" ref={dropdownRef}>
      <label>Location</label>
      <div className="location-input-wrapper">
        <input
          ref={inputRef}
          type="text"
          placeholder="e.g. Madrid, Spain"
          value={query}
          onChange={handleInputChange}
          onFocus={() => suggestions.length > 0 && setIsOpen(true)}
        />
        {isLoading && (
          <div className="location-loading">
            <div className="loading-spinner" />
          </div>
        )}
        {selectedLocation && !isLoading && (
          <button
            type="button"
            className="navigate-button"
            onClick={(e) => handleNavigate(e, selectedLocation)}
            title="Navigate to location"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" fill="currentColor"/>
              <circle cx="12" cy="9" r="2.5" fill="white"/>
            </svg>
          </button>
        )}
      </div>
      {isOpen && suggestions.length > 0 && (
        <div className="location-suggestions">
          {suggestions.map((location, index) => (
            <div 
              key={index}
              className="location-suggestion-item"
              onClick={() => handleSelect(location)}
            >
              <div className="suggestion-content">
                <span className="suggestion-name">{location.display_name}</span>
                {location.full_name !== location.display_name && (
                  <span className="suggestion-full">{location.full_name}</span>
                )}
              </div>
              <button
                type="button"
                className="suggestion-navigate"
                onClick={(e) => {
                  e.stopPropagation();
                  handleSelect(location);
                  onNavigate(location);
                }}
                title="Go to location"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const CustomSelect = ({ label, value, options, onChange, name }) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);
  const selectedOption = options.find(opt => (opt.id || opt.value) === value);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="form-group custom-select" ref={dropdownRef}>
      <label>{label}</label>
      <div className={`custom-select-trigger ${isOpen ? 'open-trigger' : ''}`} onClick={() => setIsOpen(!isOpen)}>
        <span className="selected-value">{selectedOption ? (selectedOption.name || selectedOption.label) : value}</span>
        <div className={`chevron ${isOpen ? 'open' : ''}`}>
          <svg width="12" height="8" viewBox="0 0 12 8" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M1 1.5L6 6.5L11 1.5" stroke="black" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
      </div>
      {isOpen && (
        <div className="custom-select-menu">
          {options.map(option => (
            <div 
              key={option.id || option.value} 
              className={`custom-select-item ${ (option.id || option.value) === value ? 'selected' : ''}`}
              onClick={() => {
                onChange({ target: { name, value: option.id || option.value } });
                setIsOpen(false);
              }}
            >
              <div className="item-content">
                <span className="checkmark-space">
                  {(option.id || option.value) === value && "✓"}
                </span>
                <span className="item-label">{option.name || option.label}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

const getAspectRatioValue = (sizeId) => {
  switch (sizeId) {
    case '1:1': return 1;
    case '2:3': return 2 / 3;
    case '3:4': return 3 / 4;
    case '4:5': return 4 / 5;
    case 'DIN': return 1 / 1.414;
    case '9:16': return 9 / 16;
    case '9:21': return 9 / 21;
    default: return 3 / 4;
  }
};

const getPosterDimensions = (sizeId, maxWidth = 720, maxHeight = 700) => {
  const aspectRatio = getAspectRatioValue(sizeId);
  
  // Calculate dimensions that fit within constraints while maintaining aspect ratio
  let width = maxWidth;
  let height = width / aspectRatio;
  
  // If height exceeds max, recalculate based on height constraint
  if (height > maxHeight) {
    height = maxHeight;
    width = height * aspectRatio;
  }
  
  return { width, height };
};

function App() {
  const [themes, setThemes] = useState([]);
  const [posters, setPosters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentPoster, setCurrentPoster] = useState(null);
  const [mapState, setMapState] = useState({
    center: [41.3851, 2.1734], // Barcelona default
    zoom: 13
  });

  const availableLayers = [
    { id: 'roads', label: 'Roads' },
    { id: 'water', label: 'Water' },
    { id: 'parks', label: 'Parks' },
    { id: 'subway', label: 'Subways' }
  ];

  const paperSizes = [
    { id: '1:1', label: 'Square (1:1)' },
    { id: '2:3', label: 'Poster (2:3)' },
    { id: '3:4', label: 'Classic (3:4)' },
    { id: '4:5', label: 'Frame (4:5)' },
    { id: 'DIN', label: 'DIN (A4, A3)' },
    { id: '9:16', label: '9:16 (Story)' },
    { id: '9:21', label: '9:21 (iPhone)' }
  ];
  
  const [formData, setFormData] = useState({
    location: '',
    city: '',
    country: '',
    theme: 'feature_based',
    distance: 12000,
    layers: ['roads', 'water', 'parks'],
    paper_size: '3:4',
    lat: null,
    lng: null
  });

  useEffect(() => {
    fetchThemes();
    fetchPosters();
  }, []);

  const fetchThemes = async () => {
    try {
      const response = await fetch('/api/themes');
      const data = await response.json();
      setThemes(data);
    } catch (error) {
      console.error('Error fetching themes:', error);
    }
  };

  const fetchPosters = async () => {
    try {
      const response = await fetch('/api/posters');
      const data = await response.json();
      setPosters(data);
    } catch (error) {
      console.error('Error fetching posters:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'distance' ? parseInt(value) || 0 : value
    }));
  };

  // Handle location selection from autocomplete
  const handleLocationSelect = (location) => {
    setFormData(prev => ({
      ...prev,
      location: location.display_name,
      city: location.city || location.display_name.split(',')[0].trim(),
      country: location.country || '',
      lat: location.lat,
      lng: location.lng
    }));
  };

  // Navigate to location on map
  const handleNavigateToLocation = (location) => {
    setMapState({
      center: [location.lat, location.lng],
      zoom: 13
    });
    setFormData(prev => ({
      ...prev,
      lat: location.lat,
      lng: location.lng
    }));
    // Clear current poster to show the map
    setCurrentPoster(null);
  };

  const handleBoundsChange = (center, bounds) => {
    const northEast = bounds.getNorthEast();
    const centerLatLng = L.latLng(center.lat, center.lng);
    const northCenter = L.latLng(northEast.lat, center.lng);
    const dist = centerLatLng.distanceTo(northCenter); // Radius in meters
    
    setFormData(prev => ({
      ...prev,
      lat: center.lat,
      lng: center.lng,
      distance: Math.round(dist)
    }));
  };

  const toggleLayer = (layerId) => {
    setFormData(prev => {
      const layers = prev.layers.includes(layerId)
        ? prev.layers.filter(layer => layer !== layerId)
        : [...prev.layers, layerId];
      return { ...prev, layers };
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate that we have coordinates (either from location selection or map interaction)
    if (!formData.lat || !formData.lng) {
      alert('Please select a location from the suggestions or navigate on the map');
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      const data = await response.json();
      if (response.ok) {
        setCurrentPoster(data);
        fetchPosters();
      } else {
        alert(`Error: ${data.detail || 'Unknown error'}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const downloadPoster = () => {
    if (!currentPoster) return;
    const link = document.createElement('a');
    link.href = currentPoster.url;
    link.download = currentPoster.filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="container">
      <header>
        <h1>City Map Poster</h1>
        <p className="subtitle">Minimalist urban art generator</p>
      </header>

      <div className="main-layout">
        <div className="form-section">
          <form onSubmit={handleSubmit}>
            <LocationAutocomplete
              value={formData.location}
              onChange={handleLocationSelect}
              onNavigate={handleNavigateToLocation}
            />

            <CustomSelect
              label="Theme"
              name="theme"
              value={formData.theme}
              options={themes}
              onChange={handleInputChange}
            />

            <CustomSelect
              label="Paper Size"
              name="paper_size"
              value={formData.paper_size}
              options={paperSizes}
              onChange={handleInputChange}
            />

            <div className="form-group">
              <label>Layers</label>
              <div className="chip-group">
                {availableLayers.map(layer => (
                  <button
                    key={layer.id}
                    type="button"
                    className={`chip ${formData.layers.includes(layer.id) ? 'active' : ''}`}
                    onClick={() => toggleLayer(layer.id)}
                  >
                    {layer.label}
                  </button>
                ))}
              </div>
            </div>

            <button 
              type="submit" 
              className="primary" 
              disabled={loading}
            >
              {loading ? 'Generating...' : 'Generate Poster'}
            </button>
          </form>

          {currentPoster && (
            <button 
              onClick={downloadPoster} 
              className="primary"
              style={{ background: '#fff', color: '#000', border: '1px solid #000' }}
            >
              Download PNG
            </button>
          )}
        </div>

        <div 
          className="preview-section"
          style={{
            width: getPosterDimensions(formData.paper_size).width + 64,
            height: getPosterDimensions(formData.paper_size).height + 64
          }}
        >
          {loading && (
            <div className="loading-overlay" style={{ background: '#fff' }}>
              <div className="pixel-grid">
                {[...Array(900)].map((_, i) => (
                  <div 
                    key={i} 
                    className="pixel"
                    style={{ 
                      animationDelay: `${Math.random() * 2}s`,
                      backgroundColor: `rgba(0,0,0,${0.3 + Math.random() * 0.7})`
                    }}
                  />
                ))}
              </div>
            </div>
          )}
          
          <div 
            className="poster-container" 
            style={getPosterDimensions(formData.paper_size)}
          >
            {!currentPoster && !loading ? (
              <MapContainer 
                center={mapState.center} 
                zoom={mapState.zoom} 
                style={{ height: '100%', width: '100%' }}
                scrollWheelZoom={true}
              >
                <TileLayer
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                />
                <MapEvents onBoundsChange={handleBoundsChange} />
                <ChangeMapView center={mapState.center} zoom={mapState.zoom} />
                <MapResizer aspectRatio={formData.paper_size} />
                <Marker position={mapState.center} />
              </MapContainer>
            ) : currentPoster ? (
              <img 
                src={currentPoster.url} 
                alt="Generated Poster" 
                className="poster-preview"
                onClick={() => setCurrentPoster(null)}
                title="Click to change location"
              />
            ) : (
              <div className="empty-state">
                <p>Generating your masterpiece...</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {posters.length > 0 && (
        <div className="gallery">
          <h2>Recent Creations</h2>
          <div className="gallery-grid">
            {posters.slice(0, 8).map((poster, index) => (
              <div 
                key={index} 
                className="gallery-item"
                onClick={() => setCurrentPoster(poster)}
              >
                <img src={poster.url} alt={poster.filename} />
                <p>{poster.filename.split('_')[0].toUpperCase()}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
