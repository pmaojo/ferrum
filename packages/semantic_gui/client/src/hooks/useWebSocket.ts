import { useEffect, useRef, useState, useCallback } from 'react';
import { createLogger } from '../utils/logger';
import { WebSocketDebugger } from '../utils/websocket-debug';

export interface WebSocketMessage<T = unknown> {
  type: string;
  projectId?: string;
  data: T;
  timestamp: string;
}

export function useWebSocket<T = unknown>() {
  const [lastMessage, setLastMessage] = useState<WebSocketMessage<T> | null>(
    null
  );
  const [connectionStatus, setConnectionStatus] = useState<
    'connecting' | 'connected' | 'disconnected' | 'error'
  >('disconnected');
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const logger = createLogger('useWebSocket');
  const wsDebugger = WebSocketDebugger.getInstance<WebSocketMessage<T>>();

  const connect = useCallback(() => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const envUrl = (() => {
        try {
          // Avoid direct usage of import.meta to keep compatibility with test environment
          // eslint-disable-next-line no-new-func
          return new Function('return import.meta.env.VITE_WS_URL')();
        } catch {
          return typeof process !== 'undefined'
            ? (process.env.VITE_WS_URL as string | undefined)
            : undefined;
        }
      })();
      const wsUrl = envUrl ?? `${protocol}//${window.location.host}`;

      ws.current = new WebSocket(wsUrl);
      setConnectionStatus('connecting');

      ws.current.onopen = () => {
        setConnectionStatus('connected');
        reconnectAttempts.current = 0;
        logger.info('WebSocket connected', { wsUrl });
      };

      ws.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WebSocketMessage<T>;
          setLastMessage(message);
          logger.debug('WebSocket message received', {
            messageType: message.type,
          });
          wsDebugger.log('received', message);
        } catch (error) {
          logger.error('Failed to parse WebSocket message', error instanceof Error ? error : new Error(String(error)), {
            rawData: event.data
          });
        }
      };

      ws.current.onclose = (event) => {
        setConnectionStatus('disconnected');
        logger.info('WebSocket disconnected', { 
          code: event.code, 
          reason: event.reason,
          wasClean: event.wasClean 
        });

        // Attempt reconnection if not a normal closure
        if (
          event.code !== 1000 &&
          reconnectAttempts.current < maxReconnectAttempts
        ) {
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttempts.current),
            30000
          );
          logger.info('Scheduling WebSocket reconnection', { 
            attempt: reconnectAttempts.current + 1,
            maxAttempts: maxReconnectAttempts,
            delayMs: delay 
          });
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        }
      };

      ws.current.onerror = (error) => {
        logger.error('WebSocket error occurred', error instanceof Error ? error : new Error('WebSocket error'), {
          readyState: ws.current?.readyState
        });
        setConnectionStatus('error');
      };
    } catch (error) {
      logger.error('Failed to create WebSocket connection', error instanceof Error ? error : new Error(String(error)));
      setConnectionStatus('error');
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (ws.current) {
        ws.current.close(1000, 'Component unmounting');
      }
    };
  }, [connect]);

  const sendMessage = useCallback(
    (message: WebSocketMessage<T>) => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        try {
          ws.current.send(JSON.stringify(message));
          logger.debug('WebSocket message sent', {
            messageType: message.type,
          });
          wsDebugger.log('sent', message);
        } catch (error) {
          logger.error('Failed to send WebSocket message', error instanceof Error ? error : new Error(String(error)), {
            messageType: message.type
          });
        }
      } else {
        logger.warn('WebSocket not connected, message not sent', {
          messageType: message.type,
          readyState: ws.current?.readyState,
          connectionStatus
        });
      }
    },
    [logger, connectionStatus]
  );

  const reconnect = useCallback(() => {
    if (ws.current) {
      ws.current.close();
    }
    reconnectAttempts.current = 0;
    connect();
  }, [connect]);

  return {
    lastMessage,
    connectionStatus,
    sendMessage,
    reconnect,
  };
}
