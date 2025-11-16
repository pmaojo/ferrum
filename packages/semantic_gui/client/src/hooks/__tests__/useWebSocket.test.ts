import { renderHook } from '@testing-library/react';
import {
  describe,
  it,
  expect,
  beforeEach,
  afterEach,
  jest,
} from '@jest/globals';
import { useWebSocket } from '../useWebSocket';

describe('useWebSocket', () => {
  const originalWebSocket = global.WebSocket;
  const originalEnv = process.env.VITE_WS_URL;

  beforeEach(() => {
    delete process.env.VITE_WS_URL;
  });

  afterEach(() => {
    global.WebSocket = originalWebSocket;
    if (originalEnv !== undefined) {
      process.env.VITE_WS_URL = originalEnv;
    } else {
      delete process.env.VITE_WS_URL;
    }
  });

  it('uses VITE_WS_URL when provided', () => {
    const mockWebSocket = jest.fn().mockImplementation(() => ({
      readyState: 1,
      send: jest.fn(),
      close: jest.fn(),
      onopen: null,
      onmessage: null,
      onclose: null,
      onerror: null,
    }));

    global.WebSocket = mockWebSocket as unknown as typeof WebSocket;
    process.env.VITE_WS_URL = 'ws://example.com';

    const { unmount } = renderHook(() => useWebSocket<unknown>());

    expect(mockWebSocket).toHaveBeenCalledWith('ws://example.com');

    unmount();
  });
});
