export const websocketConfig = {
  development: {
    perMessageDeflate: false,
    maxPayload: 16 * 1024 * 1024,
    pingInterval: 30000,
    pongTimeout: 5000,
  },
  production: {
    perMessageDeflate: {
      zlibDeflateOptions: {
        level: 6,
        chunkSize: 1024,
      },
    },
    maxPayload: 16 * 1024 * 1024,
    pingInterval: 30000,
    pongTimeout: 5000,
  },
};
