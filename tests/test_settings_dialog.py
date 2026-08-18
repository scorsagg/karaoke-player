"""Unit tests for source_code/dialogs/settings_dialog.py"""

import os

import pytest
from PySide6.QtWidgets import QComboBox, QLineEdit

from source_code.dialogs import settings_dialog as dialog_module
from source_code.dialogs.settings_dialog import SettingsDialog


class FakeSettingsManager:
    def __init__(self, **overrides):
        self.settings = {
            "base_directory": "/media/library",
            "download_directory": "/media/downloads",
            "ffmpeg_path": "/usr/bin/ffmpeg",
            "ffprobe_path": "/usr/bin/ffprobe",
            "ytdlp_path": "/usr/bin/yt-dlp",
            "measurement_mode": "dB Output (dBFS)",
            "auto_reduce_threshold": 90,
        }
        self.settings.update(overrides)
        self.saves = 0

    def save_settings(self):
        self.saves += 1


@pytest.fixture
def manager():
    return FakeSettingsManager()


@pytest.fixture
def dialog(qapp, manager, monkeypatch):
    """Build the dialog with accept() stubbed so no modal event loop is needed."""
    accepted = []
    monkeypatch.setattr(SettingsDialog, "accept", lambda self: accepted.append(True))
    widget = SettingsDialog(parent=None, settings_manager=manager)
    widget.accepted_calls = accepted
    yield widget
    widget.deleteLater()


@pytest.fixture
def file_dialog(monkeypatch):
    """Capture browse dialog usage and drive its return value."""
    state = {"directory": "", "file": "", "calls": []}

    class FakeFileDialog:
        @staticmethod
        def getExistingDirectory(parent, caption, directory):
            state["calls"].append(("directory", directory))
            return state["directory"]

        @staticmethod
        def getOpenFileName(parent, caption, directory, filters):
            state["calls"].append(("file", directory))
            return state["file"], ""

    monkeypatch.setattr(dialog_module, "QFileDialog", FakeFileDialog)
    return state


class TestConstruction:
    def test_settings_are_copied_not_shared(self, dialog, manager):
        dialog.temp_states["base_directory"] = "/changed"

        assert manager.settings["base_directory"] == "/media/library"

    def test_one_sidebar_entry_and_page_per_schema_section(self, dialog):
        assert dialog.settings_list.count() == len(dialog.schema)
        assert dialog.settings_stack.count() == len(dialog.schema)
        assert dialog.settings_list.currentRow() == 0

    def test_every_schema_key_gets_an_input_field(self, dialog):
        expected = {prop["key"] for props in dialog.schema.values() for prop in props}

        assert set(dialog.display_fields) == expected

    def test_text_fields_are_prefilled_from_settings(self, dialog):
        assert isinstance(dialog.display_fields["ffmpeg_path"], QLineEdit)
        assert dialog.display_fields["ffmpeg_path"].text() == "/usr/bin/ffmpeg"
        assert dialog.display_fields["auto_reduce_threshold"].text() == "90"

    def test_select_fields_use_a_combo_box_with_schema_options(self, dialog):
        combo = dialog.display_fields["measurement_mode"]

        assert isinstance(combo, QComboBox)
        assert [combo.itemText(i) for i in range(combo.count())] == [
            "dB Output (dBFS)",
            "SPL Estimate (Room)",
        ]
        assert combo.currentText() == "dB Output (dBFS)"

    def test_missing_setting_falls_back_to_first_option(self, qapp):
        manager = FakeSettingsManager()
        del manager.settings["measurement_mode"]

        widget = SettingsDialog(parent=None, settings_manager=manager)

        assert widget.display_fields["measurement_mode"].currentText() == "dB Output (dBFS)"
        widget.deleteLater()

    def test_missing_path_setting_renders_an_empty_field(self, qapp):
        manager = FakeSettingsManager()
        del manager.settings["ffmpeg_path"]

        widget = SettingsDialog(parent=None, settings_manager=manager)

        assert widget.display_fields["ffmpeg_path"].text() == ""
        widget.deleteLater()

    def test_sidebar_selection_switches_the_visible_page(self, dialog):
        dialog.settings_list.setCurrentRow(2)

        assert dialog.settings_stack.currentIndex() == 2


class TestBrowse:
    def test_directory_browse_updates_field_and_pending_state(self, dialog, file_dialog):
        file_dialog["directory"] = "/media/new/library/"

        dialog.handle_browse("base_directory", "directory")

        expected = os.path.normpath("/media/new/library/")
        assert dialog.display_fields["base_directory"].text() == expected
        assert dialog.temp_states["base_directory"] == expected
        assert file_dialog["calls"] == [("directory", "/media/library")]

    def test_file_browse_uses_the_open_file_dialog(self, dialog, file_dialog):
        file_dialog["file"] = "/opt/ffmpeg/bin/ffmpeg"

        dialog.handle_browse("ffmpeg_path", "file")

        assert dialog.display_fields["ffmpeg_path"].text() == os.path.normpath("/opt/ffmpeg/bin/ffmpeg")
        assert file_dialog["calls"] == [("file", "/usr/bin/ffmpeg")]

    def test_cancelled_browse_leaves_the_field_untouched(self, dialog, file_dialog):
        dialog.handle_browse("ffmpeg_path", "file")

        assert dialog.display_fields["ffmpeg_path"].text() == "/usr/bin/ffmpeg"


class TestAcceptChanges:
    def test_edited_values_are_persisted(self, dialog, manager):
        dialog.display_fields["base_directory"].setText("  /media/other  ")
        dialog.display_fields["measurement_mode"].setCurrentText("SPL Estimate (Room)")

        dialog.accept_changes()

        assert manager.settings["base_directory"] == "/media/other"
        assert manager.settings["measurement_mode"] == "SPL Estimate (Room)"
        assert manager.saves == 1
        assert dialog.accepted_calls == [True]

    @pytest.mark.parametrize(
        "entered, expected", [("75", 75), ("0", 0), ("-5", 0), ("250", 100), ("abc", 80), ("", 80)]
    )
    def test_threshold_is_coerced_and_clamped(self, dialog, manager, entered, expected):
        dialog.display_fields["auto_reduce_threshold"].setText(entered)

        dialog.accept_changes()

        assert manager.settings["auto_reduce_threshold"] == expected

    def test_unrelated_settings_are_preserved(self, qapp, monkeypatch):
        monkeypatch.setattr(SettingsDialog, "accept", lambda self: None)
        manager = FakeSettingsManager(theme="dark")
        widget = SettingsDialog(parent=None, settings_manager=manager)

        widget.accept_changes()

        assert manager.settings["theme"] == "dark"
        widget.deleteLater()
