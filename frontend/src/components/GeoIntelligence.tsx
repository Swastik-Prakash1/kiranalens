import React from 'react';
import { MapPin, Store, Users, Navigation } from 'lucide-react';

interface GeoIntelligenceProps {
  lat: number;
  lng: number;
  cityTier: string;
  indiaRegion: string;
  roadType: string;
  footfallProxy: number;
  competitionCount: number;
  amenityScore: number;
  geoMultiplier: number;
}

const GeoIntelligence: React.FC<GeoIntelligenceProps> = ({
  lat,
  lng,
  cityTier,
  indiaRegion,
  roadType,
  footfallProxy,
  competitionCount,
  amenityScore,
  geoMultiplier,
}) => {
  return (
    <div className="card">
      <div className="card-header">
        <MapPin className="card-icon" size={18} />
        <h3>Geo Intelligence</h3>
      </div>

      {/* Map placeholder */}
      <div className="map-placeholder">
        <div style={{ textAlign: 'center' }}>
          <Navigation size={24} style={{ color: 'var(--accent)', marginBottom: 6 }} />
          <div className="data-text" style={{ fontSize: '0.75rem' }}>
            {lat.toFixed(4)}, {lng.toFixed(4)}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>
            {indiaRegion.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
          </div>
        </div>
      </div>

      {/* Geo metrics strip */}
      <div className="geo-strip" style={{ marginTop: 12 }}>
        <div className="geo-chip">
          <div className="geo-chip-label">City Tier</div>
          <div className="geo-chip-value" style={{ color: 'var(--accent)' }}>
            {cityTier.replace('_', ' ')}
          </div>
        </div>

        <div className="geo-chip">
          <div className="geo-chip-label">Road</div>
          <div className="geo-chip-value">{roadType}</div>
        </div>

        <div className="geo-chip">
          <div className="geo-chip-label">
            <Users size={10} style={{ marginRight: 2 }} />
            Footfall
          </div>
          <div className="geo-chip-value">{(footfallProxy * 100).toFixed(0)}%</div>
        </div>

        <div className="geo-chip">
          <div className="geo-chip-label">
            <Store size={10} style={{ marginRight: 2 }} />
            Nearby
          </div>
          <div className="geo-chip-value">{competitionCount}</div>
        </div>

        <div className="geo-chip">
          <div className="geo-chip-label">Amenities</div>
          <div className="geo-chip-value">{(amenityScore * 100).toFixed(0)}%</div>
        </div>

        <div className="geo-chip">
          <div className="geo-chip-label">Geo x</div>
          <div className="geo-chip-value" style={{ color: 'var(--accent)' }}>
            {geoMultiplier.toFixed(2)}x
          </div>
        </div>
      </div>
    </div>
  );
};

export default GeoIntelligence;
