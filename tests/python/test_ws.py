import json
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from fastapi import WebSocketDisconnect
from dcs_log_web.main import app
import dcs_log_web.ws as ws_module

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_ws_state():
    # Clear clients and tasks before each test
    ws_module._clients.clear()
    ws_module._config = {"window_lines": 100, "log_path": ""}
    if ws_module._watch_task and not ws_module._watch_task.done():
        ws_module._watch_task.cancel()
    ws_module._watch_task = None
    ws_module._tailer = None

def test_websocket_connect():
    """Verify that clients receive the current configuration immediately upon connecting."""
    with client.websocket_connect("/ws") as websocket:
        # Should send config on connect
        data = websocket.receive_json()
        assert data["type"] == "config"
        assert data["data"]["window_lines"] == 100
        assert len(ws_module._clients) == 1

@pytest.mark.asyncio
async def test_broadcast():
    """Verify that messages are sent to all clients and dead sockets are pruned."""
    # Use AsyncMock for send_text
    mock_ws1 = MagicMock()
    mock_ws1.send_text = AsyncMock()
    
    mock_ws2 = MagicMock()
    mock_ws2.send_text = AsyncMock(side_effect=Exception("Connection lost"))
    
    ws_module._clients.add(mock_ws1)
    ws_module._clients.add(mock_ws2)
    
    msg = {"type": "test"}
    await ws_module.broadcast(msg)
    
    mock_ws1.send_text.assert_called_once_with(json.dumps(msg))
    # mock_ws2 should have been removed due to exception
    assert mock_ws2 not in ws_module._clients
    assert mock_ws1 in ws_module._clients

@pytest.mark.asyncio
async def test_websocket_actions():
    """Verify that the server correctly processes all supported client-side actions."""
    ws_module._config = {"log_path": "", "window_lines": 100}
    
    # We use a patch on start_watch to avoid actual tailing logic
    with patch("dcs_log_web.ws.start_watch", new_callable=AsyncMock) as mock_start:
        with client.websocket_connect("/ws") as websocket:
            websocket.receive_json() # ignore initial config
            
            # Test set_path action
            websocket.send_json({"action": "set_path", "path": "test.log"})
            # Give the server loop a moment to process
            await asyncio.sleep(0.1)
            assert ws_module._config["log_path"] == "test.log"
            mock_start.assert_called_with("test.log")
            
            # Test set_config
            websocket.send_json({"action": "set_config", "window_lines": 500})
            await asyncio.sleep(0.1)
            assert ws_module._config["window_lines"] == 500
            
            # Test reload
            websocket.send_json({"action": "reload"})
            await asyncio.sleep(0.1)
            # mock_start should have been called again
            assert mock_start.call_count >= 3
            
            # Test clear
            with patch("dcs_log_web.ws.broadcast", new_callable=AsyncMock) as mock_broadcast:
                websocket.send_json({"action": "clear"})
                await asyncio.sleep(0.1)
                mock_broadcast.assert_called_with({"type": "clear"})

def test_websocket_invalid_json():
    """Verify that malformed JSON messages from clients do not crash the server."""
    with client.websocket_connect("/ws") as websocket:
        websocket.receive_json()
        websocket.send_text("invalid json")
        # Should not crash and still be connected
        assert len(ws_module._clients) == 1

@pytest.mark.asyncio
@patch("dcs_log_web.ws.LogTailer")
@patch("dcs_log_web.ws.Path.exists")
async def test_start_watch_lifecycle(mock_exists, mock_tailer_class):
    """Verify that starting a new watch correctly cancels any existing watch tasks."""
    mock_exists.return_value = True
    mock_tailer = MagicMock()
    mock_tailer_class.return_value = mock_tailer
    mock_tailer.initial_load = AsyncMock(return_value=[])
    
    async def empty_iter():
        if False: yield []
    mock_tailer.watch.return_value = empty_iter()
    
    # Start first watch
    await ws_module.start_watch("first.log")
    task1 = ws_module._watch_task
    assert task1 is not None
    
    # Start second watch (should restart)
    await ws_module.start_watch("second.log")
    assert ws_module._watch_task != task1
    # task1 should be cancelled
    assert task1.done()

@pytest.mark.asyncio
@patch("dcs_log_web.ws.broadcast", new_callable=AsyncMock)
@patch("dcs_log_web.ws.Path.exists")
async def test_start_watch_file_not_found(mock_exists, mock_broadcast):
    """Verify that the server broadcasts an error if the requested log file does not exist."""
    mock_exists.return_value = False
    await ws_module.start_watch("missing.log")
    mock_broadcast.assert_called_once()
    assert "File not found" in mock_broadcast.call_args[0][0]["message"]

@pytest.mark.asyncio
@patch("dcs_log_web.ws.LogTailer")
@patch("dcs_log_web.ws.Path.exists")
async def test_watcher_loop_error(mock_exists, mock_tailer_class):
    """Verify that watcher crashes are caught and broadcasted to clients."""
    mock_exists.return_value = True
    mock_tailer = MagicMock()
    mock_tailer_class.return_value = mock_tailer
    mock_tailer.initial_load = AsyncMock(return_value=[])
    
    async def error_iter():
        yield [{"msg": "data"}]
        raise Exception("Watcher Crash")
    
    mock_tailer.watch.return_value = error_iter()
    
    with patch("dcs_log_web.ws.broadcast", new_callable=AsyncMock) as mock_broadcast:
        await ws_module.start_watch("crash.log")
        # Wait for the task to run and crash
        await asyncio.sleep(0.1)
        
        # Should have broadcasted the error
        any_error = any(call[0][0].get("type") == "error" for call in mock_broadcast.call_args_list)
        assert any_error

def test_ws_config_helpers():
    """Verify the module-level config accessors."""
    cfg = {"test": 123}
    ws_module.set_config(cfg)
    assert ws_module.get_config() == cfg

def test_websocket_auto_start_on_connect():
    """Verify that the watcher starts immediately if a path is already configured."""
    ws_module._config = {"log_path": "auto.log"}
    with patch("dcs_log_web.ws.start_watch", new_callable=AsyncMock) as mock_start:
        with client.websocket_connect("/ws"):
            mock_start.assert_called_with("auto.log")
