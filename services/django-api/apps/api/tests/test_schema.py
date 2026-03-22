"""Tests for GraphQL schema."""

import pytest

from graphene.test import Client

from apps.api.schema import schema


@pytest.mark.django_db
class TestGraphQLSchema:
    """Tests for GraphQL schema queries and mutations."""

    @pytest.fixture
    def graphql_client(self):
        """Create GraphQL test client."""
        return Client(schema)

    def test_hello_query(self, graphql_client):
        """Test basic hello query."""
        query = """
            query {
                hello
            }
        """
        result = graphql_client.execute(query)

        assert "errors" not in result or result["errors"] is None
        assert result["data"]["hello"] == "Welcome to ForgeLink Steel Factory IoT"

    def test_version_query(self, graphql_client):
        """Test version query."""
        query = """
            query {
                version
            }
        """
        result = graphql_client.execute(query)

        assert "errors" not in result or result["errors"] is None
        assert result["data"]["version"] == "1.0.0"

    def test_plants_query(self, graphql_client, plant):
        """Test plants query."""
        query = """
            query {
                plants {
                    code
                    name
                    isActive
                }
            }
        """
        result = graphql_client.execute(query)

        assert "errors" not in result or result["errors"] is None
        assert len(result["data"]["plants"]) >= 1

    def test_plant_query(self, graphql_client, plant):
        """Test single plant query."""
        query = f"""
            query {{
                plant(code: "{plant.code}") {{
                    code
                    name
                    description
                }}
            }}
        """
        result = graphql_client.execute(query)

        assert "errors" not in result or result["errors"] is None
        assert result["data"]["plant"]["code"] == plant.code

    def test_devices_query(self, graphql_client, device):
        """Test devices query."""
        query = """
            query {
                devices(limit: 10) {
                    deviceId
                    name
                    status
                }
            }
        """
        result = graphql_client.execute(query)

        assert "errors" not in result or result["errors"] is None
        assert len(result["data"]["devices"]) >= 1

    def test_device_query(self, graphql_client, device):
        """Test single device query."""
        query = f"""
            query {{
                device(deviceId: "{device.device_id}") {{
                    deviceId
                    name
                    unit
                }}
            }}
        """
        result = graphql_client.execute(query)

        assert "errors" not in result or result["errors"] is None
        assert result["data"]["device"]["deviceId"] == device.device_id

    def test_alert_rules_query(self, graphql_client, alert_rule):
        """Test alert rules query."""
        query = """
            query {
                alertRules {
                    name
                    severity
                    isActive
                }
            }
        """
        result = graphql_client.execute(query)

        assert "errors" not in result or result["errors"] is None
        assert len(result["data"]["alertRules"]) >= 1

    def test_alerts_query(self, graphql_client, alert):
        """Test alerts query."""
        query = """
            query {
                alerts(limit: 10) {
                    severity
                    status
                    message
                }
            }
        """
        result = graphql_client.execute(query)

        assert "errors" not in result or result["errors"] is None
        assert len(result["data"]["alerts"]) >= 1

    def test_active_alerts_query(self, graphql_client, alert):
        """Test active alerts query."""
        query = """
            query {
                activeAlerts {
                    severity
                    status
                }
            }
        """
        result = graphql_client.execute(query)

        assert "errors" not in result or result["errors"] is None
        # All returned alerts should be active
        for a in result["data"]["activeAlerts"]:
            assert a["status"] == "active"

    def test_alert_stats_query(self, graphql_client, alert):
        """Test alert statistics query."""
        query = """
            query {
                alertStats
            }
        """
        result = graphql_client.execute(query)

        assert "errors" not in result or result["errors"] is None
        stats = result["data"]["alertStats"]
        assert "total" in stats
        assert "active" in stats

    def test_acknowledge_alert_mutation(self, graphql_client, alert):
        """Test acknowledge alert mutation."""
        mutation = f"""
            mutation {{
                acknowledgeAlert(alertId: "{alert.id}", user: "test@forgelink.local") {{
                    success
                    error
                    alert {{
                        status
                    }}
                }}
            }}
        """
        result = graphql_client.execute(mutation)

        assert "errors" not in result or result["errors"] is None
        assert result["data"]["acknowledgeAlert"]["success"] is True

    def test_resolve_alert_mutation(self, graphql_client, alert):
        """Test resolve alert mutation."""
        # First acknowledge
        alert.acknowledge("test@forgelink.local")

        mutation = f"""
            mutation {{
                resolveAlert(alertId: "{alert.id}", user: "test@forgelink.local") {{
                    success
                    error
                    alert {{
                        status
                    }}
                }}
            }}
        """
        result = graphql_client.execute(mutation)

        assert "errors" not in result or result["errors"] is None
        assert result["data"]["resolveAlert"]["success"] is True

    def test_acknowledge_nonexistent_alert(self, graphql_client):
        """Test acknowledging nonexistent alert."""
        mutation = """
            mutation {
                acknowledgeAlert(alertId: "00000000-0000-0000-0000-000000000000", user: "test") {
                    success
                    error
                }
            }
        """
        result = graphql_client.execute(mutation)

        assert "errors" not in result or result["errors"] is None
        assert result["data"]["acknowledgeAlert"]["success"] is False
        assert "not found" in result["data"]["acknowledgeAlert"]["error"]

    def test_bulk_acknowledge_mutation(self, graphql_client, device, alert_rule):
        """Test bulk acknowledge mutation."""
        from apps.alerts.models import Alert
        import json

        alerts = [
            Alert.objects.create(
                device=device,
                rule=alert_rule,
                alert_type="threshold_high",
                severity="high",
                message=f"Alert {i}",
            )
            for i in range(3)
        ]
        alert_ids = [str(a.id) for a in alerts]

        mutation = f"""
            mutation {{
                bulkAcknowledgeAlerts(alertIds: {json.dumps(alert_ids)}, user: "test") {{
                    success
                    acknowledgedCount
                    errors
                }}
            }}
        """

        result = graphql_client.execute(mutation)

        assert "errors" not in result or result["errors"] is None
        assert result["data"]["bulkAcknowledgeAlerts"]["acknowledgedCount"] == 3
