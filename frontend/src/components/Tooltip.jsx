import { useState } from 'react'

export default function Tooltip({ text }) {
  const [visible, setVisible] = useState(false)

  return (
    <span className="relative inline-flex items-center">
      <span
        className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-gray-800 text-gray-500 text-[9px] font-bold cursor-help ml-1 hover:bg-gray-700 hover:text-gray-300 transition-colors select-none"
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
      >
        ?
      </span>
      {visible && (
        <div
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 rounded-lg px-3 py-2 text-xs text-gray-300 leading-relaxed shadow-xl pointer-events-none"
          style={{
            width: 'max-content',
            maxWidth: '250px',
            backgroundColor: '#111827',
            border: '1px solid #374151',
          }}
        >
          {text}
          <span
            className="absolute top-full left-1/2 -translate-x-1/2 block w-0 h-0"
            style={{
              borderLeft: '5px solid transparent',
              borderRight: '5px solid transparent',
              borderTop: '5px solid #374151',
            }}
          />
        </div>
      )}
    </span>
  )
}
