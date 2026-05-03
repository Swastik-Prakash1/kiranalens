import React from 'react';

const CATEGORY_COLORS: Record<string, string> = {
  'Packaged Foods': '#00C864',
  'Beverages': '#C86400',
  'Dairy Products': '#00C8FF',
  'Personal Care': '#0064FF',
  'Household Items': '#B400B4',
  'Snacks': '#00C8FF',
  'Staples': '#969600',
  'Other Items': '#787878',
};

interface AnnotatedImageProps {
  imageB64: string | null;
  categoryColors?: Record<string, string>;
}

const AnnotatedImage: React.FC<AnnotatedImageProps> = ({
  imageB64,
  categoryColors = CATEGORY_COLORS,
}) => {
  if (!imageB64) {
    return (
      <div className="annotated-image-container">
        <div
          style={{
            height: 220,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-muted)',
            fontSize: '0.8rem',
          }}
        >
          Annotated image available after live analysis
        </div>
      </div>
    );
  }

  return (
    <div className="annotated-image-container">
      <img src={imageB64} alt="Annotated shelf detection" />
      <div className="image-legend">
        {Object.entries(categoryColors).map(([cat, color]) => (
          <div key={cat} className="legend-item">
            <span className="legend-color" style={{ background: color }} />
            <span>{cat}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AnnotatedImage;
