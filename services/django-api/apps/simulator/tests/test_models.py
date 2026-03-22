"""Tests for simulator models."""

import pytest

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
            name="Thermocouple Temperature Sensor",
            sensor_type="temperature",
            unit="celsius",
            min_value=0.0,
            max_value=2000.0,
            noise_factor=0.02,
        )

        assert profile.name == "Thermocouple Temperature Sensor"
        assert profile.sensor_type == "temperature"
        assert profile.unit == "celsius"

    def test_create_pressure_profile(self):
        """Test creating a pressure sensor profile."""
        profile = DeviceProfile.objects.create(
            name="Pressure Transducer",
            sensor_type="pressure",
            unit="bar",
            min_value=0.0,
            max_value=100.0,
        )

        assert profile.sensor_type == "pressure"
        assert profile.unit == "bar"

    def test_profile_with_threshold_settings(self):
        """Test profile with threshold settings."""
        profile = DeviceProfile.objects.create(
            name="Vibration Sensor",
            sensor_type="vibration",
            unit="mm/s",
            min_value=0.0,
            max_value=50.0,
            high_threshold=30.0,
            critical_high=45.0,
        )

        assert profile.high_threshold == 30.0
        assert profile.critical_high == 45.0


@pytest.mark.django_db
class TestSimulatedPLCModel:
    """Tests for SimulatedPLC model."""

    def test_create_plc(self):
        """Test creating a simulated PLC."""
        plc = SimulatedPLC.objects.create(
            name="Melt Shop PLC 1",
            area="melt-shop",
            line="eaf-1",
        )

        assert plc.name == "Melt Shop PLC 1"
        assert plc.area == "melt-shop"
        assert plc.is_online is False

    def test_plc_online_status(self):
        """Test PLC online/offline status."""
        plc = SimulatedPLC.objects.create(
            name="Test PLC",
            area="melt-shop",
            line="eaf-1",
        )

        assert plc.is_online is False
        assert plc.is_simulating is False

        # Test status changes
        plc.is_online = True
        plc.save()
        plc.refresh_from_db()

        assert plc.is_online is True


@pytest.mark.django_db
class TestSimulatedDeviceModel:
    """Tests for SimulatedDevice model."""

    def test_create_simulated_device(self):
        """Test creating a simulated device."""
        profile = DeviceProfile.objects.create(
            name="Temperature Profile",
            sensor_type="temperature",
            unit="celsius",
            min_value=0.0,
            max_value=2000.0,
        )

        plc = SimulatedPLC.objects.create(
            name="Test PLC",
            area="melt-shop",
            line="eaf-1",
        )

        device = SimulatedDevice.objects.create(
            name="Simulated Temperature Sensor",
            device_id="sim-temp-001",
            plc=plc,
            profile=profile,
        )

        assert device.device_id == "sim-temp-001"
        assert device.profile == profile

    def test_device_status(self):
        """Test device status values."""
        profile = DeviceProfile.objects.create(
            name="Test Profile",
            sensor_type="temperature",
            unit="celsius",
            min_value=0.0,
            max_value=100.0,
        )

        plc = SimulatedPLC.objects.create(
            name="Test PLC",
            area="melt-shop",
            line="eaf-1",
        )

        device = SimulatedDevice.objects.create(
            name="Test Device",
            device_id="sim-001",
            plc=plc,
            profile=profile,
        )

        # Default status
        assert device.status == "offline"

        # Update status
        device.status = "online"
        device.save()
        device.refresh_from_db()

        assert device.status == "online"


@pytest.mark.django_db
class TestSimulationSessionModel:
    """Tests for SimulationSession model."""

    def test_create_session(self):
        """Test creating a simulation session."""
        session = SimulationSession.objects.create(
            name="Test Session",
            description="Testing simulation",
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
        session.start()
        assert session.status == "running"

        # Stop
        session.stop()
        assert session.status == "stopped"


@pytest.mark.django_db
class TestSimulationEventModel:
    """Tests for SimulationEvent model."""

    def test_create_event(self):
        """Test creating a simulation event."""
        profile = DeviceProfile.objects.create(
            name="Event Profile",
            sensor_type="temperature",
            unit="celsius",
            min_value=0.0,
            max_value=100.0,
        )

        plc = SimulatedPLC.objects.create(
            name="Event PLC",
            area="melt-shop",
            line="eaf-1",
        )

        device = SimulatedDevice.objects.create(
            name="Event Device",
            device_id="event-device",
            plc=plc,
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
