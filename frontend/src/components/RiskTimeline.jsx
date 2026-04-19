import React, { memo } from 'react'

const THRESHOLDS = [
  { label: 'HIGH', y: 80, color: '#f97316' },
  { label: 'MEDIUM', y: 60, color: '#f0b429' },
  { label: 'LOW', y: 35, color: '#00d084' },
]

const RiskTimeline = memo(({ history = [] }) => {
  const W = 460, H = 160, PAD = { l: 40, r: 10, t: 10, b: 20 }
  const gW = W - PAD.l - PAD.r
  const gH = H - PAD.t - PAD.b

  const toX = (i) => PAD.l + (i / Math.max(history.length - 1, 1)) * gW
  const toY = (v) => PAD.t + gH - (v / 100) * gH

  const points = history.map((v, i) => `${toX(i)},${toY(v)}`).join(' ')
  const area = history.length > 1
    ? `M ${toX(0)},${PAD.t + gH} L ${points} L ${toX(history.length - 1)},${PAD.t + gH} Z`
    : ''

  // Y-axis ticks
  const yTicks = [0, 20, 40, 60, 80, 100]

  return (
    <svg width="100%" viewBox={`0 0 ${W} ${H}`} style={{ overflow: 'visible' }}>
      {/* Grid lines */}
      {yTicks.map(t => (
        <line key={t}
          x1={PAD.l} y1={toY(t)} x2={W - PAD.r} y2={toY(t)}
          stroke="#1e1e2e" strokeWidth="1" />
      ))}
      {/* Y labels */}
      {yTicks.map(t => (
        <text key={t} x={PAD.l - 5} y={toY(t)}
          textAnchor="end" dominantBaseline="middle"
          fill="#4a4a6a" fontSize="9">{t}</text>
      ))}
      {/* Y axis label */}
      <text transform={`rotate(-90, 12, ${H/2})`} x="12" y={H/2}
        textAnchor="middle" fill="#4a4a6a" fontSize="9">Risk %</text>

      {/* Threshold lines */}
      {THRESHOLDS.map(({ label, y, color }) => (
        <g key={label}>
          <line x1={PAD.l} y1={toY(y)} x2={W - PAD.r} y2={toY(y)}
            stroke={color} strokeWidth="1" strokeDasharray="4 4" opacity="0.6" />
          <text x={W - PAD.r + 2} y={toY(y)} dominantBaseline="middle"
            fill={color} fontSize="8">{label}</text>
        </g>
      ))}

      {/* Area fill */}
      {area && (
        <path d={area} fill="#00d08418" />
      )}

      {/* Line */}
      {history.length > 1 && (
        <polyline points={points} fill="none" stroke="#00d084" strokeWidth="1.5" strokeLinejoin="round" />
      )}

      {/* Latest dot */}
      {history.length > 0 && (
        <circle cx={toX(history.length - 1)} cy={toY(history[history.length - 1])}
          r="3" fill="#00d084" />
      )}
    </svg>
  )
})

export default RiskTimeline
