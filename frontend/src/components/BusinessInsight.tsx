import React from 'react';
import { Lightbulb } from 'lucide-react';

interface BusinessInsightProps {
  insight: string;
}

const BusinessInsight: React.FC<BusinessInsightProps> = ({ insight }) => {
  if (!insight) return null;

  return (
    <div className="insight-callout">
      <div className="insight-label">
        <Lightbulb size={12} style={{ marginRight: 4, verticalAlign: 'text-bottom' }} />
        AI Business Insight
      </div>
      <p>{insight}</p>
    </div>
  );
};

export default BusinessInsight;
