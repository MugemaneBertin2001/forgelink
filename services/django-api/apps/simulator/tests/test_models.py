"""Tests for simulator models."""

import pytest
from unittest.mock import patch

from apps.simulator.models import (
    DeviceProfile,
    SimulatedDevice,
    SimulatedPLC,
    SimulationEvent,
    SimulationSession,
)


@pytest.mark.django_db
class TestDeviceProfileModel:
    """Tests for DeviceProfile model."""

    def test_create_temperature_profile(self):
        """Test creating a temperature sensor profile."""
        profile = DeviceProfile.objects.create(
            code="thermocouple",
            name="Thermocouple Temperature Sensor",
            measurement_type="temperature",
            unit="celsius",
            min_value=0.0,
            max_value=2000.0,
            typical_value=1550.0,
            noise_factor=0.02,
        )

        assert profile.code == "thermocouple"
        assert profile.measurement_type == "temperature"
        assert profile.typical_value == 1550.0

    def test_create_pressure_profile(self):
        """Test creating a pressure sensor profile."""
        profile = DeviceProfile.objects.create(
            code="pressure-transducer",
            name="Pressure Transducer",
            measurement_type="pressure",
            unit="bar",
            min_value=0.0,
            max_value=100.0,
            typical_value=50.0,
        )

        assert profile.measurement_type == "pressure"
        assert profile.unit == "bar"

    def test_profile_with_anomaly_settings(self):
        """Test profile with anomaly probability settings."""
        profile = DeviceProfile.objects.create(
            code="vibration-sensor",
            name="Vibration Sensor",
            measurement_type="vibration",
            unit="mm/s",
            min_value=0.0,
            max_value=50.0,
            anomaly_probability=0.05,
            anomaly_multiplier=3.0,
        )

        assert profile.anomaly_probability == 0.05
        assert profile.anomaly_multiplier == 3.0


@pytest.mark.django_db
class TestSimulatedPLCModel:
    """Tests for SimulatedPLC model."""

    def test_create_plc(self, area):
        """Test creating a simulated PLC."""
        plc = SimulatedPLC.objects.create(
            code="plc-melt-shop-001",
            name="Melt Shop PLC 1",
            area=area,
            opcua_endpoint="opc.tcp://localhost:4840",
        )

        assert plc.code == "plc-melt-shop-001"
        assert plc.area == area
        assert plc.status == "stopped"

    def test_plc_start_stop(self, area):
        """Test PLC start/stop methods."""
        plc = SimulatedPLC.objects.create(
            code="plc-002",
            name="Test PLC",
            area=area,
        )

        assert plc.status == "stopped"

        # Test status changes (actual start/stop would need Celery)
        plc.status = "running"
        plc.save()
        plc.refresh_from_db()

        assert plc.status == "running"


@pytest.mark.django_db
class TestSimulatedDeviceModel:
    """Tests for SimulatedDevice model."""

    def test_create_simulated_device(self, cell, device_type):
        """Test creating a simulated device."""
        profile = DeviceProfile.objects.create(
            code="temp-profile",
            name="Temperature Profile",
            measurement_type="temperature",
            unit="celsius",
            min_value=0.0,
            max_value=2000.0,
        )

        device = SimulatedDevice.objects.create(
            device_id="sim-temp-001",
            name="Simulated Temperature Sensor",
            cell=cell,
            device_type=device_type,
            profile=profile,
        )

        assert device.device_id == "sim-temp-001"
        assert device.profile == profile

    def test_device_fault_injection(self, cell, device_type):
        """Test device fault injection."""
        profile = DeviceProfile.objects.create(
            code="test-profile",
            name="Test Profile",
            measurement_type="temperature",
            unit="celsius",
            min_value=0.0,
            max_value=100.0,
        )

        device = SimulatedDevice.objects.create(
            device_id="sim-001",
            name="Test Device",
            cell=cell,
            device_type=device_type,
            profile=profile,
        )

        # Inject fault
        device.fault_type = "stuck"
        device.fault_start = "2024-01-01T00:00:00Z"
        device.save()

        assert device.fault_type == "stuck"

    def test_device_value_range(self, cell, device_type):
        """Test device value override range."""
        profile = DeviceProfile.objects.create(
            code="range-profile",
            name="Range Profile",
            measurement_type="temperature",
            unit="celsius",
            min_value=0.0,
            max_value=100.0,
        )

        device = SimulatedDevice.objects.create(
            device_id="sim-002",
            name="Range Test Device",
            cell=cell,
            device_type=device_type,
            profile=profile,
            override_min=10.0,
            override_max=90.0,
        )

        assert device.override_min == 10.0
        assert device.override_max == 90.0


@pytest.mark.django_db
class TestSimulationSessionModel:
    """Tests for SimulationSession model."""

    def test_create_session(self):
        """Test creating a simulation session."""
        session = SimulationSession.objects.create(
            name="Test Session",
            description="Testing simulation",
            update_interval_ms=1000,
        )

        assert session.name == "Test Session"
        assert session.status == "stopped"

    def test_session_lifecycle(self):
        """Test session lifecycle states."""
        session = SimulationSession.objects.create(
            name="Lifecycle Test",
        )

        # Initial state
        assert session.status == "stopped"

        # Start
        session.status = "running"
        session.save()
        assert session.status == "running"

        # Pause
        session.status = "paused"
        session.save()
        assert session.status == "paused"

        # Stop
        session.status = "stopped"
        session.save()
        assert session.status == "stopped"


@pytest.mark.django_db
class TestSimulationEventModel:
    """Tests for SimulationEvent model."""

    def test_create_event(self, cell, device_type):
        """Test creating a simulation event."""
        profile = DeviceProfile.objects.create(
            code="event-profile",
            name="Event Profile",
            measurement_type="temperature",
            unit="celsius",
            min_value=0.0,
            max_value=100.0,
        )

        device = SimulatedDevice.objects.create(
            device_id="event-device",
            name="Event Device",
            cell=cell,
            device_type=device_type,
            profile=profile,
        )

        session = SimulationSession.objects.create(name="Event Session")

        event = SimulationEvent.objects.create(
            session=session,
            device=device,
            event_type="fault_injected",
            details={"fault_type": "stuck", "value": 50.0},
        )

        assert event.event_type == "fault_injected"
        assert event.details["fault_type"] == "stuck"
