import React from 'react';
import { Package } from 'lucide-react';

const CATEGORY_COLORS: Record<string, string> = {
  'Packaged Foods': '#00C864',
  'Beverages': '#C86400',
  'Dairy Products': '#00C8FF',
  'Personal Care': '#0064FF',
  'Household Items': '#B400B4',
  'Snacks': '#FFD700',
  'Staples': '#969600',
  'Cooking Oils': '#DCB432',
  'Mobile Accessories': '#5050FF',
  'Electronics': '#3232FF',
  'Health & Wellness': '#64FF64',
  'Stationery': '#C8C864',
  'Chocolates': '#A05020',
  'Cleaning': '#00C8C8',
  'Other Items': '#787878',
};

interface CategoryTableProps {
  categoryCounts: Record<string, number>;
}

const CategoryTable: React.FC<CategoryTableProps> = ({ categoryCounts }) => {
  const entries = Object.entries(categoryCounts);
  const maxCount = Math.max(...entries.map(([, v]) => v), 1);
  const total = entries.reduce((s, [, v]) => s + v, 0);

  return (
    <div className="card">
      <div className="card-header">
        <Package className="card-icon" size={18} />
        <h3>Category Breakdown</h3>
        <span
          className="data-text"
          style={{
            marginLeft: 'auto',
            fontSize: '0.7rem',
            color: 'var(--text-muted)',
          }}
        >
          {total} items
        </span>
      </div>

      {entries.map(([category, count]) => {
        const pct = Math.round((count / maxCount) * 100);
        const color = CATEGORY_COLORS[category] || '#787878';

        return (
          <div className="category-row" key={category}>
            <div className="category-label">
              <span className="category-dot" style={{ background: color }} />
              <span>{category}</span>
            </div>
            <div className="category-bar-container">
              <div
                className="category-bar"
                style={{
                  width: `${pct}%`,
                  background: color,
                }}
              />
            </div>
            <span className="category-count">{count}</span>
          </div>
        );
      })}
    </div>
  );
};

export default CategoryTable;
