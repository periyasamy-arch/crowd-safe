import React, { memo } from 'react'

const ZoneRiskComparison = memo(({ cameras = {} }) => {
  const zones = Object.values(cameras)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {zones.map(cam => {
        const pct = cam.risk_score ?? 0
        const color = { LOW:'#00d084', MEDIUM:'#f0b429', HIGH:'#f97316', CRITICAL:'#ef4444' }[cam.risk_level] || '#00d084'
        return (
          <div key={cam.camera_id} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{ width: 70, textAlign: 'right', color: '#8a8aaa', fontSize: 11, flexShrink: 0 }}>
              {cam.zone || cam.name}
            </div>
            <div style={{ flex: 1, background: '#1a1a28', borderRadius: 3, height: 16, overflow: 'hidden' }}>
              <div style={{
                height: '100%', width: `${pct}%`,
                background: color, borderRadius: 3,
                transition: 'width 0.4s ease',
              }} />
            </div>
            <div style={{ width: 30, color, fontSize: 11, fontWeight: 600 }}>
              {pct.toFixed(0)}%
            </div>
          </div>
        )
      })}
    </div>
  )
})

export default ZoneRiskComparison
