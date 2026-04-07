import React from 'react'

export default class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null } }
  static getDerivedStateFromError(error) { return { hasError: true, error } }
  componentDidCatch(error, info) { console.error('ErrorBoundary caught:', error, info) }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 48, maxWidth: 480, margin: '80px auto', textAlign: 'center' }}>
          <h2 style={{ fontFamily: 'var(--font-display)', marginBottom: 8 }}>Something went wrong</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 24 }}>{this.state.error?.message || 'An unexpected error occurred.'}</p>
          <button className="btn btn-primary" onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload() }}>Reload Application</button>
        </div>
      )
    }
    return this.props.children
  }
}
