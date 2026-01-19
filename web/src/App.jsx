import React, { useState, useEffect, useRef } from 'react';
import './index.css';

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

function App() {
  const [themes, setThemes] = useState([]);
  const [posters, setPosters] = useState([]);
  const [loading, setLoading] = useState(false);
  const [currentPoster, setCurrentPoster] = useState(null);

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
    { id: 'DIN', label: 'DIN (A4, A3)' }
  ];
  
  const [formData, setFormData] = useState({
    city: '',
    country: '',
    theme: 'feature_based',
    distance: 12000,
    layers: ['roads', 'water', 'parks'],
    paper_size: '3:4'
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
            <div className="form-group">
              <label>City</label>
              <input
                type="text"
                name="city"
                placeholder="e.g. Barcelona"
                value={formData.city}
                onChange={handleInputChange}
                required
              />
            </div>

            <div className="form-group">
              <label>Country</label>
              <input
                type="text"
                name="country"
                placeholder="e.g. Spain"
                value={formData.country}
                onChange={handleInputChange}
                required
              />
            </div>

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

            <div className="form-group">
              <label>Radius (meters)</label>
              <input
                type="number"
                name="distance"
                value={formData.distance}
                onChange={handleInputChange}
                min="1000"
                max="50000"
              />
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

        <div className="preview-section">
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
          
          {currentPoster ? (
            <img 
              src={currentPoster.url} 
              alt="Generated Poster" 
              className="poster-preview"
            />
          ) : (
            <div className="empty-state">
              <p>Your poster will appear here</p>
            </div>
          )}
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
