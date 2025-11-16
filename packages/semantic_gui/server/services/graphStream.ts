import {
  WebSocketGraphStreamAdapter,
  GraphStreamEventType,
  type GraphStreamEvent,
} from './graphStreamAdapter';

// Singleton instance of the graph stream adapter
export const graphStreamAdapter = new WebSocketGraphStreamAdapter();

export { GraphStreamEventType };
export type { GraphStreamEvent };
