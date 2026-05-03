// KiranaLens v4.0 — Production Fintech Dashboard
import { useState, useCallback } from 'react';
import {
  Scan,
  PlayCircle,
  RotateCcw,
  Sparkles,
} from 'lucide-react';

import ProgressBar from './components/ProgressBar';
import PhotoUpload from './components/PhotoUpload';
import AnnotatedImage from './components/AnnotatedImage';
import CategoryTable from './components/CategoryTable';
import VisionFeaturesCard from './components/VisionFeatures';
import GeoIntelligence from './components/GeoIntelligence';
import RevenueOutput from './components/RevenueOutput';
import RiskAssessment from './components/RiskAssessment';
import LoanRecommendationCard from './components/LoanRecommendation';
import TrustBadges from './components/TrustBadges';
import BusinessInsight from './components/BusinessInsight';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

function App() {
  // Form state
  const [shopName, setShopName] = useState('');
  const [lat, setLat] = useState('18.62');
  const [lng, setLng] = useState('73.74');
  const [years, setYears] = useState('5');
  const [images, setImages] = useState<File[]>([]);

  // Pipeline state
  const [isProcessing, setIsProcessing] = useState(false);
  const [currentStep, setCurrentStep] = useState(-1);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const resetAll = useCallback(() => {
    setResult(null);
    setError(null);
    setCurrentStep(-1);
    setIsProcessing(false);
  }, []);

  const runDemo = useCallback(async () => {
    setIsProcessing(true);
    setError(null);
    setResult(null);

    // Simulate progress
    const delays = [400, 600, 500, 600, 400];
    for (let i = 0; i < 5; i++) {
      setCurrentStep(i);
      await new Promise((r) => setTimeout(r, delays[i]));
    }

    try {
      const res = await fetch(`${API_BASE}/demo`);
      if (!res.ok) throw new Error(`Demo failed: ${res.status}`);
      const data = await res.json();
      setResult(data);
      setCurrentStep(5);
    } catch (err: any) {
      setError(err.message || 'Demo failed');
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const runAssessment = useCallback(async () => {
    if (images.length === 0) {
      setError('Please upload at least 1 shelf image');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setResult(null);

    const formData = new FormData();
    images.forEach((img) => formData.append('images', img));
    formData.append('lat', lat);
    formData.append('lng', lng);
    formData.append('shop_name', shopName || 'Store Assessment');
    formData.append('years_in_operation', years);

    // Animate progress
    setCurrentStep(0);
    const progressTimer = setInterval(() => {
      setCurrentStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 8000);

    try {
      const res = await fetch(`${API_BASE}/assess`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`Assessment failed: ${errBody}`);
      }
      const data = await res.json();
      setResult(data);
      setCurrentStep(5);
    } catch (err: any) {
      setError(err.message || 'Assessment failed');
    } finally {
      clearInterval(progressTimer);
      setIsProcessing(false);
    }
  }, [images, lat, lng, shopName, years]);

  // ── Render Landing Page (no results yet) ────────────────────────────
  if (!result) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        {/* Header */}
        <header className="app-header">
          <div className="app-logo">
            <Scan size={24} style={{ color: 'var(--accent)' }} />
            <h1>KiranaLens</h1>
            <span className="version-badge">v4.0</span>
          </div>
          <div className="app-header-actions">
            <button className="btn-secondary" onClick={runDemo} disabled={isProcessing}>
              <Sparkles size={14} style={{ marginRight: 6 }} />
              Live Demo
            </button>
          </div>
        </header>

        {/* Progress bar (visible during processing) */}
        {isProcessing && <ProgressBar currentStep={currentStep} isProcessing={isProcessing} />}

        {/* Landing content */}
        <div className="landing-container">
          <div className="landing-hero">
            <h2>Visual Credit Bureau for India's Kirana Economy</h2>
            <p>
              Upload shelf photos + GPS coordinates. KiranaLens uses dual-model YOLO inference
              to estimate revenue, detect fraud, and generate instant loan recommendations.
              Zero cloud dependency. 100% local inference.
            </p>
          </div>

          <div className="landing-form card">
            <div className="form-row">
              <div className="form-group full-width">
                <label className="form-label">Shop Name</label>
                <input
                  className="form-input"
                  type="text"
                  placeholder="e.g., Sharma General Store"
                  value={shopName}
                  onChange={(e) => setShopName(e.target.value)}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group">
                <label className="form-label">Latitude</label>
                <input
                  className="form-input"
                  type="number"
                  step="0.01"
                  placeholder="18.62"
                  value={lat}
                  onChange={(e) => setLat(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="form-label">Longitude</label>
                <input
                  className="form-input"
                  type="number"
                  step="0.01"
                  placeholder="73.74"
                  value={lng}
                  onChange={(e) => setLng(e.target.value)}
                />
              </div>
            </div>

            <div className="form-row">
              <div className="form-group full-width">
                <label className="form-label">Years in Operation</label>
                <input
                  className="form-input"
                  type="number"
                  min="0"
                  max="50"
                  value={years}
                  onChange={(e) => setYears(e.target.value)}
                />
              </div>
            </div>

            <div style={{ marginTop: 16 }}>
              <PhotoUpload images={images} setImages={setImages} />
            </div>

            {error && (
              <div
                style={{
                  color: 'var(--danger)',
                  fontSize: '0.8rem',
                  marginTop: 12,
                  padding: '8px 12px',
                  background: 'rgba(255, 77, 106, 0.08)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid rgba(255, 77, 106, 0.2)',
                }}
              >
                {error}
              </div>
            )}

            <div style={{ marginTop: 20, display: 'flex', gap: 12 }}>
              <button
                className="btn-primary"
                onClick={runAssessment}
                disabled={isProcessing}
                style={{ flex: 1 }}
              >
                <PlayCircle size={16} style={{ marginRight: 8, verticalAlign: 'text-bottom' }} />
                {isProcessing ? 'Processing...' : 'Run Assessment'}
              </button>
              <button
                className="btn-secondary"
                onClick={runDemo}
                disabled={isProcessing}
              >
                <Sparkles size={14} style={{ marginRight: 6 }} />
                Demo
              </button>
            </div>
          </div>
        </div>

        <TrustBadges />
      </div>
    );
  }

  // ── Render Results Dashboard ─────────────────────────────────────────
  const v = result.vision_features;
  const g = result.geo_features;
  const e = result.economic_estimate;
  const f = result.fraud_analysis;
  const l = result.loan_recommendation;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Header */}
      <header className="app-header">
        <div className="app-logo">
          <Scan size={24} style={{ color: 'var(--accent)' }} />
          <h1>KiranaLens</h1>
          <span className="version-badge">v4.0</span>
        </div>
        <div className="app-header-actions">
          <span
            className="data-text"
            style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}
          >
            {result.assessment_id}
          </span>
          <button className="btn-secondary" onClick={resetAll}>
            <RotateCcw size={14} style={{ marginRight: 6 }} />
            New Assessment
          </button>
        </div>
      </header>

      {/* Progress bar - completed */}
      <ProgressBar currentStep={5} isProcessing={false} />

      {/* 3-Column Dashboard */}
      <div className="dashboard-grid">
        {/* ── Column 1: Input & Geo ────────────────────────────────── */}
        <div className="column column-scroll">
          <div className="column-title">Input & Location</div>

          {/* Store info card */}
          <div className="card">
            <div className="card-header">
              <Scan className="card-icon" size={18} />
              <h3>Store Profile</h3>
            </div>
            <div className="metrics-grid metrics-grid-2">
              <div className="metric-card">
                <div className="metric-label">Store Name</div>
                <div className="metric-value" style={{ fontSize: '0.9rem' }}>
                  {result.inputs?.shop_name || 'N/A'}
                </div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Store Size</div>
                <div className="metric-value" style={{ fontSize: '0.9rem' }}>
                  {v.store_size_proxy}
                </div>
                <div className="metric-sub">{v.estimated_floor_area_sqft} sqft</div>
              </div>
            </div>
          </div>

          {/* Geo Intelligence */}
          <GeoIntelligence
            lat={g.lat}
            lng={g.lng}
            cityTier={g.city_tier}
            indiaRegion={g.india_region}
            roadType={g.road_type}
            footfallProxy={g.footfall_proxy_index}
            competitionCount={g.competition_count_500m}
            amenityScore={g.amenity_score}
            geoMultiplier={g.geo_multiplier}
          />

          {/* Annotated Image */}
          <div className="card">
            <div className="card-header">
              <h3>Shelf Detection</h3>
            </div>
            <AnnotatedImage imageB64={v.annotated_image_b64} />
          </div>
        </div>

        {/* ── Column 2: AI Vision Analysis ─────────────────────────── */}
        <div className="column column-scroll">
          <div className="column-title">AI Vision Analysis</div>

          {/* Vision Features */}
          <VisionFeaturesCard
            sdi={v.sdi}
            sdiConfidence={v.sdi_confidence}
            skuDiversityScore={v.sku_diversity_score}
            skuDiversityLabel={v.sku_diversity_label}
            inventoryDensityScore={v.inventory_density_score}
            refillSignal={v.refill_signal}
            totalProducts={v.total_products_detected}
            detectionMethod={v.detection_method}
            cocoDetectionsUsed={v.coco_detections_used}
          />

          {/* Category Breakdown */}
          <CategoryTable categoryCounts={v.category_counts} />

          {/* Business Insight */}
          <BusinessInsight insight={v.business_insight} />

          {/* Inventory Value */}
          <div className="card">
            <div className="metrics-grid metrics-grid-2">
              <div className="metric-card">
                <div className="metric-label">Estimated Inventory</div>
                <div className="metric-value accent">
                  Rs.{(v.estimated_inventory_value_inr || 0).toLocaleString('en-IN')}
                </div>
                <div className="metric-sub">{v.inventory_value_band} band</div>
              </div>
              <div className="metric-card">
                <div className="metric-label">Vision Multiplier</div>
                <div className="metric-value">{v.vision_multiplier}x</div>
                <div className="metric-sub">
                  {v.processing_notes?.length || 0} images processed
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── Column 3: KiranaLens Output ──────────────────────────── */}
        <div className="column column-scroll">
          <div className="column-title">KiranaLens Output</div>

          {/* Revenue Estimate */}
          <RevenueOutput
            dailyLow={e.daily_sales_low}
            dailyMid={e.daily_sales_mid}
            dailyHigh={e.daily_sales_high}
            monthlyLow={e.monthly_revenue_low}
            monthlyMid={e.monthly_revenue_mid}
            monthlyHigh={e.monthly_revenue_high}
            incomeLow={e.monthly_income_low}
            incomeMid={e.monthly_income_mid}
            incomeHigh={e.monthly_income_high}
            confidence={e.confidence_score}
            combinedMultiplier={e.combined_multiplier}
          />

          {/* Risk Assessment */}
          <RiskAssessment
            manipulationProbability={f.manipulation_probability}
            recommendation={f.recommendation}
            riskFlags={f.risk_flags}
            consistencyAssessment={f.consistency_assessment}
          />

          {/* Loan Recommendation */}
          <LoanRecommendationCard
            recommendation={l.recommendation}
            recommendationLabel={l.recommendation_label}
            loanLow={l.eligible_loan_low}
            loanHigh={l.eligible_loan_high}
            tenureLow={l.recommended_tenure_months_low}
            tenureHigh={l.recommended_tenure_months_high}
            emiLow={l.emi_range_low}
            emiHigh={l.emi_range_high}
          />

          {/* Processing Time */}
          <div
            className="card"
            style={{
              textAlign: 'center',
              fontSize: '0.72rem',
              color: 'var(--text-muted)',
              padding: '14px',
            }}
          >
            <span className="data-text">
              Processed in {result.processing_time_seconds?.toFixed(1)}s | {result.model_version}
            </span>
          </div>
        </div>
      </div>

      <TrustBadges />
    </div>
  );
}

export default App;
