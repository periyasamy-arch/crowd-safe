import React, { memo, useEffect, useRef } from 'react'

const CameraFeed = memo(({ camera }) => {
  if (!camera) return null

  const imgRef = useRef(null)

  const {
    camera_id, name, person_count,
    density, direction_entropy,
    risk_score, risk_level, density_class,
  } = camera

  // ── Receive frames via DOM event — zero React re-renders ──
  useEffect(() => {
    const handler = (e) => {
      const cam = e.detail?.[camera_id]
      if (cam?.frame_b64 && imgRef.current) {
        imgRef.current.src = `data:image/jpeg;base64,${cam.frame_b64}`
      }
    }
    window.addEventListener('crowd-frames', handler)
    return () => window.removeEventListener('crowd-frames', handler)
  }, [camera_id])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span className={`dot dot-${risk_level}`} />
          <span style={{ fontWeight: 600, fontSize: 12 }}>{name}</span>
        </div>
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <span className={`cnn-badge cnn-${density_class}`}>CNN:{density_class}</span>
          <span className={`badge badge-${risk_level}`}>
            {risk_level} {risk_score?.toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Frame — updated via DOM ref, not React state */}
      <div style={{
        background: '#000', borderRadius: 6, overflow: 'hidden',
        aspectRatio: '16/9', border: '1px solid #2a2a3a',
      }}>
        <img
          ref={imgRef}
          alt={name}
          style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
        />
      </div>

      {/* HIGH density warning */}
      {density_class === 'HIGH' && (
        <div style={{
          fontSize: 10, color: '#ef4444', background: '#ef444411',
          border: '1px solid #ef444433', borderRadius: 4, padding: '3px 8px',
        }}>
          ⚠ HIGH DENSITY — YOLO skipped, MAX_DENSITY assigned
        </div>
      )}

      {/* Metrics */}
      <div style={{ display: 'flex', justifyContent: 'space-between', color: '#6a6a8a', fontSize: 11 }}>
        <span>👥 {person_count} detected</span>
        <span>Density {density?.toFixed(0)}%</span>
        <span>Entropy {direction_entropy?.toFixed(0)}%</span>
      </div>

    </div>
  )
})

export default CameraFeed