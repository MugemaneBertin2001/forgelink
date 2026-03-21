"""
Django management command to run the Kafka telemetry consumer.

Usage:
    python manage.py consume_telemetry
    python manage.py consume_telemetry --topics telemetry.melt-shop telemetry.rolling-mill
    python manage.py consume_telemetry --batch-size 1000 --batch-timeout 2000
"""

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.telemetry.kafka_consumer import EventKafkaConsumer, TelemetryKafkaConsumer

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the Kafka telemetry consumer to ingest data into TDengine"

    def add_arguments(self, parser):
        parser.add_argument(
            "--type",
            type=str,
            choices=["telemetry", "events", "both"],
            default="telemetry",
            help="Consumer type: telemetry, events, or both (default: telemetry)",
        )
        parser.add_argument(
            "--bootstrap-servers",
            type=str,
            default=None,
            help="Kafka bootstrap servers (default: from settings)",
        )
        parser.add_argument(
            "--group-id", type=str, default=None, help="Kafka consumer group ID"
        )
        parser.add_argument(
            "--topics",
            nargs="+",
            type=str,
            default=None,
            help="Kafka topics to consume from",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for TDengine writes (default: 500)",
        )
        parser.add_argument(
            "--batch-timeout",
            type=int,
            default=1000,
            help="Batch timeout in milliseconds (default: 1000)",
        )

    def handle(self, *args, **options):
        consumer_type = options["type"]
        bootstrap_servers = options["bootstrap_servers"] or getattr(
            settings, "KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"
        )

        self.stdout.write(self.style.SUCCESS(f"Starting {consumer_type} consumer..."))
        self.stdout.write(f"Bootstrap servers: {bootstrap_servers}")

        try:
            if consumer_type == "telemetry":
                self._run_telemetry_consumer(options, bootstrap_servers)
            elif consumer_type == "events":
                self._run_event_consumer(options, bootstrap_servers)
            elif consumer_type == "both":
                self._run_both_consumers(options, bootstrap_servers)

        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nReceived interrupt, shutting down...")
            )
        except Exception as e:
            raise CommandError(f"Consumer failed: {e}")

    def _run_telemetry_consumer(self, options, bootstrap_servers):
        """Run telemetry consumer."""
        topics = options["topics"] or [
            "telemetry.melt-shop",
            "telemetry.continuous-casting",
            "telemetry.rolling-mill",
            "telemetry.finishing",
        ]

        consumer = TelemetryKafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=options["group_id"] or "forgelink-telemetry-consumer",
            topics=topics,
            batch_size=options["batch_size"],
            batch_timeout_ms=options["batch_timeout"],
        )

        self.stdout.write(f'Topics: {", ".join(topics)}')
        self.stdout.write(f'Batch size: {options["batch_size"]}')
        self.stdout.write(f'Batch timeout: {options["batch_timeout"]}ms')
        self.stdout.write(self.style.SUCCESS("Consumer started, press Ctrl+C to stop"))

        consumer.start()

    def _run_event_consumer(self, options, bootstrap_servers):
        """Run event consumer."""
        topics = options["topics"] or ["events.all", "status.all"]

        consumer = EventKafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=options["group_id"] or "forgelink-event-consumer",
            topics=topics,
        )

        self.stdout.write(f'Topics: {", ".join(topics)}')
        self.stdout.write(
            self.style.SUCCESS("Event consumer started, press Ctrl+C to stop")
        )

        consumer.start()

    def _run_both_consumers(self, options, bootstrap_servers):
        """Run both consumers in separate threads."""
        import threading

        telemetry_consumer = TelemetryKafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id=options["group_id"] or "forgelink-telemetry-consumer",
            batch_size=options["batch_size"],
            batch_timeout_ms=options["batch_timeout"],
        )

        event_consumer = EventKafkaConsumer(
            bootstrap_servers=bootstrap_servers,
            group_id="forgelink-event-consumer",
        )

        telemetry_thread = threading.Thread(
            target=telemetry_consumer.start, name="telemetry-consumer", daemon=True
        )
        event_thread = threading.Thread(
            target=event_consumer.start, name="event-consumer", daemon=True
        )

        telemetry_thread.start()
        event_thread.start()

        self.stdout.write(
            self.style.SUCCESS("Both consumers started, press Ctrl+C to stop")
        )

        try:
            # Wait for threads
            telemetry_thread.join()
            event_thread.join()
        except KeyboardInterrupt:
            telemetry_consumer.stop()
            event_consumer.stop()
            telemetry_thread.join(timeout=5)
            event_thread.join(timeout=5)
