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
