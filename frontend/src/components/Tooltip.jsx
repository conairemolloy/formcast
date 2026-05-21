import { useState } from 'react'

export default function Tooltip({ text }) {
  const [pos, setPos] = useState(null)

  function show(e) {
    const r = e.currentTarget.getBoundingClientRect()
    setPos({ x: r.left + r.width / 2, y: r.top })
  }

  return (
    <span className="relative inline-flex items-center">
      <span
        className="inline-flex items-center justify-center w-4 h-4 rounded-full cursor-help ml-1 select-none text-[10px] font-bold"
        style={{ backgroundColor: '#1f2937', color: '#9ca3af' }}
        onMouseEnter={show}
        onMouseLeave={() => setPos(null)}
      >
        ?
      </span>
      {pos && (
        <div
          style={{
            position: 'fixed',
            left: pos.x,
            top: pos.y - 8,
            transform: 'translate(-50%, -100%)',
            zIndex: 9999,
            backgroundColor: '#000000',
            border: '1px solid #374151',
            borderRadius: '8px',
            padding: '8px 12px',
            maxWidth: '280px',
            fontSize: '12px',
            color: '#ffffff',
            lineHeight: '1.5',
            boxShadow: '0 4px 24px rgba(0,0,0,0.8)',
            pointerEvents: 'none',
            whiteSpace: 'normal',
          }}
        >
          {text}
        </div>
      )}
    </span>
  )
}
