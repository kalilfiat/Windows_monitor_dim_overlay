from monitor_dim.models import AppMode, MonitorPreference, Settings


def test_settings_round_trip_preserves_user_configuration():
    settings = Settings(
        enabled=False,
        mode=AppMode.ACTIVE_WINDOW,
        opacity=0.77,
        excluded_apps=["obs64.exe"],
        monitors={"DISPLAY2": MonitorPreference(True, 0.63)},
    )

    restored = Settings.from_dict(settings.to_dict())

    assert restored.enabled is False
    assert restored.mode is AppMode.ACTIVE_WINDOW
    assert restored.opacity == 0.77
    assert restored.excluded_apps == ["obs64.exe"]
    assert restored.monitors["DISPLAY2"].opacity == 0.63


def test_invalid_values_are_clamped_and_normalized():
    restored = Settings.from_dict(
        {
            "opacity": 3,
            "restore_delay_ms": -50,
            "fade_duration_ms": 80_000,
            "mode": "unknown",
            "dim_color": "invalid",
            "excluded_apps": [" OBS64.EXE ", "obs64.exe", ""],
        }
    )

    assert restored.opacity == 0.98
    assert restored.restore_delay_ms == 0
    assert restored.fade_duration_ms == 2000
    assert restored.mode is AppMode.CURSOR
    assert restored.dim_color == "#020711"
    assert restored.excluded_apps == ["obs64.exe"]


def test_profile_updates_behavioral_fields():
    settings = Settings()

    settings.apply_profile("Trabajo")

    assert settings.mode is AppMode.ACTIVE_WINDOW
    assert settings.active_profile == "Trabajo"
    assert settings.opacity == settings.profiles["Trabajo"].opacity


def test_schema_two_migration_disables_surprising_fullscreen_pause():
    migrated = Settings.from_dict(
        {
            "schema_version": 2,
            "pause_fullscreen": True,
            "profiles": {"Trabajo": {"pause_fullscreen": True}},
        }
    )
    current = Settings.from_dict(
        {
            "schema_version": 5,
            "pause_fullscreen": True,
            "dim_primary": False,
            "show_settings_on_startup": False,
        }
    )

    assert migrated.schema_version == 5
    assert migrated.pause_fullscreen is False
    assert migrated.profiles["Trabajo"].pause_fullscreen is False
    assert migrated.dim_primary is True
    assert current.pause_fullscreen is True
    assert current.dim_primary is False
    assert current.show_settings_on_startup is False


def test_primary_monitor_is_eligible_by_default():
    assert Settings().dim_primary is True


def test_settings_window_opens_by_default_and_migrates_old_config():
    assert Settings().show_settings_on_startup is True
    assert Settings.from_dict({"schema_version": 4, "show_settings_on_startup": False}).show_settings_on_startup is True
