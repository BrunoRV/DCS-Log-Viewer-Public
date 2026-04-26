/**
 * ws.js — WebSocket client with auto-reconnect.
 * Emits typed events via a simple publish/subscribe bus so other modules
 * don't need to import this file; they just listen on `Bus`.
 */

export const Bus = (() => {
  const _handlers = {};
  return {
    on(event, fn) {
      (_handlers[event] = _handlers[event] || []).push(fn);
    },
    off(event, fn) {
      if (!fn) { delete _handlers[event]; return; }
      _handlers[event] = (_handlers[event] || []).filter(f => f !== fn);
    },
    emit(event, payload) {
      (_handlers[event] || []).forEach(fn => fn(payload));
    },
  };
})();

let _socket = null;
let _reconnectTimer = null;
const RECONNECT_DELAY_MS = 2000;

export function send(obj) {
  if (_socket && _socket.readyState === WebSocket.OPEN) {
    _socket.send(JSON.stringify(obj));
  }
}

function connect() {
  const url = `ws://${location.host}/ws`;
  _socket = new WebSocket(url);

  _socket.addEventListener('open', () => {
    clearTimeout(_reconnectTimer);
    Bus.emit('status', 'connected');
  });

  _socket.addEventListener('close', () => {
    Bus.emit('status', 'disconnected');
    _reconnectTimer = setTimeout(connect, RECONNECT_DELAY_MS);
  });

  _socket.addEventListener('error', () => {
    _socket.close();
  });

  _socket.addEventListener('message', ({ data }) => {
    try {
      const msg = JSON.parse(data);
      Bus.emit(msg.type, msg);   // e.g. Bus.emit('init', { entries:[...], total:N })
    } catch (e) {
      console.warn('[ws] bad message', e);
    }
  });
}

export function init() {
  connect();
}
