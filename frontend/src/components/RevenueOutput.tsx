import React from 'react';
import { IndianRupee, TrendingUp } from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

interface RevenueOutputProps {
  dailyLow: number;
  dailyMid: number;
  dailyHigh: number;
  monthlyLow: number;
  monthlyMid: number;
  monthlyHigh: number;
  incomeLow: number;
  incomeMid: number;
  incomeHigh: number;
  confidence: number;
  combinedMultiplier: number;
}

function formatINR(n: number): string {
  if (n >= 100000) return `${(n / 100000).toFixed(1)}L`;
  if (n >= 1000) return `${(n / 1000).toFixed(0)}K`;
  return n.toLocaleString('en-IN');
}

function generateBellCurve(low: number, mid: number, high: number) {
  const points = [];
  const range = high - low;
  const steps = 30;
  for (let i = 0; i <= steps; i++) {
    const x = low + (range * i) / steps;
    const z = (x - mid) / (range / 4);
    const y = Math.exp(-0.5 * z * z);
    points.push({
      revenue: Math.round(x),
      probability: Math.round(y * 100),
      label: formatINR(Math.round(x)),
    });
  }
  return points;
}

const RevenueOutput: React.FC<RevenueOutputProps> = ({
  dailyLow,
  dailyMid,
  dailyHigh,
  monthlyLow,
  monthlyMid,
  monthlyHigh,
  incomeLow,
  incomeMid,
  incomeHigh,
  confidence,
  combinedMultiplier,
}) => {
  const chartData = generateBellCurve(monthlyLow, monthlyMid, monthlyHigh);

  return (
    <div className="card">
      <div className="card-header">
        <IndianRupee className="card-icon" size={18} />
        <h3>Revenue Estimate</h3>
        <span
          className="data-text"
          style={{
            marginLeft: 'auto',
            fontSize: '0.65rem',
            color: 'var(--accent)',
          }}
        >
          {combinedMultiplier.toFixed(2)}x multiplier
        </span>
      </div>

      {/* Revenue range header */}
      <div className="revenue-range">
        <div>
          <div className="revenue-label">Monthly Low</div>
          <div className="revenue-value" style={{ color: 'var(--text-secondary)' }}>
            Rs.{formatINR(monthlyLow)}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div className="revenue-label">Monthly Mid</div>
          <div className="revenue-value" style={{ color: 'var(--accent)', fontSize: '1.4rem' }}>
            Rs.{formatINR(monthlyMid)}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="revenue-label">Monthly High</div>
          <div className="revenue-value" style={{ color: 'var(--text-secondary)' }}>
            Rs.{formatINR(monthlyHigh)}
          </div>
        </div>
      </div>

      {/* Bell curve chart */}
      <div style={{ height: 140, marginBottom: 16, minWidth: 200 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00D4AA" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#00D4AA" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="label"
              tick={{ fontSize: 9, fill: '#5A6578', fontFamily: 'IBM Plex Mono' }}
              axisLine={{ stroke: '#1E293B' }}
              tickLine={false}
              interval={Math.floor(chartData.length / 5)}
            />
            <YAxis hide />
            <Tooltip
              contentStyle={{
                background: '#111827',
                border: '1px solid #1E293B',
                borderRadius: '8px',
                fontSize: '0.75rem',
                fontFamily: 'IBM Plex Mono',
                color: '#E8ECF1',
              }}
              formatter={(value: any) => [`${value}%`, 'Probability']}
              labelFormatter={(label) => `Revenue: Rs.${label}`}
            />
            <Area
              type="monotone"
              dataKey="probability"
              stroke="#00D4AA"
              strokeWidth={2}
              fill="url(#revGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Daily + Income metrics */}
      <div className="metrics-grid metrics-grid-3">
        <div className="metric-card">
          <div className="metric-label">Daily Revenue</div>
          <div className="metric-value" style={{ fontSize: '1rem' }}>Rs.{formatINR(dailyMid)}</div>
          <div className="metric-sub">Rs.{formatINR(dailyLow)} - {formatINR(dailyHigh)}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">
            <TrendingUp size={10} style={{ marginRight: 3 }} />
            Monthly Income
          </div>
          <div className="metric-value accent" style={{ fontSize: '1rem' }}>Rs.{formatINR(incomeMid)}</div>
          <div className="metric-sub">Rs.{formatINR(incomeLow)} - {formatINR(incomeHigh)}</div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Confidence</div>
          <div className="metric-value" style={{ fontSize: '1rem' }}>{(confidence * 100).toFixed(0)}%</div>
          <div className="confidence-bar" style={{ marginTop: 6 }}>
            <div className="confidence-fill" style={{ width: `${confidence * 100}%` }} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default RevenueOutput;
