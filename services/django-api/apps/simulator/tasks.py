"""Celery tasks for steel plant simulation."""
import json
import math
import random
import logging
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Optional

from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.conf import settings
import redis

logger = logging.getLogger(__name__)

# Redis client for publishing OPC-UA value updates
redis_client = redis.Redis.from_url(
    getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/2')
)

# OPC-UA update channel
OPCUA_CHANNEL = 'forgelink:opcua:values'


@shared_task(bind=True, max_retries=3)
def update_device_value(self, device_id: str) -> dict:
    """
    Update a single device's simulated value.

    This task calculates a new value based on the device's simulation mode,
    applies noise/drift, checks thresholds, and publishes to Redis for OPC-UA server.
    """
    from .models import SimulatedDevice, SimulationEvent

    try:
        device = SimulatedDevice.objects.select_related('plc', 'profile').get(id=device_id)
    except SimulatedDevice.DoesNotExist:
        logger.warning(f"Device {device_id} not found")
        return {'error': 'device not found'}

    if device.status != 'running':
        return {'status': 'device not running'}

    # Calculate new value
    new_value = calculate_new_value(device)

    # Apply fault effects
    new_value, quality = apply_fault_effects(device, new_value)

    # Check thresholds and generate events
    check_thresholds(device, new_value)

    # Update device state
    with transaction.atomic():
        device.current_value = Decimal(str(new_value))
        device.quality = quality
        device.sequence_number += 1
        device.messages_sent += 1
        device.last_published_at = timezone.now()
        device.last_value_change_at = timezone.now()
        device.save(update_fields=[
            'current_value', 'quality', 'sequence_number',
            'messages_sent', 'last_published_at', 'last_value_change_at'
        ])

    # Publish to Redis for OPC-UA server
    publish_to_opcua(device, new_value, quality)

    return {
        'device_id': str(device.id),
        'value': float(new_value),
        'quality': quality,
        'sequence': device.sequence_number
    }


def calculate_new_value(device) -> float:
    """Calculate new value based on simulation mode."""
    profile = device.profile
    min_val = float(device.effective_min)
    max_val = float(device.effective_max)
    current = float(device.current_value) if device.current_value else (min_val + max_val) / 2
    target = float(device.target_value) if device.target_value else None

    mode = device.simulation_mode

    if mode == 'constant':
        return target if target else current

    elif mode == 'random_walk':
        # Random walk with drift toward center
        noise = float(device.noise_override or profile.noise_factor)
        step = random.gauss(0, noise * (max_val - min_val))
        new_value = current + step

        # Mean reversion
        center = (min_val + max_val) / 2
        drift = float(profile.drift_rate) * (center - current)
        new_value += drift

    elif mode == 'sine_wave':
        # Sinusoidal variation
        period = device.sine_period_seconds or 60
        amplitude = (max_val - min_val) / 2
        center = (min_val + max_val) / 2
        phase = (timezone.now().timestamp() % period) / period * 2 * math.pi
        new_value = center + amplitude * math.sin(phase)

        # Add noise
        noise = float(device.noise_override or profile.noise_factor)
        new_value += random.gauss(0, noise * amplitude * 0.1)

    elif mode == 'ramp':
        # Linear ramp toward target
        if target:
            rate = float(device.ramp_rate_per_second or 1.0)
            if current < target:
                new_value = min(current + rate, target)
            else:
                new_value = max(current - rate, target)
        else:
            new_value = current

    elif mode == 'step':
        # Step changes at random intervals
        if random.random() < 0.05:  # 5% chance of step
            step_size = (max_val - min_val) * 0.1
            new_value = current + random.choice([-1, 1]) * step_size
        else:
            new_value = current

    elif mode == 'realistic':
        # Process-based realistic simulation
        new_value = simulate_realistic_process(device, current, target, min_val, max_val)

    else:
        new_value = current

    # Clamp to valid range
    new_value = max(min_val, min(max_val, new_value))

    return new_value


def simulate_realistic_process(device, current: float, target: Optional[float],
                                min_val: float, max_val: float) -> float:
    """
    Simulate realistic steel plant process behavior.

    Different sensor types have different characteristics:
    - Temperature: slow changes, thermal inertia
    - Pressure: can change quickly
    - Flow: generally stable
    - Vibration: noisy, can spike
    - Level: slow changes
    """
    profile = device.profile
    sensor_type = profile.sensor_type
    noise = float(device.noise_override or profile.noise_factor)

    if sensor_type == 'temperature':
        # Temperature changes slowly (thermal inertia)
        # EAF temperatures fluctuate around setpoint
        setpoint = target or ((min_val + max_val) * 0.6)  # Higher than center
        inertia = 0.98  # High inertia
        process_noise = random.gauss(0, noise * (max_val - min_val) * 0.5)
        new_value = current * inertia + setpoint * (1 - inertia) + process_noise

    elif sensor_type == 'pressure':
        # Pressure can change more quickly
        setpoint = target or ((min_val + max_val) / 2)
        inertia = 0.9
        process_noise = random.gauss(0, noise * (max_val - min_val))
        new_value = current * inertia + setpoint * (1 - inertia) + process_noise

    elif sensor_type == 'flow':
        # Flow is generally stable with occasional variations
        setpoint = target or ((min_val + max_val) / 2)
        inertia = 0.95
        process_noise = random.gauss(0, noise * (max_val - min_val) * 0.3)
        new_value = current * inertia + setpoint * (1 - inertia) + process_noise

    elif sensor_type == 'vibration':
        # Vibration is noisy with occasional spikes
        base_value = (min_val + max_val) * 0.3
        noise_value = random.gauss(0, noise * (max_val - min_val) * 2)

        # Occasional spikes (5% chance)
        if random.random() < 0.05:
            spike = random.uniform(0.3, 0.7) * (max_val - min_val)
            new_value = base_value + abs(noise_value) + spike
        else:
            new_value = base_value + abs(noise_value)

    elif sensor_type == 'level':
        # Level changes slowly
        setpoint = target or ((min_val + max_val) / 2)
        inertia = 0.99
        process_noise = random.gauss(0, noise * (max_val - min_val) * 0.1)
        new_value = current * inertia + setpoint * (1 - inertia) + process_noise

    elif sensor_type == 'current':
        # Electrode current fluctuates with arc behavior
        setpoint = target or ((min_val + max_val) * 0.7)
        inertia = 0.85
        # Arc instability
        arc_noise = random.gauss(0, noise * (max_val - min_val) * 1.5)
        new_value = current * inertia + setpoint * (1 - inertia) + arc_noise

    elif sensor_type == 'force':
        # Roll force varies with material
        setpoint = target or ((min_val + max_val) / 2)
        inertia = 0.92
        process_noise = random.gauss(0, noise * (max_val - min_val))
        new_value = current * inertia + setpoint * (1 - inertia) + process_noise

    else:
        # Generic behavior
        setpoint = target or ((min_val + max_val) / 2)
        inertia = 0.95
        process_noise = random.gauss(0, noise * (max_val - min_val))
        new_value = current * inertia + setpoint * (1 - inertia) + process_noise

    return new_value


def apply_fault_effects(device, value: float) -> tuple[float, str]:
    """Apply fault effects to the value."""
    fault_type = device.fault_type
    min_val = float(device.effective_min)
    max_val = float(device.effective_max)

    if fault_type == 'none':
        return value, 'good'

    # Check if fault has expired
    if device.fault_end and timezone.now() > device.fault_end:
        device.fault_type = 'none'
        device.save(update_fields=['fault_type'])
        return value, 'good'

    if fault_type == 'stuck':
        # Value doesn't change
        return float(device.current_value or value), 'bad'

    elif fault_type == 'drift':
        # Excessive drift away from normal
        drift_direction = 1 if random.random() > 0.5 else -1
        drift_amount = (max_val - min_val) * 0.01 * drift_direction
        return value + drift_amount, 'uncertain'

    elif fault_type == 'noise':
        # Excessive noise
        noise = random.gauss(0, (max_val - min_val) * 0.2)
        return value + noise, 'uncertain'

    elif fault_type == 'spike':
        # Random spikes
        if random.random() < 0.2:  # 20% chance of spike
            spike = random.choice([-1, 1]) * (max_val - min_val) * random.uniform(0.3, 0.8)
            return max(min_val, min(max_val, value + spike)), 'uncertain'
        return value, 'uncertain'

    elif fault_type == 'dead':
        # Sensor dead - returns zero or last value
        return 0.0, 'bad'

    return value, 'good'


def check_thresholds(device, value: float):
    """Check thresholds and generate events if needed."""
    from .models import SimulationEvent

    profile = device.profile

    if profile.critical_high and value > float(profile.critical_high):
        SimulationEvent.objects.create(
            device=device,
            plc=device.plc,
            event_type='critical_high',
            severity='critical',
            message=f"CRITICAL: {device.name} exceeded critical high threshold",
            value=Decimal(str(value)),
            threshold=profile.critical_high
        )

    elif profile.high_threshold and value > float(profile.high_threshold):
        SimulationEvent.objects.create(
            device=device,
            plc=device.plc,
            event_type='threshold_high',
            severity='high',
            message=f"WARNING: {device.name} exceeded high threshold",
            value=Decimal(str(value)),
            threshold=profile.high_threshold
        )

    elif profile.critical_low and value < float(profile.critical_low):
        SimulationEvent.objects.create(
            device=device,
            plc=device.plc,
            event_type='critical_low',
            severity='critical',
            message=f"CRITICAL: {device.name} below critical low threshold",
            value=Decimal(str(value)),
            threshold=profile.critical_low
        )

    elif profile.low_threshold and value < float(profile.low_threshold):
        SimulationEvent.objects.create(
            device=device,
            plc=device.plc,
            event_type='threshold_low',
            severity='high',
            message=f"WARNING: {device.name} below low threshold",
            value=Decimal(str(value)),
            threshold=profile.low_threshold
        )


def publish_to_opcua(device, value: float, quality: str):
    """Publish value update to Redis for OPC-UA server."""
    message = {
        'device_id': str(device.id),
        'opc_node_id': device.opc_node_id,
        'mqtt_topic': device.mqtt_topic,
        'value': value,
        'quality': quality,
        'timestamp': timezone.now().isoformat(),
        'sequence': device.sequence_number,
        'unit': device.profile.unit,
        'plant': device.plc.plant,
        'area': device.plc.area,
        'line': device.plc.line,
        'cell': device.plc.cell,
    }

    try:
        redis_client.publish(OPCUA_CHANNEL, json.dumps(message))
    except Exception as e:
        logger.error(f"Failed to publish to Redis: {e}")


@shared_task
def run_simulation_cycle():
    """
    Run one simulation cycle for all running devices.

    This task is called periodically by Celery Beat.
    It dispatches individual update_device_value tasks for each running device.
    """
    from .models import SimulatedDevice

    running_devices = SimulatedDevice.objects.filter(
        status='running',
        plc__is_simulating=True
    ).values_list('id', flat=True)

    count = 0
    for device_id in running_devices:
        update_device_value.delay(str(device_id))
        count += 1

    logger.info(f"Dispatched updates for {count} devices")
    return {'devices_updated': count}


@shared_task
def update_plc_heartbeats():
    """Update heartbeats for all online PLCs."""
    from .models import SimulatedPLC

    count = SimulatedPLC.objects.filter(
        is_online=True
    ).update(last_heartbeat=timezone.now())

    logger.info(f"Updated heartbeats for {count} PLCs")
    return {'plcs_updated': count}


@shared_task
def check_expired_faults():
    """Check and clear expired faults."""
    from .models import SimulatedDevice, SimulationEvent

    now = timezone.now()
    expired_devices = SimulatedDevice.objects.filter(
        fault_end__lt=now
    ).exclude(fault_type='none')

    for device in expired_devices:
        SimulationEvent.objects.create(
            device=device,
            plc=device.plc,
            event_type='device_recovery',
            severity='info',
            message=f"{device.name} recovered from {device.fault_type} fault",
            value=device.current_value
        )

    count = expired_devices.update(
        fault_type='none',
        quality='good'
    )

    if count:
        logger.info(f"Cleared {count} expired faults")

    return {'faults_cleared': count}


@shared_task
def cleanup_old_events(days: int = 7):
    """Clean up old simulation events."""
    from .models import SimulationEvent

    cutoff = timezone.now() - timedelta(days=days)
    count, _ = SimulationEvent.objects.filter(
        created_at__lt=cutoff,
        acknowledged=True
    ).delete()

    logger.info(f"Deleted {count} old events")
    return {'events_deleted': count}


@shared_task
def update_session_stats():
    """Update statistics for running sessions."""
    from .models import SimulationSession, SimulatedDevice, SimulationEvent
    from django.db.models import Sum, Count

    running_sessions = SimulationSession.objects.filter(status='running')

    for session in running_sessions:
        # Aggregate device stats
        device_stats = session.devices.aggregate(
            messages=Sum('messages_sent'),
            errors=Sum('error_count')
        )

        # Count events
        event_count = SimulationEvent.objects.filter(session=session).count()

        # Update session
        session.messages_sent = device_stats['messages'] or 0
        session.events_generated = event_count
        session.error_count = device_stats['errors'] or 0
        session.save(update_fields=['messages_sent', 'events_generated', 'error_count', 'updated_at'])

    return {'sessions_updated': running_sessions.count()}


@shared_task
def generate_random_fault():
    """
    Randomly inject a fault into a running device.

    Used to simulate realistic failure scenarios.
    Probability controlled by settings.
    """
    from .models import SimulatedDevice, SimulationEvent

    # Only 0.1% chance per cycle
    if random.random() > 0.001:
        return {'fault_generated': False}

    # Get a random running device
    devices = SimulatedDevice.objects.filter(
        status='running',
        fault_type='none'
    )

    if not devices.exists():
        return {'fault_generated': False}

    device = random.choice(list(devices))
    fault_types = ['stuck', 'drift', 'noise', 'spike']
    fault_type = random.choice(fault_types)

    # Random duration 1-10 minutes
    duration = random.randint(60, 600)
    fault_end = timezone.now() + timedelta(seconds=duration)

    device.fault_type = fault_type
    device.fault_start = timezone.now()
    device.fault_end = fault_end
    device.quality = 'bad' if fault_type in ['stuck', 'dead'] else 'uncertain'
    device.save()

    SimulationEvent.objects.create(
        device=device,
        plc=device.plc,
        event_type='device_fault',
        severity='high',
        message=f"Fault detected: {fault_type} on {device.name}",
        value=device.current_value
    )

    logger.warning(f"Random fault injected: {fault_type} on {device.device_id}")

    return {
        'fault_generated': True,
        'device': str(device.id),
        'fault_type': fault_type,
        'duration': duration
    }
