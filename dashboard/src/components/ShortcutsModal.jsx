import React from 'react'

export function ShortcutsModal({ isOpen, onClose }) {
  if (!isOpen) return null

  const shortcuts = [
    { key: '?', desc: 'Toggle this keyboard shortcuts dialog' },
    { key: 't', desc: 'Toggle Dark / Light theme mode' },
    { key: 'r', desc: 'Refresh runs list and status' },
    { key: 'Esc', desc: 'Close open modal or active drawer' },
  ]

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Keyboard Shortcuts"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--bg-panel, #121620)',
          border: '1px solid var(--border-color, #222938)',
          borderRadius: '12px',
          padding: '24px',
          width: '420px',
          maxWidth: '90vw',
          boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
          color: 'var(--text-primary, #e2e8f0)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>⌨️ Keyboard Shortcuts</h3>
          <button
            onClick={onClose}
            aria-label="Close shortcuts dialog"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted, #94a3b8)',
              fontSize: '18px',
              cursor: 'pointer',
            }}
          >
            ✕
          </button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {shortcuts.map((s) => (
            <div
              key={s.key}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '8px 12px',
                borderRadius: '6px',
                background: 'var(--bg-subtle, #1a202c)',
              }}
            >
              <span style={{ fontSize: '14px', color: 'var(--text-muted, #cbd5e1)' }}>{s.desc}</span>
              <kbd
                style={{
                  background: 'var(--bg-card, #2d3748)',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  border: '1px solid var(--border-color, #4a5568)',
                  color: '#60a5fa',
                  fontWeight: 600,
                }}
              >
                {s.key}
              </kbd>
            </div>
          ))}
        </div>

        <div style={{ marginTop: '20px', textAlign: 'right' }}>
          <button
            onClick={onClose}
            style={{
              padding: '6px 16px',
              borderRadius: '6px',
              background: '#3b82f6',
              color: '#fff',
              border: 'none',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  )
}
