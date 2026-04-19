import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = 'ws://localhost:8000/ws/live'

export function useWebSocket() {
  const [state, setState]         = useState(null)
  const [connected, setConnected] = useState(false)
  const wsRef    = useRef(null)
  const timerRef = useRef(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      clearTimeout(timerRef.current)
    }

    ws.onmessage = (e) => {
  try {
    const msg = JSON.parse(e.data)

    // ignore keepalive pings
    if (msg.type === 'ping') return

    if (msg.type !== 'state') return

    window.dispatchEvent(new CustomEvent('crowd-frames', {
      detail: msg.data.cameras
    }))

    const stripped = {
      ...msg.data,
      cameras: Object.fromEntries(
        Object.entries(msg.data.cameras || {}).map(([k, v]) => {
          const { frame_b64, ...rest } = v
          return [k, rest]
        })
      )
    }
    setState(stripped)

  } catch {}
}

    ws.onclose = () => {
      setConnected(false)
      timerRef.current = setTimeout(connect, 2000)
    }

    ws.onerror = () => ws.close()
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(timerRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  return { state, connected }
}