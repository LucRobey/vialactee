import asyncio
import json
import pytest
from core.PresetRepository import PresetRepository


def test_preset_repository_init():
    repo = PresetRepository({"hardware_profile": "full"})
    assert repo.infos == {"hardware_profile": "full"}
    assert repo._app_config_flush_task is None
    assert repo._pending_app_config_snapshot is None


def test_atomic_write(tmp_path):
    repo = PresetRepository({"hardware_profile": "full"})
    target = str(tmp_path / "test_file.json")
    content = '{"key": "value"}\n'

    assert repo._atomic_write(target, content) is True
    with open(target, "r", encoding="utf-8") as f:
        assert f.read() == content
    assert not (tmp_path / "test_file.json.tmp").exists()


@pytest.mark.anyio
async def test_persist_app_config_debounced_async(tmp_path, monkeypatch):
    repo = PresetRepository({"hardware_profile": "full"})
    test_file = str(tmp_path / "app_config_test.json")
    monkeypatch.setattr(repo, "_resolve_app_config_path", lambda: test_file)

    # Write settings including mode_settings
    repo.persist_app_config_debounced("luminosity", 50, delay_seconds=0.05)
    repo.persist_app_config_debounced("sensibility", 70, delay_seconds=0.05)
    repo.persist_app_config_debounced("mode_settings", {"Rainbow": {"speed": 2.5}}, delay_seconds=0.05)

    data = {}
    for _ in range(30):
        await asyncio.sleep(0.05)
        if (tmp_path / "app_config_test.json").exists():
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("mode_settings"):
                    break
            except Exception:
                pass

    assert (tmp_path / "app_config_test.json").exists()
    assert data["luminosity"] == 50
    assert data["sensibility"] == 70
    assert data["mode_settings"]["Rainbow"]["speed"] == 2.5
    assert repo._pending_app_config_snapshot is None


def test_persist_app_config_sync(tmp_path, monkeypatch):
    repo = PresetRepository({"hardware_profile": "full"})
    test_file = str(tmp_path / "app_config_sync.json")
    monkeypatch.setattr(repo, "_resolve_app_config_path", lambda: test_file)

    repo._persist_app_config_value_sync("auto_transition_time", 42)
    assert (tmp_path / "app_config_sync.json").exists()
    with open(test_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["auto_transition_time"] == 42


@pytest.mark.anyio
async def test_flush_sync_immediate_persistence(tmp_path, monkeypatch):
    repo = PresetRepository({"hardware_profile": "full"})
    app_file = str(tmp_path / "app_config_flush.json")
    monkeypatch.setattr(repo, "_resolve_app_config_path", lambda: app_file)

    repo.persist_app_config_debounced("luminosity", 99, delay_seconds=10.0)

    # Immediate shutdown flush
    repo.flush_sync()
    assert (tmp_path / "app_config_flush.json").exists()
    with open(app_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["luminosity"] == 99
    assert repo._pending_app_config_snapshot is None
    await asyncio.sleep(0.01)
    assert repo._app_config_flush_task.cancelled()


def test_concurrent_atomic_writes(tmp_path):
    import concurrent.futures
    repo = PresetRepository({"hardware_profile": "full"})
    target = str(tmp_path / "concurrent_output.json")

    def worker(i):
        return repo._atomic_write(target, f'{{"thread_id": {i}}}\n')

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(worker, range(20)))

    assert all(results)
    assert (tmp_path / "concurrent_output.json").exists()
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0


@pytest.mark.anyio
async def test_persist_app_config_debounced_no_disk_reads_during_slider_updates(tmp_path, monkeypatch):
    import builtins
    repo = PresetRepository({"hardware_profile": "full"})
    test_file = str(tmp_path / "app_config_reads_test.json")
    monkeypatch.setattr(repo, "_resolve_app_config_path", lambda: test_file)

    # Initial file creation
    repo._atomic_write(test_file, '{"initial": 1}\n')

    # Warm up cache
    repo.persist_app_config_debounced("val", 0, delay_seconds=0.05)

    original_open = builtins.open
    read_open_calls = []

    def tracking_open(file, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        if str(file) == test_file and "r" in mode and "w" not in mode and "+" not in mode:
            read_open_calls.append(str(file))
        return original_open(file, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", tracking_open)

    # Drag slider rapidly 20 times
    for i in range(1, 21):
        repo.persist_app_config_debounced("val", i, delay_seconds=0.05)

    # Verify zero disk reads occurred during the 20 rapid slider updates
    assert len(read_open_calls) == 0

    data = {}
    for _ in range(20):
        await asyncio.sleep(0.05)
        try:
            with original_open(test_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("val") == 20:
                break
        except Exception:
            pass
    assert data.get("val") == 20
