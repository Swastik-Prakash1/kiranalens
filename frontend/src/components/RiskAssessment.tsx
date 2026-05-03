import React from 'react';
import { ShieldCheck, AlertTriangle } from 'lucide-react';

interface RiskFlagItem {
  flag_type: string;
  severity: string;
  confidence: number;
  evidence: string;
  recommendation: string;
}

interface RiskAssessmentProps {
  manipulationProbability: number;
  recommendation: string;
  riskFlags: RiskFlagItem[];
  consistencyAssessment: string;
}

const RiskAssessment: React.FC<RiskAssessmentProps> = ({
  manipulationProbability,
  recommendation,
  riskFlags,
  consistencyAssessment,
}) => {
  const badgeClass =
    recommendation === 'APPROVE'
      ? 'approve'
      : recommendation === 'VERIFY'
      ? 'verify'
      : 'reject';

  return (
    <div className="card">
      <div className="card-header">
        <ShieldCheck className="card-icon" size={18} />
        <h3>Risk Assessment</h3>
      </div>

      {/* Recommendation badge + fraud probability */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
        <span className={`risk-badge ${badgeClass}`}>
          {recommendation === 'APPROVE' ? (
            <ShieldCheck size={14} />
          ) : (
            <AlertTriangle size={14} />
          )}
          {recommendation}
        </span>
        <div>
          <div className="metric-label">Manipulation Risk</div>
          <div
            className="data-text"
            style={{
              fontSize: '1.1rem',
              fontWeight: 700,
              color:
                manipulationProbability < 0.15
                  ? 'var(--accent)'
                  : manipulationProbability < 0.30
                  ? 'var(--warning)'
                  : 'var(--danger)',
            }}
          >
            {(manipulationProbability * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Consistency assessment */}
      <p
        style={{
          fontSize: '0.78rem',
          color: 'var(--text-secondary)',
          lineHeight: 1.6,
          marginBottom: 12,
        }}
      >
        {consistencyAssessment}
      </p>

      {/* Risk flags */}
      {riskFlags.length > 0 && (
        <div>
          <div
            className="metric-label"
            style={{ marginBottom: 6 }}
          >
            {riskFlags.length} Flag{riskFlags.length > 1 ? 's' : ''} Identified
          </div>
          {riskFlags.map((flag, idx) => (
            <div className="risk-flag-item" key={idx}>
              <span className={`risk-flag-severity ${flag.severity.toLowerCase()}`}>
                {flag.severity}
              </span>
              <div>
                <div
                  className="data-text"
                  style={{ fontSize: '0.72rem', color: 'var(--text-primary)', marginBottom: 3 }}
                >
                  {flag.flag_type.replace(/_/g, ' ')}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  {flag.evidence}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {riskFlags.length === 0 && (
        <div
          style={{
            fontSize: '0.78rem',
            color: 'var(--accent-dim)',
            fontStyle: 'italic',
          }}
        >
          No significant risk flags detected
        </div>
      )}
    </div>
  );
};

export default RiskAssessment;
