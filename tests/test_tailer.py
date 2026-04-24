import asyncio
import pytest
import os
from pathlib import Path
from dcs_log_viewer.tailer import LogTailer

@pytest.mark.asyncio
async def test_initial_load(tmp_path):
    """Verify that LogTailer correctly reads existing file content on startup."""
    log_file = tmp_path / "dcs.log"
    content = (
        "2026-04-23 23:10:52.872 INFO    A (1): Line 1\n"
        "2026-04-23 23:10:53.000 INFO    B (2): Line 2\n"
    ).encode("utf-8")
    log_file.write_bytes(content)
    
    tailer = LogTailer(log_file, window_lines=10)
    entries = await tailer.initial_load()
    
    assert len(entries) == 2
    assert entries[0].message == "Line 1"
    assert entries[1].message == "Line 2"
    assert tailer._offset == len(content)

@pytest.mark.asyncio
async def test_watch_new_entries(tmp_path):
    """Verify that LogTailer detects and yields new lines appended to the file."""
    log_file = tmp_path / "dcs.log"
    log_file.write_bytes("2026-04-23 23:10:52.872 INFO    A (1): Line 1\n".encode("utf-8"))
    
    tailer = LogTailer(log_file, window_lines=10)
    await tailer.initial_load()
    
    batches = []
    
    async def collect():
        async for batch in tailer.watch():
            batches.append(batch)
            if len(batches) >= 1:
                tailer.stop()

    watch_task = asyncio.create_task(collect())
    await asyncio.sleep(0.3)
    
    with open(log_file, "ab") as f:
        f.write("2026-04-23 23:10:54.000 INFO    C (3): Line 3\n".encode("utf-8"))
    
    try:
        await asyncio.wait_for(watch_task, timeout=2.0)
    except asyncio.TimeoutError:
        tailer.stop()
        await watch_task
    
    assert len(batches) >= 1
    assert batches[0][0].message == "Line 3"

@pytest.mark.asyncio
async def test_log_rotation(tmp_path):
    """Verify that LogTailer detects file rotation (truncation or replacement) and resets."""
    log_file = tmp_path / "dcs.log"
    # Make the first file larger so the size check triggers rotation even if inode is reused
    log_file.write_bytes(("A" * 100 + "\n").encode("utf-8"))
    
    tailer = LogTailer(log_file, window_lines=10)
    await tailer.initial_load()
    assert tailer._offset > 10
    
    # Simulate rotation with a smaller file
    log_file.unlink()
    await asyncio.sleep(0.1)
    log_file.write_bytes("2026-04-23 23:10:55.000 INFO    D (4): New Start\n".encode("utf-8"))
    
    batches = []
    async def collect():
        async for batch in tailer.watch():
            batches.append(batch)
            tailer.stop()

    watch_task = asyncio.create_task(collect())
    try:
        await asyncio.wait_for(watch_task, timeout=2.0)
    except asyncio.TimeoutError:
        tailer.stop()
        await watch_task
    except asyncio.CancelledError:
        pass # Task was cancelled by wait_for timeout
    
    assert len(batches) >= 1
    assert batches[0][0].message == "New Start"

@pytest.mark.asyncio
async def test_read_incomplete_line(tmp_path):
    """Verify that LogTailer buffers partial lines and only parses them once complete."""
    log_file = tmp_path / "dcs.log"
    log_file.write_bytes("2026-04-23 23:10:52.872 INFO    A (1): Line 1\n".encode("utf-8"))
    
    tailer = LogTailer(log_file, window_lines=10)
    await tailer.initial_load()
    
    # Append incomplete line
    with open(log_file, "ab") as f:
        f.write("2026-04-23 23:10:56.000 INFO    E (5): Incomplete".encode("utf-8"))
    
    # Should not yield anything and offset should NOT move
    old_offset = tailer._offset
    entries = await tailer._read_new_entries()
    assert len(entries) == 0
    assert tailer._offset == old_offset
    
    # Complete the line
    with open(log_file, "ab") as f:
        f.write(" line\n".encode("utf-8"))
    
    entries = await tailer._read_new_entries()
    assert len(entries) == 1
    assert entries[0].message == "Incomplete line"
    assert tailer._offset > old_offset
