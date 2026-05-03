import React from 'react';
import {
  CheckCircle,
  Loader,
  Camera,
  MapPin,
  Brain,
  BarChart3,
  ShieldCheck,
} from 'lucide-react';

interface Step {
  label: string;
  icon: React.ReactNode;
}

const STEPS: Step[] = [
  { label: 'Upload', icon: <Camera size={14} /> },
  { label: 'Vision AI', icon: <Brain size={14} /> },
  { label: 'Geo Intel', icon: <MapPin size={14} /> },
  { label: 'Economics', icon: <BarChart3 size={14} /> },
  { label: 'Risk', icon: <ShieldCheck size={14} /> },
];

interface ProgressBarProps {
  currentStep: number; // 0-indexed, -1 = not started
  isProcessing: boolean;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ currentStep, isProcessing }) => {
  return (
    <div className="progress-container">
      <div className="progress-steps">
        {STEPS.map((step, idx) => {
          const isCompleted = idx < currentStep;
          const isActive = idx === currentStep && isProcessing;

          return (
            <React.Fragment key={step.label}>
              <div
                className={`progress-step ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''}`}
              >
                <span className="step-dot" />
                {isActive ? <Loader size={12} className="spin" /> : step.icon}
                <span>{step.label}</span>
                {isCompleted && <CheckCircle size={12} />}
              </div>
              {idx < STEPS.length - 1 && (
                <div className={`progress-connector ${isCompleted ? 'completed' : ''}`} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};

export default ProgressBar;
