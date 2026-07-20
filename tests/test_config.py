import json

from monitor_dim.config import ConfigStore
from monitor_dim.models import AppMode, Settings


def test_config_store_saves_and_loads_atomically(tmp_path):
    store = ConfigStore(base_dir=tmp_path / "config")
    settings = Settings(mode=AppMode.MANUAL, opacity=0.74)

    assert store.save(settings) is True
    restored = store.load()

    assert restored.mode is AppMode.MANUAL
    assert restored.opacity == 0.74
    assert not store.path.with_suffix(".tmp").exists()


def test_legacy_opacity_file_is_migrated(tmp_path):
    legacy = tmp_path / "monitor_dim_overlay_config.json"
    legacy.write_text(json.dumps({"opacity": 0.7}), encoding="utf-8")
    store = ConfigStore(base_dir=tmp_path / "new", legacy_path=legacy)

    restored = store.load()

    assert restored.opacity == 0.7
    assert store.path.exists()


def test_invalid_json_falls_back_to_defaults(tmp_path):
    store = ConfigStore(base_dir=tmp_path)
    store.path.write_text("not json", encoding="utf-8")

    restored = store.load()

    assert restored == Settings()
