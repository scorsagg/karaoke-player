"""Unit tests for source_code/widgets/audio_meter.py"""

import pytest

from source_code.widgets.audio_meter import AudioLevelMeter


@pytest.fixture
def meter(qapp):
    widget = AudioLevelMeter()
    yield widget
    widget.deleteLater()


class TestDefaults:
    def test_starts_silent(self, meter):
        assert meter.db_level == -80.0
        assert meter.level_percent == 0.0
        assert meter.measurement_mode == "dB Output (dBFS)"
        assert meter.auto_reduce_threshold_spl == 90

    def test_has_constrained_geometry(self, meter):
        assert meter.height() == 30
        assert meter.minimumWidth() == 150
        assert meter.maximumWidth() == 200


class TestSetLevel:
    def test_first_update_is_smoothed_from_silence(self, meter):
        meter.set_level(0.0)

        assert meter.db_level == pytest.approx(-64.0)
        assert meter.level_percent == pytest.approx(20.0)

    def test_repeated_updates_converge_towards_target(self, meter):
        for _ in range(200):
            meter.set_level(-20.0)

        assert meter.db_level == pytest.approx(-20.0, abs=0.1)
        assert meter.level_percent == pytest.approx(75.0, abs=0.2)

    @pytest.mark.parametrize("value", [10.0, 1000.0])
    def test_values_above_zero_dbfs_are_clamped(self, meter, value):
        meter.set_level(value)

        assert meter.db_level == pytest.approx(-64.0)

    def test_values_below_floor_are_clamped(self, meter):
        meter.set_level(-500.0)

        assert meter.db_level == pytest.approx(-80.0)
        assert meter.level_percent == pytest.approx(0.0)

    def test_update_level_is_an_alias(self, meter):
        meter.update_level(0.0)

        assert meter.db_level == pytest.approx(-64.0)


class TestSplConversion:
    def test_silence_maps_to_floor_spl(self, meter):
        assert meter.get_approximate_spl() == pytest.approx(60.0)

    def test_full_scale_maps_to_ninety_spl(self, meter):
        meter.level_percent = 100.0

        assert meter.get_approximate_spl() == pytest.approx(90.0)


class TestConfiguration:
    def test_set_measurement_mode(self, meter):
        meter.set_measurement_mode("SPL Estimate (Room)")

        assert meter.measurement_mode == "SPL Estimate (Room)"

    def test_threshold_accepts_numeric_strings(self, meter):
        meter.set_auto_reduce_threshold("85")

        assert meter.auto_reduce_threshold_spl == 85

    def test_threshold_falls_back_on_invalid_input(self, meter):
        meter.set_auto_reduce_threshold("loud")

        assert meter.auto_reduce_threshold_spl == 90


class TestPaintEvent:
    @pytest.mark.parametrize("db_value", [-80.0, -40.0, -10.0, 0.0])
    def test_paints_at_every_level_band(self, meter, db_value):
        meter.set_level(db_value)
        meter.level_percent = ((max(-80.0, min(0.0, db_value)) + 80.0) / 80.0) * 100.0

        meter.render(meter.grab())

    @pytest.mark.parametrize("mode", ["dB Output (dBFS)", "SPL Estimate (Room)"])
    def test_paints_in_both_measurement_modes(self, meter, mode):
        meter.set_measurement_mode(mode)

        meter.render(meter.grab())

    @pytest.mark.parametrize("threshold", [40, 90, 200])
    def test_threshold_marker_stays_within_meter(self, meter, threshold):
        meter.set_auto_reduce_threshold(threshold)

        meter.render(meter.grab())
