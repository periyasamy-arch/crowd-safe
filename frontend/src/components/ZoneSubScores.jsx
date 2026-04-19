import React, { memo } from 'react'

const COLORS = ['#00d084', '#06b6d4', '#a855f7', '#f0b429']

const ZoneSubScores = memo(({ cameras = {} }) => {
  const zones = Object.values(cameras)
  const metrics = ['density', 'speed_variance', 'direction_entropy']
  const labels = ['Density', 'Speed Var.', 'Direction Entropy']

  const W = 100 / Math.max(metrics.length, 1)

  return (
    <div>
      {/* Grouped bar chart */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 24, height: 140, padding: '0 10px' }}>
        {metrics.map((m, mi) => (
          <div key={m} style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 3, height: 120 }}>
              {zones.map((cam, ci) => {
                const val = cam[m] ?? 0
                return (
                  <div key={cam.camera_id} style={{
                    flex: 1,
                    height: `${Math.max(val, 2)}%`,
                    background: COLORS[ci % COLORS.length],
                    borderRadius: '2px 2px 0 0',
                    opacity: 0.8,
                    transition: 'height 0.3s ease',
                  }} />
                )
              })}
            </div>
            <div style={{ fontSize: 9, color: '#6a6a8a', textAlign: 'center' }}>{labels[mi]}</div>
          </div>
        ))}
      </div>

      {/* Y ticks overlay */}
      <div style={{ display: 'flex', justifyContent: 'space-between', color: '#4a4a6a', fontSize: 9, padding: '2px 10px' }}>
        <span>0%</span><span>50%</span><span>100%</span>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 12, marginTop: 8, flexWrap: 'wrap' }}>
        {zones.map((cam, ci) => (
          <div key={cam.camera_id} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: '#8a8aaa' }}>
            <div style={{ width: 10, height: 10, background: COLORS[ci % COLORS.length], borderRadius: 2 }} />
            {cam.zone || cam.name}
          </div>
        ))}
      </div>
    </div>
  )
})

export default ZoneSubScores
