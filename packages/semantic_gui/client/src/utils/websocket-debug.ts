export class WebSocketDebugger<T = unknown> {
  private static instance: WebSocketDebugger<unknown>;
  private logs: Array<{ timestamp: string; type: string; data: T }> = [];

  static getInstance<T = unknown>(): WebSocketDebugger<T> {
    if (!WebSocketDebugger.instance) {
      WebSocketDebugger.instance = new WebSocketDebugger<unknown>();
    }
    return WebSocketDebugger.instance as WebSocketDebugger<T>;
  }

  log(type: string, data: T): void {
    const entry = {
      timestamp: new Date().toISOString(),
      type,
      data,
    };
    this.logs.push(entry);

    // Keep only last 100 entries
    if (this.logs.length > 100) {
      this.logs.shift();
    }

    if (process.env.NODE_ENV === 'development') {
      console.log(`[WebSocket ${type}]`, data);
    }
  }

  getLogs(): Array<{ timestamp: string; type: string; data: T }> {
    return [...this.logs];
  }

  clearLogs(): void {
    this.logs = [];
  }
}
