# ForgeLink Slack Bot

Slack integration for the ForgeLink steel factory IoT platform.

## Overview

The Slack bot provides:

- Slash commands for plant status and alerts
- Real-time alert notifications
- Daily operations summary

## Slash Commands

| Command | Role | Description |
|---------|------|-------------|
| `/plant status` | VIEWER | Active alerts + top 3 critical |
| `/plant alerts [area]` | VIEWER | Active alerts for area |
| `/plant device [id]` | VIEWER | Last telemetry + status |
| `/plant ack [alert_id]` | PLANT_OPERATOR | Acknowledge alert |

## Notification Channels

| Event | Channel |
|-------|---------|
| Critical alert triggered | `#factory-alerts` |
| Device offline | `#factory-alerts` |
| Daily summary (08:00 CAT) | `#factory-ops` |
| Deployment events | `#infra-alerts` |

## Environment Variables

```bash
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_ALERTS_CHANNEL=factory-alerts
SLACK_OPS_CHANNEL=factory-ops
SLACK_INFRA_CHANNEL=infra-alerts

# ForgeLink API
FORGELINK_API_URL=http://forgelink-api:8000
```

## Local Development

```bash
cd slack-bot
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python bot.py
```

## Slack App Setup

1. Create a Slack app at https://api.slack.com/apps
2. Add Bot Token Scopes:
   - `chat:write`
   - `commands`
   - `channels:read`
3. Install to workspace
4. Copy Bot Token and Signing Secret to `.env`
