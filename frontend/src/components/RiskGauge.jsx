import React, { memo } from 'react'

const RISK_COLORS = {
  LOW: '#00d084',
  MEDIUM: '#f0b429',
  HIGH: '#f97316',
  CRITICAL: '#ef4444',
}

function polarToCartesian(cx, cy, r, angleDeg) {
  const rad = ((angleDeg - 90) * Math.PI) / 180
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
}

function arcPath(cx, cy, r, startAngle, endAngle) {
  const s = polarToCartesian(cx, cy, r, startAngle)
  const e = polarToCartesian(cx, cy, r, endAngle)
  const large = endAngle - startAngle > 180 ? 1 : 0
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`
}

const RiskGauge = memo(({ score = 0, level = 'LOW' }) => {
  const color = RISK_COLORS[level] || '#00d084'
  const cx = 100, cy = 90, r = 70
  const startAngle = -135
  const endAngle = 135
  const valueAngle = startAngle + (score / 100) * (endAngle - startAngle)
  const needle = polarToCartesian(cx, cy, 60, valueAngle)

  // Tick marks
  const ticks = [0, 20, 40, 60, 80, 100]

  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ fontSize: 10, letterSpacing: '0.1em', color: '#6a6a8a', marginBottom: 4 }}>GLOBAL RISK</div>
      <svg width="200" height="130" viewBox="0 0 200 130">
        {/* Background arc */}
        <path d={arcPath(cx, cy, r, startAngle, endAngle)}
          fill="none" stroke="#1e1e2e" strokeWidth="14" strokeLinecap="round" />

        {/* Colored zones */}
        <path d={arcPath(cx, cy, r, startAngle, startAngle + 0.35 * 270)}
          fill="none" stroke="#00d08444" strokeWidth="14" strokeLinecap="round" />
        <path d={arcPath(cx, cy, r, startAngle + 0.35 * 270, startAngle + 0.6 * 270)}
          fill="none" stroke="#f0b42944" strokeWidth="14" strokeLinecap="round" />
        <path d={arcPath(cx, cy, r, startAngle + 0.6 * 270, startAngle + 0.8 * 270)}
          fill="none" stroke="#f9731644" strokeWidth="14" strokeLinecap="round" />
        <path d={arcPath(cx, cy, r, startAngle + 0.8 * 270, endAngle)}
          fill="none" stroke="#ef444444" strokeWidth="14" strokeLinecap="round" />

        {/* Value arc */}
        <path d={arcPath(cx, cy, r, startAngle, valueAngle)}
          fill="none" stroke={color} strokeWidth="4" strokeLinecap="round" />

        {/* Tick labels */}
        {ticks.map(t => {
          const angle = startAngle + (t / 100) * (endAngle - startAngle)
          const lp = polarToCartesian(cx, cy, r + 16, angle)
          return (
            <text key={t} x={lp.x} y={lp.y}
              textAnchor="middle" dominantBaseline="middle"
              fill="#4a4a6a" fontSize="9">{t}</text>
          )
        })}

        {/* Needle */}
        <line x1={cx} y1={cy} x2={needle.x} y2={needle.y}
          stroke={color} strokeWidth="2" strokeLinecap="round" />
        <circle cx={cx} cy={cy} r="5" fill={color} />

        {/* Center text */}
        <text x={cx} y={cy + 20} textAnchor="middle" fill={color} fontSize="18" fontWeight="700">
          {score?.toFixed(1)}%
        </text>
        <text x={cx} y={cy + 36} textAnchor="middle" fill="#6a6a8a" fontSize="10">
          ▼ {(score).toFixed(1)}
        </text>
      </svg>
      <div style={{ fontSize: 10, color: '#6a6a8a', marginTop: -8 }}>GLOBAL RISK</div>
      <div style={{ fontSize: 11, color, fontWeight: 600 }}>{level}</div>
    </div>
  )
})

export default RiskGauge
