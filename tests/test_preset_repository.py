import asyncio
import json
import pytest
from core.PresetRepository import PresetRepository


def test_preset_repository_init():
    repo = PresetRepository({"hardware_profile": "full"})
    assert repo.configurations == {}
    assert repo.playlists == []
    assert repo.blocked_playlists == []
    assert repo.shuffle_bag == []


def test_preset_repository_load_and_pick():
    repo = PresetRepository({"hardware_profile": "full"})
    repo.load_configurations()
    assert len(repo.playlists) > 0
    assert len(repo.configurations) > 0

    conf = repo.pick_a_random_conf()
    assert isinstance(conf, dict)
    assert "name" in conf
    assert "modes" in conf


def test_preset_repository_playlist_activation():
    repo = PresetRepository({"hardware_profile": "full"})
    repo.load_configurations()
    first_playlist = repo.playlists[0]

    assert repo.set_only_playlist_active(first_playlist) is True
    # First should be False (unblocked), all others True (blocked)
    assert repo.blocked_playlists[0] is False
    for blocked in repo.blocked_playlists[1:]:
        assert blocked is True


def test_preset_repository_find_configuration():
    repo = PresetRepository({"hardware_profile": "full"})
    repo.load_configurations()
    first_playlist = repo.playlists[0]
    first_conf = repo.configurations[first_playlist][0]
    conf_name = first_conf["name"]

    found = repo.find_configuration(conf_name)
    assert found is not None
    assert found["name"] == conf_name


def test_atomic_write(tmp_path):
    repo = PresetRepository({"hardware_profile": "full"})
    target = str(tmp_path / "test_file.json")
    content = '{"key": "value"}\n'

    assert repo._atomic_write(target, content) is True
    with open(target, "r", encoding="utf-8") as f:
        assert f.read() == content
    assert not (tmp_path / "test_file.json.tmp").exists()


def test_persist_configurations_debounced_sync_fallback(tmp_path, monkeypatch):
    repo = PresetRepository({"hardware_profile": "full"})
    test_file = str(tmp_path / "configurations_test.json")
    monkeypatch.setattr("core.PresetRepository.resolve_configurations_file_path", lambda infos: test_file)

    repo.playlists = ["P1"]
    repo.configurations = {"P1": [{"name": "C1"}]}

    repo.persist_configurations_debounced()
    assert (tmp_path / "configurations_test.json").exists()
    assert repo._pending_snapshot is None


@pytest.mark.anyio
async def test_persist_configurations_debounced_async(tmp_path, monkeypatch):
    import asyncio
    import json
    repo = PresetRepository({"hardware_profile": "full"})
    test_file = str(tmp_path / "configurations_test.json")
    monkeypatch.setattr("core.PresetRepository.resolve_configurations_file_path", lambda infos: test_file)

    repo.playlists = ["P1"]
    repo.configurations = {"P1": [{"name": "initial"}]}

    # Rapid slider movements
    for i in range(5):
        repo.configurations["P1"][0]["name"] = f"val_{i}"
        repo.persist_configurations_debounced(delay_seconds=0.05)

    # File should not exist yet (debounced)
    await asyncio.sleep(0.01)
    assert not (tmp_path / "configurations_test.json").exists()

    # Wait for debounce to complete
    await asyncio.sleep(0.15)
    assert (tmp_path / "configurations_test.json").exists()
    with open(test_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["configurations"]["P1"][0]["name"] == "val_4"
    assert repo._pending_snapshot is None


@pytest.mark.anyio
async def test_persist_app_config_debounced_async(tmp_path, monkeypatch):
    import asyncio
    import json
    repo = PresetRepository({"hardware_profile": "full"})
    test_file = str(tmp_path / "app_config_test.json")
    monkeypatch.setattr(repo, "_resolve_app_config_path", lambda: test_file)

    # Initial write
    repo.persist_app_config_debounced("luminosity", 50, delay_seconds=0.05)
    repo.persist_app_config_debounced("sensibility", 70, delay_seconds=0.05)
    repo.persist_app_config_debounced("luminosity", 80, delay_seconds=0.05)

    await asyncio.sleep(0.15)
    assert (tmp_path / "app_config_test.json").exists()
    with open(test_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["luminosity"] == 80
    assert data["sensibility"] == 70
    assert repo._pending_app_config_snapshot is None


@pytest.mark.anyio
async def test_flush_sync_immediate_persistence(tmp_path, monkeypatch):
    repo = PresetRepository({"hardware_profile": "full"})
    conf_file = str(tmp_path / "configurations_flush.json")
    app_file = str(tmp_path / "app_config_flush.json")
    monkeypatch.setattr("core.PresetRepository.resolve_configurations_file_path", lambda infos: conf_file)
    monkeypatch.setattr(repo, "_resolve_app_config_path", lambda: app_file)

    repo.playlists = ["P1"]
    repo.configurations = {"P1": [{"name": "before_shutdown"}]}

    repo.persist_configurations_debounced(delay_seconds=10.0)
    repo.persist_app_config_debounced("luminosity", 99, delay_seconds=10.0)

    # Immediate shutdown flush
    repo.flush_sync()
    assert (tmp_path / "configurations_flush.json").exists()
    assert (tmp_path / "app_config_flush.json").exists()
    assert repo._pending_snapshot is None
    assert repo._pending_app_config_snapshot is None
    await asyncio.sleep(0.01)
    assert repo._flush_task.cancelled()
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
    # Confirm no orphan tmp files remain
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0


@pytest.mark.anyio
async def test_persist_app_config_debounced_no_disk_reads_during_slider_updates(tmp_path, monkeypatch):
    import asyncio
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


