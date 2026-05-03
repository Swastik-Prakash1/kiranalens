import React from 'react';
import { Shield, Cpu, Lock, Zap, FileCheck } from 'lucide-react';

const TrustBadges: React.FC = () => {
  const badges = [
    { icon: <Cpu size={14} />, label: 'YOLOv8 + COCO Inference' },
    { icon: <Shield size={14} />, label: 'Zero Data Sent to Cloud' },
    { icon: <Lock size={14} />, label: 'AES-256 Encrypted' },
    { icon: <Zap size={14} />, label: 'Real-time Processing' },
    { icon: <FileCheck size={14} />, label: 'Deterministic Logic' },
  ];

  return (
    <div className="trust-strip">
      {badges.map((badge, idx) => (
        <div className="trust-badge" key={idx}>
          <span className="trust-icon">{badge.icon}</span>
          <span>{badge.label}</span>
        </div>
      ))}
    </div>
  );
};

export default TrustBadges;
