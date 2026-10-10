/**
 * Centralized, authoritative date & timestamp formatting utilities for REVY BMS.
 * All user-facing BMS timestamps must be represented in Asia/Kolkata (IST).
 */

export function parseAsUTC(value) {
  if (!value) return null;
  if (value instanceof Date) return value;
  if (typeof value !== 'string') return new Date(value);

  const trimmed = value.trim();
  if (!trimmed) return null;

  // If ISO string without explicit timezone offset (no Z and no +/- offset),
  // treat as UTC instant as per server convention.
  if (trimmed.includes('T') && !trimmed.endsWith('Z') && !/[+-]\d{2}(:\d{2})?$/.test(trimmed)) {
    return new Date(`${trimmed}Z`);
  }

  return new Date(trimmed);
}

/**
 * Formats any ISO/UTC timestamp or Date into consistent Asia/Kolkata (IST) display:
 * Example output: "09 Oct 2026, 04:30:00 PM"
 */
export function formatISTTimestamp(value, includeSeconds = true) {
  if (!value) return '—';

  const date = parseAsUTC(value);

  if (!date || Number.isNaN(date.getTime())) {
    return '—';
  }

  const options = {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  };

  if (includeSeconds) {
    options.second = '2-digit';
  }

  return new Intl.DateTimeFormat('en-IN', options).format(date);
}

/**
 * Formats timestamp to time-only in Asia/Kolkata (IST):
 * Example output: "04:30 PM"
 */
export function formatISTTime(value) {
  if (!value) return '—';

  const date = parseAsUTC(value);

  if (!date || Number.isNaN(date.getTime())) {
    return '—';
  }

  return new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata',
    hour: '2-digit',
    minute: '2-digit',
    hour12: true
  }).format(date);
}

/**
 * Formats date into "09 Oct 2026" in Asia/Kolkata (IST).
 */
export function formatISTDate(value) {
  if (!value) return '—';

  const date = parseAsUTC(value);

  if (!date || Number.isNaN(date.getTime())) {
    return '—';
  }

  return new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: 'short',
    year: 'numeric'
  }).format(date);
}
