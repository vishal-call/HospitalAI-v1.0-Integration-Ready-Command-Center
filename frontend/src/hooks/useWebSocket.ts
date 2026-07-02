import { useEffect, useRef, useState } from "react";

export function useWebSocket(url: string, onMessage?: (data: unknown) => void) {
  const [connected, setConnected] = useState(false);
  const [metrics, setMetrics] = useState<unknown>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelayRef = useRef(1000); // starts at 1s
  const maxDelay = 30000; // max 30s
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastTimestampRef = useRef<string | null>(null);

  const connect = () => {
    if (!url) return;
    if (wsRef.current) return;

    let targetUrl = url;
    if (lastTimestampRef.current) {
      const separator = targetUrl.includes("?") ? "&" : "?";
      targetUrl = `${targetUrl}${separator}last_received_timestamp=${encodeURIComponent(lastTimestampRef.current)}`;
    }

    console.log(`Connecting to WebSocket: ${targetUrl}`);
    const ws = new WebSocket(targetUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      reconnectDelayRef.current = 1000; // reset delay on success
      console.log("WebSocket connection established successfully.");
    };

    ws.onmessage = (event) => {
      lastTimestampRef.current = new Date().toISOString();
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === "INITIAL_STATE" || payload.type === "OCCUPANCY_METRICS") {
          setMetrics(payload.data);
        } else if (payload.type === "PING") {
          // Respond to server heartbeat
          ws.send(JSON.stringify({ command: "PONG" }));
        }
        if (onMessage) {
          onMessage(payload);
        }
      } catch (err) {
        console.error("Error parsing WebSocket packet:", err);
      }
    };

    ws.onclose = (event) => {
      setConnected(false);
      wsRef.current = null;
      
      // Do not reconnect on clean shutdown/close
      if (event.code === 1000) {
        console.log("WebSocket closed cleanly.");
        return;
      }

      console.warn(`WebSocket connection closed unexpectedly (code: ${event.code}). Attempting reconnect...`);
      
      // Calculate backoff delay
      const nextDelay = Math.min(reconnectDelayRef.current * 2, maxDelay);
      reconnectDelayRef.current = nextDelay;

      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        connect();
      }, reconnectDelayRef.current);
    };

    ws.onerror = (err) => {
      console.error("WebSocket connection encountered an error:", err);
      ws.close();
    };
  };

  useEffect(() => {
    connect();

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
      if (wsRef.current) {
        wsRef.current.onclose = null; // detach listener to prevent loop
        wsRef.current.onerror = null; // detach error listener to prevent false positives during unmount
        wsRef.current.close(1000); // clean close
        wsRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  return { connected, metrics };
}
