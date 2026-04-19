import React, { useState, useEffect, useRef } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import CameraFeed from './components/CameraFeed'
import RiskGauge from './components/RiskGauge'
import RiskTimeline from './components/RiskTimeline'
import ZoneRiskComparison from './components/ZoneRiskComparison'
import EvacuationNetwork from './components/EvacuationNetwork'
import ZoneSubScores from './components/ZoneSubScores'

function Clock() {
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return (
    <div style={{ textAlign: 'right' }}>
      <div style={{ fontSize: 10, color: '#6a6a8a', letterSpacing: '0.1em' }}>LOCAL TIME</div>
      <div style={{ fontSize: 22, fontWeight: 700, fontVariantNumeric: 'tabular-nums', letterSpacing: '0.05em' }}>
        {time.toLocaleTimeString()}
      </div>
      <div style={{ fontSize: 10, color: '#6a6a8a' }}>⟳ Live</div>
    </div>
  )
}

function MonitoringPanel({ level, score }) {
  const colors = { LOW: '#00d084', MEDIUM: '#f0b429', HIGH: '#f97316', CRITICAL: '#ef4444' }
  const icons = { LOW: '●', MEDIUM: '⚠', HIGH: '🔴', CRITICAL: '🚨' }
  const labels = { LOW: 'MONITORING', MEDIUM: 'WARNING', HIGH: 'ALERT', CRITICAL: 'CRITICAL' }
  const color = colors[level] || '#00d084'

  return (
    <div style={{
      background: `${color}11`, border: `1px solid ${color}44`,
      borderRadius: 8, padding: '16px', textAlign: 'center', marginTop: 10,
    }}>
      <div style={{ fontSize: 24, marginBottom: 6 }}>{icons[level]}</div>
      <div style={{ fontSize: 14, fontWeight: 700, color, letterSpacing: '0.1em' }}>
        {labels[level]}
      </div>
      <div style={{ fontSize: 11, color: '#6a6a8a', marginTop: 4 }}>Risk Level: {level}</div>
    </div>
  )
}

function AlertPanel({ alerts = [], level = 'LOW' }) {
  const alert = alerts[0]
  if (!alert) return null
  const colors = { LOW: '#00d084', MEDIUM: '#f0b429', HIGH: '#f97316', CRITICAL: '#ef4444' }
  const color = colors[level] || '#00d084'

  return (
    <div style={{
      background: '#111118',
      border: `1px solid ${color}44`,
      borderLeft: `3px solid ${color}`,
      borderRadius: 6,
      padding: '10px 12px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <span style={{ fontSize: 10 }}>⚠</span>
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: '#6a6a8a' }}>ALERT PANEL</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
        <span className={`dot dot-${level}`} />
        <span style={{ color, fontWeight: 700, fontSize: 11 }}>{alert.level}</span>
      </div>
      <div style={{ fontSize: 11, color: '#aaa', lineHeight: 1.5 }}>
        ✓ {alert.message}
      </div>
    </div>
  )
}

function EvacuationPanel({ evacuation, visible }) {
  if (!visible) return null
  return (
    <div style={{
      background: '#ef444411', border: '1px solid #ef444466',
      borderRadius: 8, padding: '14px', animation: 'pulse 0.8s infinite alternate',
    }}>
      <div style={{ color: '#ef4444', fontWeight: 700, fontSize: 13, marginBottom: 8 }}>
        🚨 EVACUATION ROUTE ACTIVE
      </div>
      {evacuation?.evacuation_route?.length > 0 && (
        <div style={{ fontSize: 11, color: '#fca5a5', lineHeight: 1.8 }}>
          {evacuation.evacuation_route.map((node, i) => (
            <span key={node}>
              {i > 0 && <span style={{ color: '#ef4444', margin: '0 4px' }}>→</span>}
              <span style={{ background: '#ef444422', padding: '1px 6px', borderRadius: 4 }}>{node}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

export default function App() {
  const { state, connected } = useWebSocket()

  if (!state) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexDirection: 'column', gap: 16, color: '#6a6a8a',
      }}>
        <div style={{ fontSize: 32 }}>🎯</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: '#e0e0f0' }}>CrowdSafe AI Command Center</div>
        <div style={{ fontSize: 13 }}>{connected ? 'Loading data...' : 'Connecting to backend...'}</div>
        <div style={{
          width: 200, height: 4, background: '#1e1e2e', borderRadius: 2, overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', background: '#3b82f6', borderRadius: 2,
            animation: 'slideIn 1.5s ease-in-out infinite',
          }} />
        </div>
        <style>{`@keyframes slideIn { 0%{width:0;margin-left:0} 50%{width:100%;margin-left:0} 100%{width:0;margin-left:200px} }`}</style>
      </div>
    )
  }

  const { cameras = {}, global_risk_score = 0, global_risk_level = 'LOW',
    total_people = 0, alerts = [], evacuation = {}, risk_history = [] } = state

  const camList = Object.values(cameras)
  const isCritical = global_risk_level === 'CRITICAL'

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0f', padding: '12px 16px' }}>
      {/* ── HEADER ── */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        marginBottom: 14, paddingBottom: 12,
        borderBottom: '1px solid #1e1e2e',
      }}>
        {/* Brand */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 22 }}>🎯</span>
            <span style={{ fontSize: 20, fontWeight: 800, background: 'linear-gradient(90deg,#06b6d4,#a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              CrowdSafe AI Command Center
            </span>
          </div>
          <div style={{ fontSize: 11, color: '#6a6a8a', marginLeft: 34, marginTop: 2 }}>
            Real-Time Multi-Camera Crowd Risk Intelligence & Evacuation System
          </div>
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', gap: 40, alignItems: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: '#6a6a8a', letterSpacing: '0.1em' }}>GLOBAL RISK</div>
            <div style={{ fontSize: 24, fontWeight: 800, color: { LOW:'#00d084', MEDIUM:'#f0b429', HIGH:'#f97316', CRITICAL:'#ef4444' }[global_risk_level] }}>
              {global_risk_score?.toFixed(0)}%
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, justifyContent: 'center' }}>
              <span className={`dot dot-${global_risk_level}`} />
              <span style={{ fontSize: 11, color: '#8a8aaa' }}>{global_risk_level}</span>
            </div>
          </div>

          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: '#6a6a8a', letterSpacing: '0.1em' }}>TOTAL DETECTED</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: '#e0e0f0' }}>{total_people}</div>
            <div style={{ fontSize: 11, color: '#8a8aaa' }}>👥 persons</div>
          </div>

          <Clock />
        </div>
      </div>

      {/* ── MAIN GRID ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 12 }}>
        {/* LEFT: Camera grid + analytics */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Camera grid */}
          <div className="panel">
            <div className="panel-title">📹 Live Camera Feeds</div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, 1fr)',
              gap: 14,
            }}>
              {camList.length > 0 ? camList.map(cam => (
                <CameraFeed key={cam.camera_id} camera={cam} />
              )) : (
                <div style={{ color: '#6a6a8a', gridColumn: 'span 2', textAlign: 'center', padding: 40 }}>
                  No cameras connected
                </div>
              )}
            </div>
          </div>

          {/* Evacuation panel - only when CRITICAL */}
          {isCritical && (
            <EvacuationPanel evacuation={evacuation} visible={isCritical} />
          )}

          {/* Bottom analytics row */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
            {/* Risk timeline */}
            <div className="panel" style={{ gridColumn: 'span 1' }}>
              <div className="panel-title">📈 Risk Timeline (60s)</div>
              <RiskTimeline history={risk_history.slice(-360)} />
            </div>

            {/* Zone comparison */}
            <div className="panel">
              <div className="panel-title">📊 Zone Risk Comparison</div>
              <ZoneRiskComparison cameras={cameras} />
            </div>

            {/* Evacuation network */}
            <div className="panel">
              <div className="panel-title">🗺 Evacuation Network</div>
              <EvacuationNetwork evacuation={evacuation} />
            </div>
          </div>

          {/* Sub-score breakdown */}
          <div className="panel">
            <div className="panel-title">📉 Zone Sub-Score Breakdown</div>
            <ZoneSubScores cameras={cameras} />
          </div>
        </div>

        {/* RIGHT: Risk sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div className="panel">
            <div className="panel-title">🌐 Global Risk Gauge</div>
            <RiskGauge score={global_risk_score} level={global_risk_level} />
            <MonitoringPanel level={global_risk_level} score={global_risk_score} />
          </div>

          <AlertPanel alerts={alerts} level={global_risk_level} />

          {/* Connection status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 10px',
            background: '#111118', borderRadius: 6, border: '1px solid #1e1e2e' }}>
            <span className={`dot ${connected ? 'dot-LOW' : 'dot-HIGH'}`} />
            <span style={{ fontSize: 10, color: '#6a6a8a' }}>
              {connected ? 'Backend connected' : 'Reconnecting...'}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
