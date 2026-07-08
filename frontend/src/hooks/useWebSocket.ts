import { useEffect, useRef, useState } from "react";

export function useWebSocket(url: string, onMessage?: (data: unknown) => void) {
  const [connected, setConnected] = useState(false);
  const [metrics, setMetrics] = useState<unknown>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectDelayRef = useRef(1000); // starts at 1s
  const maxDelay = 30000; // max 30s
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastTimestampRef = useRef<string | null>(null);

  // Heartbeat / Zombie Connection Detection Refs
  const lastMessageTimeRef = useRef<number>(Date.now());
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
      lastMessageTimeRef.current = Date.now();
      console.log("WebSocket connection established successfully.");

      // Start the heartbeat monitor interval (check every 5 seconds)
      if (heartbeatIntervalRef.current) clearInterval(heartbeatIntervalRef.current);
      heartbeatIntervalRef.current = setInterval(() => {
        if (Date.now() - lastMessageTimeRef.current > 45000) {
          console.warn("WebSocket heartbeat timeout (zombie connection detected). Forcing reconnect...");
          ws.close();
        }
      }, 5000);
    };

    ws.onmessage = (event) => {
      lastTimestampRef.current = new Date().toISOString();
      lastMessageTimeRef.current = Date.now(); // update message timestamp
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

      // Clear the heartbeat interval on close
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }
      
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

    // Browser events for network status recovery and tab visible wakeups
    const handleOnline = () => {
      console.log("Browser went online. Forcing WebSocket reconnect...");
      if (wsRef.current) {
        wsRef.current.close();
      } else {
        connect();
      }
    };

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        console.log("Tab became active. Verifying WebSocket connection state...");
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          console.warn("WebSocket state not open. Restoring connection...");
          if (wsRef.current) {
            wsRef.current.close();
          } else {
            connect();
          }
        }
      }
    };

    if (typeof window !== "undefined") {
      window.addEventListener("online", handleOnline);
      window.addEventListener("visibilitychange", handleVisibilityChange);
    }

    return () => {
      if (typeof window !== "undefined") {
        window.removeEventListener("online", handleOnline);
        window.removeEventListener("visibilitychange", handleVisibilityChange);
      }
      if (heartbeatIntervalRef.current) {
        clearInterval(heartbeatIntervalRef.current);
        heartbeatIntervalRef.current = null;
      }
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
