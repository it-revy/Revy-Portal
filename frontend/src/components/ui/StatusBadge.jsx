import React from 'react';
import { CheckCircle2, XCircle, Info, Clock } from 'lucide-react';

export default function StatusBadge({
  status = '',
  variant = null, // 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'primary'
  label = null,
  showIcon = false,
  className = '',
  style = {}
}) {
  const text = label || status;
  const normalized = String(status || '').toUpperCase();

  let resolvedVariant = variant;
  let ResolvedIcon = null;

  if (!resolvedVariant) {
    if (['ACTIVE', 'WON', 'CLOSED WON', 'QUALIFIED', 'APPROVED', 'PROVIDED', 'SUCCESS', 'NORMAL'].includes(normalized)) {
      resolvedVariant = 'success';
      ResolvedIcon = CheckCircle2;
    } else if (['PENDING', 'DORMANT', 'NEGOTIATION', 'PROPOSE', 'PROPOSE/OFFER', 'DEVELOP', 'ENQUIRY', 'OFFER', 'WARNING'].includes(normalized)) {
      resolvedVariant = 'warning';
      ResolvedIcon = Clock;
    } else if (['INACTIVE', 'LOST', 'CLOSED LOST', 'DISQUALIFIED', 'REJECTED', 'DANGER', 'PERMANENT_NON_TAKER'].includes(normalized)) {
      resolvedVariant = 'danger';
      ResolvedIcon = XCircle;
    } else if (['OPEN', 'OPEN PIPELINE', 'INFO', 'DAILY_ENTRY', 'ADDITIONAL_ORDER'].includes(normalized)) {
      resolvedVariant = 'info';
      ResolvedIcon = Info;
    } else {
      resolvedVariant = 'neutral';
    }
  }

  return (
    <span
      className={`revy-badge revy-badge-${resolvedVariant} ${className}`.trim()}
      style={style}
    >
      {showIcon && ResolvedIcon && <ResolvedIcon size={12} />}
      {text}
    </span>
  );
}
