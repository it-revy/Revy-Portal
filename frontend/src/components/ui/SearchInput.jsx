import React from 'react';
import { Search, X } from 'lucide-react';

export default function SearchInput({
  value = '',
  onChange,
  onSearch,
  onClear,
  placeholder = 'Search...',
  size = 'md', // 'sm' | 'md'
  className = '',
  style = {},
  autoFocus = false,
  disabled = false,
  ...props
}) {
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && onSearch) {
      e.preventDefault();
      onSearch(value);
    }
  };

  const handleClear = () => {
    if (onChange) {
      onChange({ target: { value: '' } });
    }
    if (onClear) {
      onClear();
    }
  };

  return (
    <div className={`revy-search-wrap ${className}`.trim()} style={style}>
      <Search size={size === 'sm' ? 14 : 16} className="revy-search-icon" />
      <input
        type="text"
        className={`revy-input revy-search-input ${size === 'sm' ? 'revy-input-sm' : ''}`}
        value={value}
        onChange={onChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        autoFocus={autoFocus}
        {...props}
      />
      {value && !disabled && (
        <button
          type="button"
          onClick={handleClear}
          className="revy-search-clear"
          title="Clear search"
          aria-label="Clear search query"
        >
          <X size={14} />
        </button>
      )}
    </div>
  );
}
