import React from 'react';
import { Eye, Layers, PackageSearch, Gauge, RefreshCw } from 'lucide-react';

interface VisionFeaturesProps {
  sdi: number;
  sdiConfidence: number;
  skuDiversityScore: number;
  skuDiversityLabel: string;
  inventoryDensityScore: number;
  refillSignal: string;
  totalProducts: number;
  detectionMethod: string;
  cocoDetectionsUsed: number;
}

const REFILL_COLORS: Record<string, string> = {
  RECENT_RESTOCK: 'var(--accent)',
  NORMAL: 'var(--info)',
  LOW_STOCK: 'var(--warning)',
  STAGED: 'var(--danger)',
};

const VisionFeaturesCard: React.FC<VisionFeaturesProps> = ({
  sdi,
  sdiConfidence,
  skuDiversityScore,
  skuDiversityLabel,
  inventoryDensityScore,
  refillSignal,
  totalProducts,
  detectionMethod,
  cocoDetectionsUsed,
}) => {
  return (
    <div className="card">
      <div className="card-header">
        <Eye className="card-icon" size={18} />
        <h3>Vision Analysis</h3>
        <span
          className="data-text"
          style={{
            marginLeft: 'auto',
            fontSize: '0.65rem',
            color: 'var(--text-muted)',
            background: 'var(--bg-elevated)',
            padding: '2px 8px',
            borderRadius: '4px',
          }}
        >
          {detectionMethod.toUpperCase()}
        </span>
      </div>

      <div className="metrics-grid">
        {/* SDI */}
        <div className="metric-card">
          <div className="metric-label">
            <Layers size={12} style={{ marginRight: 4, verticalAlign: 'text-bottom' }} />
            Shelf Density
          </div>
          <div className="metric-value accent">{(sdi * 100).toFixed(0)}%</div>
          <div className="confidence-bar" style={{ marginTop: 6 }}>
            <div className="confidence-fill" style={{ width: `${sdiConfidence * 100}%` }} />
          </div>
          <div className="metric-sub">Conf: {(sdiConfidence * 100).toFixed(0)}%</div>
        </div>

        {/* SKU Diversity */}
        <div className="metric-card">
          <div className="metric-label">
            <PackageSearch size={12} style={{ marginRight: 4, verticalAlign: 'text-bottom' }} />
            SKU Diversity
          </div>
          <div className="metric-value">{(skuDiversityScore * 100).toFixed(0)}%</div>
          <div className="metric-sub" style={{ color: 'var(--accent)' }}>{skuDiversityLabel}</div>
        </div>

        {/* Products Detected */}
        <div className="metric-card">
          <div className="metric-label">
            <Gauge size={12} style={{ marginRight: 4, verticalAlign: 'text-bottom' }} />
            Products
          </div>
          <div className="metric-value">{totalProducts}</div>
          <div className="metric-sub">
            {cocoDetectionsUsed > 0 ? `${cocoDetectionsUsed} COCO` : 'Spatial inference'}
          </div>
        </div>

        {/* Inventory Density */}
        <div className="metric-card">
          <div className="metric-label">Inventory Density</div>
          <div className="metric-value">{(inventoryDensityScore * 100).toFixed(0)}%</div>
        </div>

        {/* Refill Signal */}
        <div className="metric-card">
          <div className="metric-label">
            <RefreshCw size={12} style={{ marginRight: 4, verticalAlign: 'text-bottom' }} />
            Refill Signal
          </div>
          <div
            className="metric-value data-text"
            style={{
              fontSize: '0.85rem',
              color: REFILL_COLORS[refillSignal] || 'var(--text-primary)',
            }}
          >
            {refillSignal.replace('_', ' ')}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VisionFeaturesCard;
