import { useState, useRef, useId, useLayoutEffect, useEffect, useCallback } from 'react'
import { HelpCircle } from 'lucide-react'
import { GLOSSARY } from '../glossary'

/*
 * InfoTip — a quiet "?" that explains a GLOSSARY term in plain language.
 *
 * Positioning follows the existing Tooltip.jsx: position: fixed from the
 * trigger's getBoundingClientRect, which escapes the cards' overflow-hidden.
 * Added here: prefer above, flip below near the top edge, clamp horizontally
 * so it never overflows a 375px viewport, and reposition on scroll/resize.
 *
 * Interaction:
 *  - mouse: opens on hover, closes on leave (unless pinned by a click)
 *  - touch: tap opens (pinned), tap again / tap outside / Escape closes
 *  - keyboard: opens on focus-visible, Escape or blur closes
 *
 * Styling lives in shell.css (.fc-tip*). Uses <span>s only, so it is valid
 * inside <p>, <h2>, <dt> and label text.
 */

const GAP    = 8   // px between trigger and popover
const MARGIN = 8   // px kept clear of the viewport edge
const MAX_W  = 260

export default function InfoTip({ term, label }) {
  const entry   = GLOSSARY[term]
  const descId  = useId()
  const wrapRef = useRef(null)
  const btnRef  = useRef(null)
  const popRef  = useRef(null)

  const [open,   setOpen]   = useState(false)
  const [pinned, setPinned] = useState(false)
  const [pos,    setPos]    = useState(null) // { left, top, width, placement }

  const close = useCallback(() => { setOpen(false); setPinned(false) }, [])

  const place = useCallback(() => {
    const btn = btnRef.current
    const pop = popRef.current
    if (!btn) return
    const r      = btn.getBoundingClientRect()
    const vw     = window.innerWidth
    const width  = Math.min(MAX_W, vw - MARGIN * 2)
    const height = pop ? pop.offsetHeight : 0
    const centre = r.left + r.width / 2
    const left   = Math.min(Math.max(centre - width / 2, MARGIN), vw - width - MARGIN)
    const above  = r.top - GAP - height >= MARGIN
    const top    = above ? r.top - GAP - height : r.bottom + GAP
    setPos({ left, top, width, placement: above ? 'above' : 'below' })
  }, [])

  // Measure after the popover renders, then place it. Layout effects run
  // before paint, so it never shows at a stale position; on the very first
  // open it stays hidden until the first measurement lands.
  useLayoutEffect(() => {
    if (open) place()
  }, [open, place])

  useEffect(() => {
    if (!open) return
    function onPointerDown(e) {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) close()
    }
    function onKey(e) {
      if (e.key === 'Escape') { close(); btnRef.current?.focus() }
    }
    document.addEventListener('pointerdown', onPointerDown)
    document.addEventListener('keydown', onKey)
    window.addEventListener('scroll', place, true)
    window.addEventListener('resize', place)
    return () => {
      document.removeEventListener('pointerdown', onPointerDown)
      document.removeEventListener('keydown', onKey)
      window.removeEventListener('scroll', place, true)
      window.removeEventListener('resize', place)
    }
  }, [open, close, place])

  if (!entry) return null

  return (
    <span ref={wrapRef} className="fc-tip">
      <button
        ref={btnRef}
        type="button"
        className="fc-tip-btn"
        aria-label={entry.term}
        aria-describedby={descId}
        aria-expanded={open}
        onPointerEnter={e => { if (e.pointerType === 'mouse') setOpen(true) }}
        onPointerLeave={e => { if (e.pointerType === 'mouse' && !pinned) setOpen(false) }}
        onFocus={e => { if (e.currentTarget.matches(':focus-visible')) setOpen(true) }}
        onBlur={close}
        onClick={e => {
          e.stopPropagation() // e.g. inside a clickable row
          if (pinned) close()
          else { setOpen(true); setPinned(true) }
        }}
      >
        {label ?? <HelpCircle className="fc-tip-icon" aria-hidden="true" strokeWidth={2} />}
      </button>

      {/* Always in the DOM for screen readers; the visual popover is aria-hidden. */}
      <span id={descId} className="sr-only">{entry.short}</span>

      {open && (
        <span
          ref={popRef}
          className="fc-tip-pop"
          data-placement={pos?.placement}
          aria-hidden="true"
          style={{
            left:       pos?.left ?? 0,
            top:        pos?.top ?? 0,
            width:      pos?.width ?? MAX_W,
            visibility: pos ? 'visible' : 'hidden',
          }}
        >
          <span className="fc-tip-term">{entry.term}</span>
          <span className="fc-tip-body">{entry.short}</span>
        </span>
      )}
    </span>
  )
}
