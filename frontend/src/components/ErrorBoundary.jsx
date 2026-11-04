import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
      remountKey: 0
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    // Log error to console for debugging
    console.error('REVY Application ErrorBoundary caught an exception:', error, errorInfo);
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  componentDidUpdate(prevProps) {
    if (this.props.resetKey !== undefined && prevProps.resetKey !== this.props.resetKey) {
      if (this.state.hasError) {
        this.setState(prevState => ({
          hasError: false,
          error: null,
          errorInfo: null,
          showDetails: false,
          remountKey: prevState.remountKey + 1
        }));
      }
    }
  }

  handleReset = () => {
    this.setState(prevState => ({
      hasError: false,
      error: null,
      errorInfo: null,
      showDetails: false,
      remountKey: prevState.remountKey + 1
    }));
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return typeof this.props.fallback === 'function'
          ? this.props.fallback({ error: this.state.error, reset: this.handleReset })
          : this.props.fallback;
      }

      const isGlobal = this.props.level === 'global';

      return (
        <div
          role="alert"
          style={{
            minHeight: isGlobal ? '100vh' : '400px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 'var(--space-6, 24px)',
            background: isGlobal ? 'var(--color-bg-subtle, #f8fafc)' : 'transparent',
            fontFamily: 'var(--font-sans, system-ui, sans-serif)'
          }}
        >
          <div
            style={{
              maxWidth: '560px',
              width: '100%',
              background: '#ffffff',
              border: '1px solid var(--color-border, #e2e8f0)',
              borderRadius: 'var(--radius-lg, 12px)',
              boxShadow: 'var(--shadow-lg, 0 10px 15px -3px rgba(0,0,0,0.1))',
              padding: 'var(--space-6, 24px)',
              textAlign: 'center'
            }}
          >
            <div
              style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                background: 'rgba(239, 68, 68, 0.1)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 'var(--space-4, 16px)'
              }}
            >
              <AlertTriangle size={28} color="#ef4444" />
            </div>

            <h2
              style={{
                fontSize: '1.25rem',
                fontWeight: 700,
                color: 'var(--color-text-primary, #0f172a)',
                margin: '0 0 var(--space-2, 8px) 0'
              }}
            >
              {this.props.title || 'An unexpected error occurred'}
            </h2>

            <p
              style={{
                fontSize: '0.9rem',
                color: 'var(--color-text-secondary, #64748b)',
                lineHeight: 1.5,
                margin: '0 0 var(--space-5, 20px) 0'
              }}
            >
              {this.props.message ||
                'This section of the portal encountered an unexpected issue. You can try refreshing the view or returning to the portal dashboard.'}
            </p>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-3, 12px)',
                flexWrap: 'wrap',
                marginBottom: 'var(--space-4, 16px)'
              }}
            >
              <button
                type="button"
                onClick={this.handleReset}
                className="revy-btn revy-btn-primary"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  borderRadius: 'var(--radius-md, 6px)',
                  cursor: 'pointer'
                }}
              >
                <RefreshCw size={14} />
                Try Again
              </button>

              <a
                href="/portal"
                className="revy-btn revy-btn-secondary"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  borderRadius: 'var(--radius-md, 6px)',
                  textDecoration: 'none',
                  cursor: 'pointer'
                }}
              >
                <Home size={14} />
                Return to Portal
              </a>
            </div>

            {/* Collapsible diagnostic details for developers */}
            {this.state.error && (
              <div style={{ marginTop: 'var(--space-4, 16px)', textAlign: 'left' }}>
                <button
                  type="button"
                  onClick={() => this.setState({ showDetails: !this.state.showDetails })}
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: 0,
                    color: 'var(--color-text-muted, #94a3b8)',
                    fontSize: '0.75rem',
                    cursor: 'pointer',
                    textDecoration: 'underline'
                  }}
                >
                  {this.state.showDetails ? 'Hide diagnostic details' : 'Show diagnostic details'}
                </button>

                {this.state.showDetails && (
                  <pre
                    style={{
                      marginTop: '8px',
                      padding: '12px',
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      borderRadius: '6px',
                      fontSize: '0.75rem',
                      color: '#dc2626',
                      overflowX: 'auto',
                      whiteSpace: 'pre-wrap',
                      maxHeight: '160px'
                    }}
                  >
                    {this.state.error.toString() + (this.state.error.stack ? '\n\n' + this.state.error.stack : '') + (this.state.errorInfo?.componentStack ? '\n\nComponent Stack:' + this.state.errorInfo.componentStack : '')}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>
      );
    }

    return <React.Fragment key={this.state.remountKey}>{this.props.children}</React.Fragment>;
  }
}

export default ErrorBoundary;
