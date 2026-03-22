"""Tests for assets models."""

from datetime import timedelta

from django.utils import timezone

import pytest

from apps.assets.models import Area, Cell, Device, DeviceType, Line, Plant


@pytest.mark.django_db
class TestPlantModel:
    """Tests for Plant model."""

    def test_create_plant(self):
        """Test creating a plant."""
        plant = Plant.objects.create(
            code="test-plant",
            name="Test Steel Plant",
            description="A test plant",
            timezone="Africa/Kigali",
        )

        assert plant.code == "test-plant"
        assert plant.name == "Test Steel Plant"
        assert plant.is_active is True
        assert str(plant) == "Test Steel Plant"

    def test_plant_unique_code(self, plant):
        """Test that plant codes must be unique."""
        with pytest.raises(Exception):
            Plant.objects.create(
                code=plant.code,
                name="Duplicate Plant",
            )

    def test_plant_with_location(self):
        """Test plant with GPS coordinates."""
        plant = Plant.objects.create(
            code="located-plant",
            name="Located Plant",
            latitude=-1.9403,
            longitude=29.8739,
            address="Kigali, Rwanda",
        )

        assert plant.latitude == -1.9403
        assert plant.longitude == 29.8739

    def test_plant_commissioned_at(self):
        """Test plant with commissioned date."""
        commissioned = timezone.now() - timedelta(days=365)
        plant = Plant.objects.create(
            code="old-plant",
            name="Old Plant",
            commissioned_at=commissioned,
        )

        assert plant.commissioned_at == commissioned


@pytest.mark.django_db
class TestAreaModel:
    """Tests for Area model."""

    def test_create_area(self, plant):
        """Test creating an area."""
        area = Area.objects.create(
            plant=plant,
            code="melt-shop",
            name="Melt Shop",
            description="Electric arc furnace area",
            area_type="melt_shop",
        )

        assert area.code == "melt-shop"
        assert area.plant == plant
        assert area.area_type == "melt_shop"

    def test_area_sequence(self, plant):
        """Test area sequencing."""
        area1 = Area.objects.create(
            plant=plant,
            code="area-1",
            name="Area 1",
            sequence=1,
        )
        area2 = Area.objects.create(
            plant=plant,
            code="area-2",
            name="Area 2",
            sequence=2,
        )

        assert area1.sequence < area2.sequence

    def test_area_types(self, plant):
        """Test valid area types."""
        for area_type in [
            "melt_shop",
            "continuous_casting",
            "rolling_mill",
            "finishing",
        ]:
            area = Area.objects.create(
                plant=plant,
                code=f"area-{area_type}",
                name=f"Area {area_type}",
                area_type=area_type,
            )
            assert area.area_type == area_type


@pytest.mark.django_db
class TestLineModel:
    """Tests for Line model."""

    def test_create_line(self, area):
        """Test creating a line."""
        line = Line.objects.create(
            area=area,
            code="eaf-1",
            name="Electric Arc Furnace 1",
            description="Primary EAF",
        )

        assert line.code == "eaf-1"
        assert line.area == area

    def test_line_capacity(self, area):
        """Test line with design capacity."""
        line = Line.objects.create(
            area=area,
            code="caster-1",
            name="Continuous Caster 1",
            design_capacity=150.0,
            capacity_unit="tons/hour",
        )

        assert line.design_capacity == 150.0
        assert line.capacity_unit == "tons/hour"


@pytest.mark.django_db
class TestCellModel:
    """Tests for Cell model."""

    def test_create_cell(self, line):
        """Test creating a cell."""
        cell = Cell.objects.create(
            line=line,
            code="electrode-a",
            name="Electrode A",
            description="First electrode",
        )

        assert cell.code == "electrode-a"
        assert cell.line == line


@pytest.mark.django_db
class TestDeviceTypeModel:
    """Tests for DeviceType model."""

    def test_create_device_type(self):
        """Test creating a device type."""
        device_type = DeviceType.objects.create(
            code="thermocouple",
            name="Thermocouple",
            description="High temperature sensor",
            default_unit="celsius",
            typical_min=0.0,
            typical_max=2000.0,
        )

        assert device_type.code == "thermocouple"
        assert device_type.typical_max == 2000.0

    def test_device_type_icon(self):
        """Test device type with icon."""
        device_type = DeviceType.objects.create(
            code="vibration",
            name="Vibration Sensor",
            icon="vibration_icon",
        )

        assert device_type.icon == "vibration_icon"


@pytest.mark.django_db
class TestDeviceModel:
    """Tests for Device model."""

    def test_create_device(self, cell, device_type):
        """Test creating a device."""
        device = Device.objects.create(
            cell=cell,
            device_type=device_type,
            device_id="temp-001",
            name="Temperature Sensor 001",
            unit="celsius",
        )

        assert device.device_id == "temp-001"
        assert device.cell == cell
        assert device.device_type == device_type

    def test_device_thresholds(self, cell, device_type):
        """Test device threshold configuration."""
        device = Device.objects.create(
            cell=cell,
            device_type=device_type,
            device_id="temp-002",
            name="Temperature Sensor 002",
            warning_low=100.0,
            warning_high=1500.0,
            critical_low=50.0,
            critical_high=1600.0,
        )

        assert device.warning_low == 100.0
        assert device.critical_high == 1600.0

    def test_device_status(self, cell, device_type):
        """Test device status values."""
        device = Device.objects.create(
            cell=cell,
            device_type=device_type,
            device_id="temp-003",
            name="Temperature Sensor 003",
            status="online",
        )

        assert device.status == "online"

    def test_device_calibration(self, cell, device_type):
        """Test device calibration tracking."""
        last_cal = timezone.now() - timedelta(days=30)
        next_cal = timezone.now() + timedelta(days=335)

        device = Device.objects.create(
            cell=cell,
            device_type=device_type,
            device_id="temp-004",
            name="Temperature Sensor 004",
            last_calibration=last_cal,
            next_calibration=next_cal,
        )

        assert device.last_calibration == last_cal
        assert device.next_calibration == next_cal

    def test_device_tags(self, cell, device_type):
        """Test device tags as JSON field."""
        device = Device.objects.create(
            cell=cell,
            device_type=device_type,
            device_id="temp-005",
            name="Temperature Sensor 005",
            tags={"location": "furnace-top", "priority": "high"},
        )

        assert device.tags["location"] == "furnace-top"
        assert device.tags["priority"] == "high"

    def test_device_update_status(self, device):
        """Test updating device status."""
        device.status = "offline"
        device.save()
        device.refresh_from_db()

        assert device.status == "offline"

    def test_device_sampling_rate(self, cell, device_type):
        """Test device sampling rate configuration."""
        device = Device.objects.create(
            cell=cell,
            device_type=device_type,
            device_id="temp-006",
            name="Fast Sensor",
            sampling_rate_ms=100,
        )

        assert device.sampling_rate_ms == 100

    def test_device_hierarchy_navigation(self, device):
        """Test navigating device hierarchy."""
        # Device -> Cell -> Line -> Area -> Plant
        assert device.cell is not None
        assert device.cell.line is not None
        assert device.cell.line.area is not None
        assert device.cell.line.area.plant is not None
