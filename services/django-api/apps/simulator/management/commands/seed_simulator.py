"""
Management command to seed the simulator with realistic steel plant devices.

Creates ~68 devices across 4 production areas matching the steel manufacturing process:
- Melt Shop (EAF, LRF)
- Continuous Casting
- Rolling Mill
- Finishing
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from decimal import Decimal

from apps.simulator.models import DeviceProfile, SimulatedPLC, SimulatedDevice


class Command(BaseCommand):
    help = 'Seed the simulator with realistic steel plant devices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing simulator data before seeding',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing simulator data...')
            SimulatedDevice.objects.all().delete()
            SimulatedPLC.objects.all().delete()
            DeviceProfile.objects.all().delete()

        self.stdout.write('Creating device profiles...')
        profiles = self.create_profiles()

        self.stdout.write('Creating PLCs and devices...')
        with transaction.atomic():
            self.create_melt_shop(profiles)
            self.create_continuous_casting(profiles)
            self.create_rolling_mill(profiles)
            self.create_finishing(profiles)

        total_plcs = SimulatedPLC.objects.count()
        total_devices = SimulatedDevice.objects.count()

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {total_plcs} PLCs and {total_devices} devices'
        ))

    def create_profiles(self) -> dict:
        """Create sensor profile templates."""
        profiles = {}

        # Temperature profiles
        profiles['eaf_temp'] = DeviceProfile.objects.get_or_create(
            name='EAF Temperature',
            defaults={
                'sensor_type': 'temperature',
                'description': 'Electric Arc Furnace molten steel temperature',
                'min_value': Decimal('1400'),
                'max_value': Decimal('1700'),
                'unit': 'celsius',
                'noise_factor': Decimal('0.005'),
                'drift_rate': Decimal('0.0001'),
                'response_time_ms': 500,
                'dead_band': Decimal('1.0'),
                'low_threshold': Decimal('1500'),
                'high_threshold': Decimal('1620'),
                'critical_low': Decimal('1450'),
                'critical_high': Decimal('1680'),
            }
        )[0]

        profiles['lrf_temp'] = DeviceProfile.objects.get_or_create(
            name='LRF Temperature',
            defaults={
                'sensor_type': 'temperature',
                'description': 'Ladle Refining Furnace temperature',
                'min_value': Decimal('1500'),
                'max_value': Decimal('1650'),
                'unit': 'celsius',
                'noise_factor': Decimal('0.003'),
                'drift_rate': Decimal('0.00005'),
                'response_time_ms': 500,
                'dead_band': Decimal('0.5'),
                'low_threshold': Decimal('1530'),
                'high_threshold': Decimal('1610'),
                'critical_low': Decimal('1510'),
                'critical_high': Decimal('1640'),
            }
        )[0]

        profiles['tundish_temp'] = DeviceProfile.objects.get_or_create(
            name='Tundish Temperature',
            defaults={
                'sensor_type': 'temperature',
                'description': 'Continuous casting tundish temperature',
                'min_value': Decimal('1520'),
                'max_value': Decimal('1580'),
                'unit': 'celsius',
                'noise_factor': Decimal('0.002'),
                'drift_rate': Decimal('0.00002'),
                'response_time_ms': 300,
                'dead_band': Decimal('0.3'),
                'low_threshold': Decimal('1530'),
                'high_threshold': Decimal('1565'),
                'critical_low': Decimal('1525'),
                'critical_high': Decimal('1575'),
            }
        )[0]

        profiles['reheat_temp'] = DeviceProfile.objects.get_or_create(
            name='Reheat Furnace Temperature',
            defaults={
                'sensor_type': 'temperature',
                'description': 'Billet reheating furnace zone temperature',
                'min_value': Decimal('1000'),
                'max_value': Decimal('1250'),
                'unit': 'celsius',
                'noise_factor': Decimal('0.008'),
                'drift_rate': Decimal('0.0002'),
                'response_time_ms': 1000,
                'dead_band': Decimal('2.0'),
                'low_threshold': Decimal('1080'),
                'high_threshold': Decimal('1200'),
                'critical_high': Decimal('1230'),
            }
        )[0]

        profiles['strip_temp'] = DeviceProfile.objects.get_or_create(
            name='Strip Temperature',
            defaults={
                'sensor_type': 'temperature',
                'description': 'Rolling mill strip/billet temperature',
                'min_value': Decimal('800'),
                'max_value': Decimal('1100'),
                'unit': 'celsius',
                'noise_factor': Decimal('0.01'),
                'drift_rate': Decimal('0.0003'),
                'response_time_ms': 200,
                'dead_band': Decimal('2.0'),
                'low_threshold': Decimal('850'),
                'high_threshold': Decimal('1050'),
            }
        )[0]

        profiles['offgas_temp'] = DeviceProfile.objects.get_or_create(
            name='Off-gas Temperature',
            defaults={
                'sensor_type': 'temperature',
                'description': 'EAF off-gas duct temperature',
                'min_value': Decimal('200'),
                'max_value': Decimal('1200'),
                'unit': 'celsius',
                'noise_factor': Decimal('0.02'),
                'drift_rate': Decimal('0.0005'),
                'response_time_ms': 100,
                'dead_band': Decimal('5.0'),
                'high_threshold': Decimal('1000'),
                'critical_high': Decimal('1100'),
            }
        )[0]

        # Current sensor (EAF electrodes)
        profiles['electrode_current'] = DeviceProfile.objects.get_or_create(
            name='Electrode Current',
            defaults={
                'sensor_type': 'current',
                'description': 'EAF electrode arc current',
                'min_value': Decimal('20'),
                'max_value': Decimal('100'),
                'unit': 'kA',
                'noise_factor': Decimal('0.03'),
                'drift_rate': Decimal('0.001'),
                'response_time_ms': 50,
                'dead_band': Decimal('0.5'),
                'high_threshold': Decimal('80'),
                'critical_high': Decimal('90'),
            }
        )[0]

        # Pressure sensors
        profiles['hydraulic_pressure'] = DeviceProfile.objects.get_or_create(
            name='Hydraulic Pressure',
            defaults={
                'sensor_type': 'pressure',
                'description': 'Hydraulic system pressure',
                'min_value': Decimal('0'),
                'max_value': Decimal('350'),
                'unit': 'bar',
                'noise_factor': Decimal('0.005'),
                'drift_rate': Decimal('0.00005'),
                'response_time_ms': 20,
                'dead_band': Decimal('0.5'),
                'low_threshold': Decimal('180'),
                'high_threshold': Decimal('300'),
                'critical_high': Decimal('330'),
            }
        )[0]

        profiles['cooling_pressure'] = DeviceProfile.objects.get_or_create(
            name='Cooling Water Pressure',
            defaults={
                'sensor_type': 'pressure',
                'description': 'Cooling water system pressure',
                'min_value': Decimal('0'),
                'max_value': Decimal('10'),
                'unit': 'bar',
                'noise_factor': Decimal('0.01'),
                'drift_rate': Decimal('0.0001'),
                'response_time_ms': 50,
                'dead_band': Decimal('0.1'),
                'low_threshold': Decimal('3'),
                'high_threshold': Decimal('8'),
            }
        )[0]

        # Flow sensors
        profiles['cooling_flow'] = DeviceProfile.objects.get_or_create(
            name='Cooling Water Flow',
            defaults={
                'sensor_type': 'flow',
                'description': 'Cooling water flow rate',
                'min_value': Decimal('0'),
                'max_value': Decimal('1000'),
                'unit': 'L/min',
                'noise_factor': Decimal('0.008'),
                'drift_rate': Decimal('0.0001'),
                'response_time_ms': 100,
                'dead_band': Decimal('5'),
                'low_threshold': Decimal('200'),
                'high_threshold': Decimal('900'),
            }
        )[0]

        profiles['gas_flow'] = DeviceProfile.objects.get_or_create(
            name='Gas Flow',
            defaults={
                'sensor_type': 'flow',
                'description': 'Process gas flow rate',
                'min_value': Decimal('0'),
                'max_value': Decimal('5000'),
                'unit': 'Nm3/h',
                'noise_factor': Decimal('0.01'),
                'drift_rate': Decimal('0.0002'),
                'response_time_ms': 200,
                'dead_band': Decimal('10'),
                'high_threshold': Decimal('4500'),
            }
        )[0]

        # Level sensors
        profiles['mold_level'] = DeviceProfile.objects.get_or_create(
            name='Mold Level',
            defaults={
                'sensor_type': 'level',
                'description': 'Continuous caster mold steel level',
                'min_value': Decimal('-10'),
                'max_value': Decimal('10'),
                'unit': 'mm',
                'noise_factor': Decimal('0.02'),
                'drift_rate': Decimal('0.00001'),
                'response_time_ms': 10,
                'dead_band': Decimal('0.1'),
                'low_threshold': Decimal('-5'),
                'high_threshold': Decimal('5'),
                'critical_low': Decimal('-8'),
                'critical_high': Decimal('8'),
            }
        )[0]

        profiles['tundish_level'] = DeviceProfile.objects.get_or_create(
            name='Tundish Level',
            defaults={
                'sensor_type': 'level',
                'description': 'Tundish steel level',
                'min_value': Decimal('0'),
                'max_value': Decimal('100'),
                'unit': '%',
                'noise_factor': Decimal('0.005'),
                'drift_rate': Decimal('0.00005'),
                'response_time_ms': 100,
                'dead_band': Decimal('0.5'),
                'low_threshold': Decimal('30'),
                'high_threshold': Decimal('90'),
                'critical_low': Decimal('20'),
            }
        )[0]

        # Vibration sensors
        profiles['motor_vibration'] = DeviceProfile.objects.get_or_create(
            name='Motor Vibration',
            defaults={
                'sensor_type': 'vibration',
                'description': 'Motor/gearbox vibration velocity',
                'min_value': Decimal('0'),
                'max_value': Decimal('15'),
                'unit': 'mm/s',
                'noise_factor': Decimal('0.05'),
                'drift_rate': Decimal('0.0001'),
                'response_time_ms': 10,
                'dead_band': Decimal('0.1'),
                'high_threshold': Decimal('4.5'),
                'critical_high': Decimal('7.1'),
            }
        )[0]

        profiles['oscillation'] = DeviceProfile.objects.get_or_create(
            name='Mold Oscillation',
            defaults={
                'sensor_type': 'vibration',
                'description': 'Mold oscillation amplitude',
                'min_value': Decimal('0'),
                'max_value': Decimal('10'),
                'unit': 'mm',
                'noise_factor': Decimal('0.02'),
                'drift_rate': Decimal('0.00005'),
                'response_time_ms': 5,
                'dead_band': Decimal('0.05'),
                'low_threshold': Decimal('2'),
                'high_threshold': Decimal('8'),
            }
        )[0]

        # Force sensors
        profiles['roll_force'] = DeviceProfile.objects.get_or_create(
            name='Roll Force',
            defaults={
                'sensor_type': 'force',
                'description': 'Rolling stand roll separating force',
                'min_value': Decimal('0'),
                'max_value': Decimal('30000'),
                'unit': 'kN',
                'noise_factor': Decimal('0.01'),
                'drift_rate': Decimal('0.0002'),
                'response_time_ms': 50,
                'dead_band': Decimal('50'),
                'high_threshold': Decimal('25000'),
                'critical_high': Decimal('28000'),
            }
        )[0]

        # Speed sensors
        profiles['casting_speed'] = DeviceProfile.objects.get_or_create(
            name='Casting Speed',
            defaults={
                'sensor_type': 'speed',
                'description': 'Continuous casting strand speed',
                'min_value': Decimal('0'),
                'max_value': Decimal('5'),
                'unit': 'm/min',
                'noise_factor': Decimal('0.005'),
                'drift_rate': Decimal('0.00002'),
                'response_time_ms': 100,
                'dead_band': Decimal('0.01'),
                'low_threshold': Decimal('0.5'),
                'high_threshold': Decimal('3.5'),
            }
        )[0]

        profiles['roll_speed'] = DeviceProfile.objects.get_or_create(
            name='Roll Speed',
            defaults={
                'sensor_type': 'speed',
                'description': 'Rolling stand roll speed',
                'min_value': Decimal('0'),
                'max_value': Decimal('500'),
                'unit': 'rpm',
                'noise_factor': Decimal('0.003'),
                'drift_rate': Decimal('0.00005'),
                'response_time_ms': 50,
                'dead_band': Decimal('0.5'),
            }
        )[0]

        # Weight sensor
        profiles['bundle_weight'] = DeviceProfile.objects.get_or_create(
            name='Bundle Weight',
            defaults={
                'sensor_type': 'weight',
                'description': 'Finished bundle weight',
                'min_value': Decimal('0'),
                'max_value': Decimal('5000'),
                'unit': 'kg',
                'noise_factor': Decimal('0.001'),
                'drift_rate': Decimal('0.00001'),
                'response_time_ms': 500,
                'dead_band': Decimal('1'),
            }
        )[0]

        return profiles

    def create_melt_shop(self, profiles: dict):
        """Create Melt Shop PLCs and devices."""

        # EAF-1 PLC
        eaf1_plc = SimulatedPLC.objects.get_or_create(
            name='EAF-1 Controller',
            plant='steel-plant-kigali',
            area='melt-shop',
            line='eaf-1',
            defaults={
                'plc_type': 'siemens_s7',
                'description': 'Electric Arc Furnace 1 main controller',
                'scan_rate_ms': 500,
                'publish_rate_ms': 1000,
            }
        )[0]

        # EAF Temperature sensors (3 electrodes)
        for i, electrode in enumerate(['electrode-a', 'electrode-b', 'electrode-c'], 1):
            SimulatedDevice.objects.get_or_create(
                plc=eaf1_plc,
                device_id=f'temp-sensor-{i:03d}',
                defaults={
                    'name': f'EAF-1 {electrode.title()} Temperature',
                    'profile': profiles['eaf_temp'],
                    'description': f'Temperature sensor for {electrode}',
                    'simulation_mode': 'realistic',
                }
            )
            SimulatedDevice.objects.get_or_create(
                plc=eaf1_plc,
                device_id=f'current-sensor-{i:03d}',
                defaults={
                    'name': f'EAF-1 {electrode.title()} Current',
                    'profile': profiles['electrode_current'],
                    'description': f'Arc current sensor for {electrode}',
                    'simulation_mode': 'realistic',
                }
            )

        # EAF Vibration sensors
        for i, location in enumerate(['motor', 'gearbox', 'tilting-mechanism'], 1):
            SimulatedDevice.objects.get_or_create(
                plc=eaf1_plc,
                device_id=f'vibration-{i:03d}',
                defaults={
                    'name': f'EAF-1 {location.title()} Vibration',
                    'profile': profiles['motor_vibration'],
                    'description': f'Vibration sensor for {location}',
                    'simulation_mode': 'realistic',
                }
            )

        # Off-gas system
        offgas_plc = SimulatedPLC.objects.get_or_create(
            name='Off-gas Controller',
            plant='steel-plant-kigali',
            area='melt-shop',
            line='offgas',
            cell='main-duct',
            defaults={
                'plc_type': 'siemens_s7',
                'description': 'Off-gas extraction system controller',
                'scan_rate_ms': 200,
                'publish_rate_ms': 500,
            }
        )[0]

        SimulatedDevice.objects.get_or_create(
            plc=offgas_plc,
            device_id='temp-sensor-020',
            defaults={
                'name': 'Off-gas Duct Temperature',
                'profile': profiles['offgas_temp'],
                'simulation_mode': 'realistic',
            }
        )
        SimulatedDevice.objects.get_or_create(
            plc=offgas_plc,
            device_id='flow-meter-001',
            defaults={
                'name': 'Off-gas Flow Rate',
                'profile': profiles['gas_flow'],
                'simulation_mode': 'realistic',
            }
        )

        # LRF-1 PLC
        lrf1_plc = SimulatedPLC.objects.get_or_create(
            name='LRF-1 Controller',
            plant='steel-plant-kigali',
            area='melt-shop',
            line='lrf-1',
            cell='ladle',
            defaults={
                'plc_type': 'siemens_s7',
                'description': 'Ladle Refining Furnace 1 controller',
                'scan_rate_ms': 500,
                'publish_rate_ms': 1000,
            }
        )[0]

        SimulatedDevice.objects.get_or_create(
            plc=lrf1_plc,
            device_id='temp-sensor-010',
            defaults={
                'name': 'LRF-1 Steel Temperature',
                'profile': profiles['lrf_temp'],
                'simulation_mode': 'realistic',
            }
        )
        SimulatedDevice.objects.get_or_create(
            plc=lrf1_plc,
            device_id='level-sensor-001',
            defaults={
                'name': 'LRF-1 Alloy Bin Level',
                'profile': profiles['tundish_level'],
                'simulation_mode': 'realistic',
            }
        )

        self.stdout.write(f'  Created Melt Shop: {eaf1_plc.devices.count() + offgas_plc.devices.count() + lrf1_plc.devices.count()} devices')

    def create_continuous_casting(self, profiles: dict):
        """Create Continuous Casting PLCs and devices."""

        # Caster-1 Tundish
        tundish_plc = SimulatedPLC.objects.get_or_create(
            name='Tundish Controller',
            plant='steel-plant-kigali',
            area='continuous-casting',
            line='caster-1',
            cell='tundish',
            defaults={
                'plc_type': 'siemens_s7',
                'description': 'Caster 1 tundish controller',
                'scan_rate_ms': 200,
                'publish_rate_ms': 500,
            }
        )[0]

        SimulatedDevice.objects.get_or_create(
            plc=tundish_plc,
            device_id='temp-sensor-030',
            defaults={
                'name': 'Tundish Steel Temperature',
                'profile': profiles['tundish_temp'],
                'simulation_mode': 'realistic',
            }
        )
        SimulatedDevice.objects.get_or_create(
            plc=tundish_plc,
            device_id='level-sensor-010',
            defaults={
                'name': 'Tundish Level',
                'profile': profiles['tundish_level'],
                'simulation_mode': 'realistic',
            }
        )
        SimulatedDevice.objects.get_or_create(
            plc=tundish_plc,
            device_id='flow-meter-010',
            defaults={
                'name': 'Tundish Flow Rate',
                'profile': profiles['cooling_flow'],
                'simulation_mode': 'realistic',
            }
        )

        # Mold
        mold_plc = SimulatedPLC.objects.get_or_create(
            name='Mold Controller',
            plant='steel-plant-kigali',
            area='continuous-casting',
            line='caster-1',
            cell='mold',
            defaults={
                'plc_type': 'siemens_s7',
                'description': 'Caster 1 mold controller',
                'scan_rate_ms': 100,
                'publish_rate_ms': 200,
            }
        )[0]

        SimulatedDevice.objects.get_or_create(
            plc=mold_plc,
            device_id='level-sensor-011',
            defaults={
                'name': 'Mold Level',
                'profile': profiles['mold_level'],
                'simulation_mode': 'realistic',
            }
        )
        SimulatedDevice.objects.get_or_create(
            plc=mold_plc,
            device_id='temp-sensor-031',
            defaults={
                'name': 'Mold Copper Temperature',
                'profile': profiles['strip_temp'],
                'simulation_mode': 'realistic',
            }
        )
        SimulatedDevice.objects.get_or_create(
            plc=mold_plc,
            device_id='oscillation-sensor-001',
            defaults={
                'name': 'Mold Oscillation',
                'profile': profiles['oscillation'],
                'simulation_mode': 'realistic',
            }
        )
        SimulatedDevice.objects.get_or_create(
            plc=mold_plc,
            device_id='speed-sensor-001',
            defaults={
                'name': 'Casting Speed',
                'profile': profiles['casting_speed'],
                'simulation_mode': 'realistic',
            }
        )

        # Secondary cooling zones
        for zone in range(1, 5):
            cooling_plc = SimulatedPLC.objects.get_or_create(
                name=f'Cooling Zone {zone} Controller',
                plant='steel-plant-kigali',
                area='continuous-casting',
                line='caster-1',
                cell=f'cooling-zone-{zone}',
                defaults={
                    'plc_type': 'generic',
                    'description': f'Secondary cooling zone {zone}',
                    'scan_rate_ms': 500,
                    'publish_rate_ms': 1000,
                }
            )[0]

            SimulatedDevice.objects.get_or_create(
                plc=cooling_plc,
                device_id=f'flow-meter-{20+zone:03d}',
                defaults={
                    'name': f'Zone {zone} Cooling Flow',
                    'profile': profiles['cooling_flow'],
                    'simulation_mode': 'realistic',
                }
            )
            SimulatedDevice.objects.get_or_create(
                plc=cooling_plc,
                device_id=f'pressure-{zone:03d}',
                defaults={
                    'name': f'Zone {zone} Cooling Pressure',
                    'profile': profiles['cooling_pressure'],
                    'simulation_mode': 'realistic',
                }
            )

        self.stdout.write(f'  Created Continuous Casting: 16 devices')

    def create_rolling_mill(self, profiles: dict):
        """Create Rolling Mill PLCs and devices."""

        # Reheat Furnace
        furnace_plc = SimulatedPLC.objects.get_or_create(
            name='Reheat Furnace Controller',
            plant='steel-plant-kigali',
            area='rolling-mill',
            line='reheat-furnace',
            defaults={
                'plc_type': 'allen_bradley',
                'description': 'Billet reheating furnace controller',
                'scan_rate_ms': 1000,
                'publish_rate_ms': 2000,
            }
        )[0]

        for zone in range(1, 4):
            SimulatedDevice.objects.get_or_create(
                plc=furnace_plc,
                device_id=f'temp-sensor-{40+zone:03d}',
                defaults={
                    'name': f'Furnace Zone {zone} Temperature',
                    'profile': profiles['reheat_temp'],
                    'simulation_mode': 'realistic',
                }
            )

        # Roughing stands
        roughing_plc = SimulatedPLC.objects.get_or_create(
            name='Roughing Mill Controller',
            plant='steel-plant-kigali',
            area='rolling-mill',
            line='roughing',
            defaults={
                'plc_type': 'allen_bradley',
                'description': 'Roughing mill stands controller',
                'scan_rate_ms': 200,
                'publish_rate_ms': 500,
            }
        )[0]

        for stand in range(1, 4):
            SimulatedDevice.objects.get_or_create(
                plc=roughing_plc,
                device_id=f'roll-force-{stand:03d}',
                defaults={
                    'name': f'Stand {stand} Roll Force',
                    'profile': profiles['roll_force'],
                    'simulation_mode': 'realistic',
                }
            )
            SimulatedDevice.objects.get_or_create(
                plc=roughing_plc,
                device_id=f'vibration-{10+stand:03d}',
                defaults={
                    'name': f'Stand {stand} Motor Vibration',
                    'profile': profiles['motor_vibration'],
                    'simulation_mode': 'realistic',
                }
            )
            SimulatedDevice.objects.get_or_create(
                plc=roughing_plc,
                device_id=f'speed-{stand:03d}',
                defaults={
                    'name': f'Stand {stand} Roll Speed',
                    'profile': profiles['roll_speed'],
                    'simulation_mode': 'realistic',
                }
            )

        # Finishing stands
        finishing_plc = SimulatedPLC.objects.get_or_create(
            name='Finishing Mill Controller',
            plant='steel-plant-kigali',
            area='rolling-mill',
            line='finishing',
            defaults={
                'plc_type': 'allen_bradley',
                'description': 'Finishing mill stands controller',
                'scan_rate_ms': 100,
                'publish_rate_ms': 250,
            }
        )[0]

        for stand in range(4, 7):
            SimulatedDevice.objects.get_or_create(
                plc=finishing_plc,
                device_id=f'roll-force-{stand:03d}',
                defaults={
                    'name': f'Stand {stand} Roll Force',
                    'profile': profiles['roll_force'],
                    'simulation_mode': 'realistic',
                }
            )
            SimulatedDevice.objects.get_or_create(
                plc=finishing_plc,
                device_id=f'strip-temp-{stand:03d}',
                defaults={
                    'name': f'Stand {stand} Strip Temperature',
                    'profile': profiles['strip_temp'],
                    'simulation_mode': 'realistic',
                }
            )

        # Cooling bed
        cooling_plc = SimulatedPLC.objects.get_or_create(
            name='Cooling Bed Controller',
            plant='steel-plant-kigali',
            area='rolling-mill',
            line='cooling-bed',
            defaults={
                'plc_type': 'generic',
                'description': 'Cooling bed controller',
                'scan_rate_ms': 2000,
                'publish_rate_ms': 5000,
            }
        )[0]

        for section in range(1, 4):
            SimulatedDevice.objects.get_or_create(
                plc=cooling_plc,
                device_id=f'temp-sensor-{50+section:03d}',
                defaults={
                    'name': f'Section {section} Temperature',
                    'profile': profiles['strip_temp'],
                    'simulation_mode': 'realistic',
                }
            )

        self.stdout.write(f'  Created Rolling Mill: 24 devices')

    def create_finishing(self, profiles: dict):
        """Create Finishing area PLCs and devices."""

        # Inspection station
        inspection_plc = SimulatedPLC.objects.get_or_create(
            name='Inspection Station Controller',
            plant='steel-plant-kigali',
            area='finishing',
            line='inspection',
            cell='station-1',
            defaults={
                'plc_type': 'generic',
                'description': 'Quality inspection station',
                'scan_rate_ms': 500,
                'publish_rate_ms': 1000,
            }
        )[0]

        SimulatedDevice.objects.get_or_create(
            plc=inspection_plc,
            device_id='ultrasonic-001',
            defaults={
                'name': 'Ultrasonic Defect Detector',
                'profile': profiles['motor_vibration'],  # Using vibration as proxy
                'simulation_mode': 'realistic',
            }
        )
        SimulatedDevice.objects.get_or_create(
            plc=inspection_plc,
            device_id='eddy-current-001',
            defaults={
                'name': 'Eddy Current Tester',
                'profile': profiles['motor_vibration'],
                'simulation_mode': 'realistic',
            }
        )

        # Bundling
        bundling_plc = SimulatedPLC.objects.get_or_create(
            name='Bundling Machine Controller',
            plant='steel-plant-kigali',
            area='finishing',
            line='bundling',
            cell='machine-1',
            defaults={
                'plc_type': 'generic',
                'description': 'Product bundling machine',
                'scan_rate_ms': 1000,
                'publish_rate_ms': 2000,
            }
        )[0]

        SimulatedDevice.objects.get_or_create(
            plc=bundling_plc,
            device_id='counter-001',
            defaults={
                'name': 'Product Counter',
                'profile': profiles['roll_speed'],  # Using speed as proxy
                'simulation_mode': 'step',
            }
        )
        SimulatedDevice.objects.get_or_create(
            plc=bundling_plc,
            device_id='weight-scale-001',
            defaults={
                'name': 'Bundle Weight Scale',
                'profile': profiles['bundle_weight'],
                'simulation_mode': 'realistic',
            }
        )
        SimulatedDevice.objects.get_or_create(
            plc=bundling_plc,
            device_id='hydraulic-001',
            defaults={
                'name': 'Bundling Press Pressure',
                'profile': profiles['hydraulic_pressure'],
                'simulation_mode': 'realistic',
            }
        )

        self.stdout.write(f'  Created Finishing: 5 devices')
