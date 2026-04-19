import React, { memo } from 'react'

const W = 420, H = 300

const EvacuationNetwork = memo(({ evacuation = {} }) => {
  const {
    nodes = [], edges = [],
    evacuation_route = [], active = false,
    nearest_exits = [],
  } = evacuation

  const nodeMap = {}
  nodes.forEach(n => { nodeMap[n.id] = n })

  const displayRoute = active && evacuation_route.length > 0
    ? evacuation_route
    : ['Main Hall', 'Corridor', 'Entrance', 'Emergency Exit North', 'Assembly Point']

  const routeEdges = new Set()
  for (let i = 0; i < displayRoute.length - 1; i++) {
    routeEdges.add(`${displayRoute[i]}||${displayRoute[i + 1]}`)
    routeEdges.add(`${displayRoute[i + 1]}||${displayRoute[i]}`)
  }
  const routeNodes   = new Set(displayRoute)
  const routeColor   = active ? '#ef4444' : '#3b82f6'

  // Build nearest exit pairs
  const nearestSet   = new Set(nearest_exits.map(n => n.exit))
  const nearestZones = new Set(nearest_exits.map(n => n.zone))

  return (
    <div>
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginBottom: 8,
      }}>
        <div style={{ fontSize: 10, color: '#6a6a8a' }}>Building Topology</div>
        {active
          ? <span style={{ fontSize: 10, color: '#ef4444', fontWeight: 700 }}>🚨 EVACUATION ACTIVE</span>
          : <span style={{ fontSize: 10, color: '#3b82f6' }}>📋 Default Route Preview</span>
        }
      </div>

      <svg width="100%" viewBox={`0 0 ${W} ${H}`}>
        <defs>
          {/* Arrow marker for nearest exit */}
          <marker id="arrow-red" markerWidth="8" markerHeight="8"
            refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#ef4444" />
          </marker>
          <marker id="arrow-orange" markerWidth="8" markerHeight="8"
            refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L8,3 z" fill="#f97316" />
          </marker>
        </defs>

        {/* Non-route edges */}
        {edges.map((e, i) => {
          const f = nodeMap[e.from], t = nodeMap[e.to]
          if (!f || !t) return null
          const isRoute = routeEdges.has(`${e.from}||${e.to}`)
          if (isRoute) return null
          return (
            <line key={i}
              x1={f.x * W} y1={f.y * H}
              x2={t.x * W} y2={t.y * H}
              stroke="#2a2a3a" strokeWidth={1} opacity={0.5}
            />
          )
        })}

        {/* Route edges */}
        {edges.map((e, i) => {
          const f = nodeMap[e.from], t = nodeMap[e.to]
          if (!f || !t) return null
          const isRoute = routeEdges.has(`${e.from}||${e.to}`)
          if (!isRoute) return null
          return (
            <g key={`re-${i}`}>
              <line x1={f.x*W} y1={f.y*H} x2={t.x*W} y2={t.y*H}
                stroke={routeColor} strokeWidth={8} opacity={0.15} />
              <line x1={f.x*W} y1={f.y*H} x2={t.x*W} y2={t.y*H}
                stroke={routeColor} strokeWidth={2.5} />
            </g>
          )
        })}

        {/* Nearest exit arrows from critical zones */}
        {nearest_exits.map((ne, i) => {
          const from = nodeMap[ne.zone]
          const to   = nodeMap[ne.exit]
          if (!from || !to) return null
          return (
            <g key={`ne-${i}`}>
              {/* Dashed arrow line */}
              <line
                x1={from.x * W} y1={from.y * H}
                x2={to.x * W}   y2={to.y * H}
                stroke="#f97316"
                strokeWidth={2}
                strokeDasharray="5 3"
                markerEnd="url(#arrow-orange)"
                opacity={0.9}
              />
              {/* Distance label at midpoint */}
              <text
                x={(from.x + to.x) / 2 * W}
                y={(from.y + to.y) / 2 * H - 6}
                textAnchor="middle"
                fill="#f97316"
                fontSize={8}
                fontWeight={700}
              >
                NEAREST EXIT
              </text>
            </g>
          )
        })}

        {/* Nodes */}
        {nodes.map(n => {
          const isRoute    = routeNodes.has(n.id)
          const isAssembly = n.id === 'Assembly Point'
          const isStart    = n.id === displayRoute[0]
          const isNearest  = nearestSet.has(n.id)
          const isCritical = nearestZones.has(n.id)

          const color = isAssembly   ? '#00d084'
            : isCritical             ? '#ef4444'
            : isNearest              ? '#f97316'
            : isStart                ? '#f0b429'
            : isRoute                ? routeColor
            : '#334155'

          const radius = isAssembly || isCritical ? 9 : isRoute || isNearest ? 7 : 5

          return (
            <g key={n.id}>
              {(isRoute || isNearest || isCritical) && (
                <circle cx={n.x*W} cy={n.y*H} r={radius+6}
                  fill={color} opacity={0.15} />
              )}
              <circle cx={n.x*W} cy={n.y*H} r={radius}
                fill={color} fillOpacity={0.25}
                stroke={color} strokeWidth={isRoute || isCritical ? 2 : 1}
              />
              {/* Critical zone pulse ring */}
              {isCritical && (
                <circle cx={n.x*W} cy={n.y*H} r={radius+10}
                  fill="none" stroke="#ef4444" strokeWidth={1}
                  opacity={0.4}
                />
              )}
              <text
                x={n.x*W} y={n.y*H + radius + 10}
                textAnchor="middle"
                fill={isRoute || isNearest || isCritical ? color : '#4a5568'}
                fontSize={isRoute || isCritical ? 9 : 8}
                fontWeight={isRoute || isCritical ? 700 : 400}
              >
                {n.id}
              </text>
            </g>
          )
        })}

        {/* Midpoint dots on route */}
        {displayRoute.slice(0, -1).map((nodeId, i) => {
          const f = nodeMap[nodeId]
          const t = nodeMap[displayRoute[i+1]]
          if (!f || !t) return null
          return (
            <circle key={`mid-${i}`}
              cx={(f.x+t.x)/2*W} cy={(f.y+t.y)/2*H}
              r={3} fill={routeColor} opacity={0.8}
            />
          )
        })}
      </svg>

      {/* Nearest exits legend */}
      {nearest_exits.length > 0 && (
        <div style={{
          marginTop: 6, padding: '6px 10px',
          background: '#f9731611', border: '1px solid #f9731633',
          borderRadius: 6, fontSize: 10, color: '#f97316',
        }}>
          🚪 Nearest exits: {nearest_exits.map(ne =>
            `${ne.zone} → ${ne.exit}`
          ).join('  |  ')}
        </div>
      )}

      {/* Evacuation route */}
      <div style={{
        marginTop: 6, padding: '8px 10px',
        background: active ? '#ef444411' : '#3b82f611',
        border: `1px solid ${active ? '#ef444433' : '#3b82f633'}`,
        borderRadius: 6, fontSize: 11,
        color: active ? '#ef4444' : '#3b82f6',
        lineHeight: 1.8,
      }}>
        {active ? '🚨' : '📋'} {displayRoute.join(' → ')}
      </div>
    </div>
  )
})

export default EvacuationNetwork