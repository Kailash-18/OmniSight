import { useState } from 'react'
import { clampPercent } from '../lifecycle.js'

// Drag (or use the arrow keys on) the handle to reveal the "after" screenshot over the "before" one.
export default function CompareSlider({ before, after, label }) {
  const [pos, setPos] = useState(50)
  return (
    <div className="compare viewfinder" data-testid="compare-slider">
      <img src={before} alt={`Before the fix: ${label}`} className="compare-img" />
      <div className="compare-after" style={{ clipPath: `inset(0 0 0 ${pos}%)` }}>
        <img src={after} alt={`After the fix: ${label}`} className="compare-img" />
      </div>
      <span className="compare-tag before">Before</span>
      <span className="compare-tag after">After</span>
      <input type="range" min="0" max="100" value={pos} onChange={(e) => setPos(clampPercent(Number(e.target.value)))}
        className="compare-range" aria-label={`Compare before and after for ${label}`} data-testid="compare-range" />
      <span className="compare-handle" style={{ left: `${pos}%` }} aria-hidden="true" />
    </div>
  )
}
