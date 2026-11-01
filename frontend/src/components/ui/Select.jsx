import React, { forwardRef } from 'react';

const Select = forwardRef(function Select(
  {
    options = null, // array of { value, label } or children can be passed directly
    size = 'md',    // 'sm' | 'md'
    error = false,
    className = '',
    style = {},
    children,
    ...props
  },
  ref
) {
  const sizeClass = size === 'sm' ? 'revy-select-sm' : '';
  const errorClass = error ? 'revy-select-error' : '';
  const combinedClass = `revy-select ${sizeClass} ${errorClass} ${className}`.trim();

  return (
    <select ref={ref} className={combinedClass} style={style} {...props}>
      {options
        ? options.map(opt => (
            <option key={opt.value} value={opt.value} disabled={opt.disabled}>
              {opt.label}
            </option>
          ))
        : children}
    </select>
  );
});

export default Select;
