import { useEffect } from 'react';
import mqtt from 'mqtt';

export function useTelem(onMessage: (msg: string) => void) {
  useEffect(() => {
    const client = mqtt.connect('ws://localhost:1884');
    client.subscribe('telem/data');
    client.on('message', (_t, m) => onMessage(m.toString()));
    return () => client.end();
  }, [onMessage]);
}
