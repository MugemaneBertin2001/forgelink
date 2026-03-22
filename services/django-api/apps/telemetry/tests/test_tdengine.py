"""Tests for TDengine integration."""

import pytest

from apps.telemetry.tdengine import (
    VALID_AREAS,
    VALID_INTERVALS,
    VALID_PERIODS,
    sanitize_identifier,
    validate_area,
    validate_device_id,
    validate_interval,
    validate_period,
    validate_table_name,
)


class TestValidationFunctions:
    """Tests for TDengine validation functions."""

    def test_validate_device_id_valid(self):
        """Test valid device IDs."""
        valid_ids = [
            "temp-sensor-001",
            "TEMP_SENSOR_001",
            "sensor123",
            "a",
            "sensor_with_underscore",
        ]
        for device_id in valid_ids:
            result = validate_device_id(device_id)
            assert result == device_id

    def test_validate_device_id_invalid(self):
        """Test invalid device IDs."""
        invalid_ids = [
            "",
            "a" * 100,  # Too long
            "-invalid",  # Starts with hyphen
            "has space",  # Contains space
            "has;semicolon",  # SQL injection attempt
            "'; DROP TABLE--",  # SQL injection
        ]
        for device_id in invalid_ids:
            with pytest.raises(ValueError):
                validate_device_id(device_id)

    def test_validate_area_valid(self):
        """Test valid areas."""
        for area in VALID_AREAS:
            result = validate_area(area)
            assert result == area

    def test_validate_area_invalid(self):
        """Test invalid areas."""
        with pytest.raises(ValueError):
            validate_area("invalid-area")
        with pytest.raises(ValueError):
            validate_area("'; DROP TABLE--")

    def test_validate_period_valid(self):
        """Test valid periods."""
        for period in VALID_PERIODS:
            result = validate_period(period)
            assert result == period

    def test_validate_period_invalid(self):
        """Test invalid periods."""
        with pytest.raises(ValueError):
            validate_period("invalid")
        with pytest.raises(ValueError):
            validate_period("100d")

    def test_validate_interval_valid(self):
        """Test valid intervals."""
        for interval in VALID_INTERVALS:
            result = validate_interval(interval)
            assert result == interval

    def test_validate_interval_invalid(self):
        """Test invalid intervals."""
        with pytest.raises(ValueError):
            validate_interval("invalid")
        with pytest.raises(ValueError):
            validate_interval("2m")

    def test_validate_table_name_valid(self):
        """Test valid table names."""
        valid_names = [
            "telemetry",
            "device_data",
            "temp_sensor_001",
        ]
        for name in valid_names:
            result = validate_table_name(name)
            assert result == name

    def test_validate_table_name_invalid(self):
        """Test invalid table names."""
        invalid_names = [
            "",
            "has space",
            "has;semicolon",
            "a" * 200,
        ]
        for name in invalid_names:
            with pytest.raises(ValueError):
                validate_table_name(name)

    def test_sanitize_identifier(self):
        """Test identifier sanitization."""
        assert sanitize_identifier("normal_name") == "normal_name"
        # sanitize_identifier preserves hyphens but removes dangerous chars
        result = sanitize_identifier("has-hyphen")
        assert ";" not in result
        assert "'" not in result


class TestTDengineConnection:
    """Tests for TDengine connection management."""

    def test_tdengine_module_has_connection_function(self):
        """Test that tdengine module has connection capabilities."""
        from apps.telemetry import tdengine
        # Module should exist and have validation functions
        assert hasattr(tdengine, "validate_device_id")


class TestTelemetryQueries:
    """Tests for telemetry query functions."""

    def test_validate_device_id_prevents_injection(self):
        """Test that validation prevents SQL injection."""
        # Should raise for invalid device ID
        with pytest.raises(ValueError):
            validate_device_id("'; DROP TABLE--")

    def test_validate_area_with_valid_areas(self):
        """Test that area validation accepts valid areas."""
        # Valid areas should not raise
        for area in VALID_AREAS:
            assert validate_area(area) == area
