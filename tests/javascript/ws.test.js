import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { Bus, send, init } from '../../dcs_log_viewer/static/js/ws.js';

describe('WebSocket Client', () => {
  let mockSocket;
  let eventListeners = {};

  beforeEach(() => {
    vi.useFakeTimers();
    eventListeners = {};
    
    // Mock WebSocket
    mockSocket = {
      send: vi.fn(),
      close: vi.fn(),
      readyState: 0, // CONNECTING
      addEventListener: vi.fn((event, cb) => {
        eventListeners[event] = cb;
      }),
    };

    global.WebSocket = vi.fn(() => mockSocket);
    global.WebSocket.OPEN = 1;
    
    global.location = {
      host: 'localhost:8000'
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should connect and emit status on open', () => {
    const spy = vi.fn();
    Bus.on('status', spy);

    init();
    expect(global.WebSocket).toHaveBeenCalledWith('ws://localhost:8000/ws');
    
    // Simulate open
    eventListeners['open']();
    expect(spy).toHaveBeenCalledWith('connected');
  });

  it('should emit status and reconnect on close', () => {
    const spy = vi.fn();
    Bus.on('status', spy);

    init();
    eventListeners['close']();
    
    expect(spy).toHaveBeenCalledWith('disconnected');
    
    // Should trigger reconnection timer
    vi.advanceTimersByTime(2000);
    expect(global.WebSocket).toHaveBeenCalledTimes(2);
  });

  it('should emit message data on message event', () => {
    const spy = vi.fn();
    Bus.on('test_event', spy);

    init();
    
    const mockData = JSON.stringify({ type: 'test_event', payload: 'hello' });
    eventListeners['message']({ data: mockData });
    
    expect(spy).toHaveBeenCalledWith({ type: 'test_event', payload: 'hello' });
  });

  it('should send objects as JSON when open', () => {
    init();
    mockSocket.readyState = 1; // OPEN
    
    send({ foo: 'bar' });
    expect(mockSocket.send).toHaveBeenCalledWith('{"foo":"bar"}');
  });

  it('should not send when not open', () => {
    init();
    mockSocket.readyState = 0; // CONNECTING
    
    send({ foo: 'bar' });
    expect(mockSocket.send).not.toHaveBeenCalled();
  });

  it('should close on error', () => {
    init();
    eventListeners['error']();
    expect(mockSocket.close).toHaveBeenCalled();
  });

  it('should remove handlers with off()', () => {
    const spy = vi.fn();
    Bus.on('foo', spy);
    Bus.off('foo', spy);
    Bus.emit('foo', 'bar');
    expect(spy).not.toHaveBeenCalled();
  });

  it('should remove all handlers for an event with off()', () => {
    const spy = vi.fn();
    Bus.on('bar', spy);
    Bus.off('bar');
    Bus.emit('bar', 'baz');
    expect(spy).not.toHaveBeenCalled();
  });
});
