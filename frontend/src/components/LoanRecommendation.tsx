import React from 'react';
import { Landmark, Calendar, CreditCard } from 'lucide-react';

interface LoanRecommendationProps {
  recommendation: string;
  recommendationLabel: string;
  loanLow: number;
  loanHigh: number;
  tenureLow: number;
  tenureHigh: number;
  emiLow: number;
  emiHigh: number;
}

function formatINR(n: number): string {
  if (n >= 100000) return `${(n / 100000).toFixed(1)}L`;
  if (n >= 1000) return `${(n / 1000).toFixed(0)}K`;
  return n.toLocaleString('en-IN');
}

const LoanRecommendationCard: React.FC<LoanRecommendationProps> = ({
  recommendation,
  recommendationLabel,
  loanLow,
  loanHigh,
  tenureLow,
  tenureHigh,
  emiLow,
  emiHigh,
}) => {
  const isApproved = recommendation === 'PRE_APPROVE';
  const isReject = recommendation === 'REJECT';

  return (
    <div className="card">
      <div className="card-header">
        <Landmark className="card-icon" size={18} />
        <h3>Loan Recommendation</h3>
      </div>

      {/* Hero */}
      <div className="loan-hero">
        <span
          className={`risk-badge ${isApproved ? 'approve' : isReject ? 'reject' : 'verify'}`}
          style={{ marginBottom: 12 }}
        >
          {recommendationLabel}
        </span>

        {!isReject && (
          <>
            <div className="loan-amount" style={{ marginTop: 16 }}>
              Rs.{formatINR(loanLow)} - Rs.{formatINR(loanHigh)}
            </div>
            <div className="loan-amount-range">Eligible Loan Amount</div>
          </>
        )}

        {isReject && (
          <div
            style={{
              marginTop: 16,
              color: 'var(--danger)',
              fontSize: '0.85rem',
            }}
          >
            Application does not meet lending criteria
          </div>
        )}
      </div>

      {/* Tenure + EMI */}
      {!isReject && (
        <div className="metrics-grid metrics-grid-2">
          <div className="metric-card">
            <div className="metric-label">
              <Calendar size={10} style={{ marginRight: 3 }} />
              Tenure
            </div>
            <div className="metric-value" style={{ fontSize: '1.1rem' }}>
              {tenureLow}-{tenureHigh}
            </div>
            <div className="metric-sub">months</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">
              <CreditCard size={10} style={{ marginRight: 3 }} />
              Est. EMI
            </div>
            <div className="metric-value accent" style={{ fontSize: '1.1rem' }}>
              Rs.{formatINR(emiLow)}-{formatINR(emiHigh)}
            </div>
            <div className="metric-sub">per month</div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LoanRecommendationCard;
