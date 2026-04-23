# ForgeLink Mobile — Install Guide (Android)

**Last updated:** 2026-04-23
**Minimum:** Android 10 (API 29).
**iOS:** not yet distributed. Tracked as a v2.0.0/v2.1.0 item in
[`ROADMAP.md`](../../ROADMAP.md); requires an Apple Developer account.

This guide is for reviewers who want to install the ForgeLink mobile
app against the public demo stack. The APK is signed with the
ForgeLink release keystore, attached as an asset on every GitHub
release under this repo. Two install paths are documented below —
pick the one that matches how you use Android.

---

## Path 1 — `adb` sideload (technical reviewers)

Prerequisites: a USB cable, the Android SDK platform-tools installed
on your laptop, and developer mode enabled on the phone.

```bash
# 1. Download the latest APK from the release page
curl -L -o forgelink.apk \
  "https://github.com/MugemaneBertin2001/forgelink/releases/latest/download/app-release.apk"

# 2. Verify signature chain (optional but recommended)
apksigner verify --verbose forgelink.apk

# 3. Install over USB
adb install forgelink.apk
```

If you get `INSTALL_PARSE_FAILED_NO_CERTIFICATES`, you downloaded an
unsigned debug build. The release pipeline signs every tagged release
— make sure you grabbed an asset from a tagged release, not a CI
artefact from a merge commit.

---

## Path 2 — Unknown-sources sideload (phone-only)

1. On your phone, visit:
   `https://github.com/MugemaneBertin2001/forgelink/releases/latest`
2. Tap the `app-release.apk` asset to download.
3. Android prompts to allow installs from your browser — grant it.
4. Open the downloaded file from your notification tray or the
   Downloads app.
5. Confirm the install.

The first launch asks for notification permission (needed for the
Socket.IO alert push path) and network access.

---

## Connect to the demo

On the login screen, use the documented demo credentials (see the
[README Quick Start](../../README.md#quick-start)). Default API base:
`https://forgelink.mugemanebertin.com` (public demo, planned for
v1.1.0). During local development the app can also point at
`http://localhost:8000` — see
[`services/flutter-app/lib/core/config/app_config.dart`](../../services/flutter-app/lib/core/config/app_config.dart)
for the override.

Expected flow once logged in:

1. Dashboard populates within a few seconds with live telemetry from
   the simulator (EAF electrode temp, tundish level, strip
   temperature, etc.).
2. The bell icon shows recent alerts — tap an active one to
   acknowledge.
3. Toggling the simulator to inject a fault (from the web admin)
   triggers a push notification on the phone within 1–2 seconds via
   the Socket.IO namespace.

---

## Troubleshooting

**"App not installed" / Play Protect warning.** The release keystore
is not registered with Play Protect; this is expected for sideloaded
builds. Tap "Install anyway". If your organisation's device policy
blocks this, use Path 1 with `adb` instead.

**Can't log in / "Network error".** The demo URL is live 24/7 at
`forgelink.mugemanebertin.com`. If the app shows a network error,
check that your phone is not filtering `*.mugemanebertin.com` via a
captive-portal DNS.

**Notifications don't arrive.** Push delivery depends on the
foreground service plus the OS letting Socket.IO keep a persistent
connection. On aggressive battery-saver modes (Samsung, Xiaomi), the
OS will kill the connection — disable battery optimisation for the
app to fix.

---

## How the signed APK gets built (for maintainers)

1. **One-time keystore bootstrap** — generate a strong random
   password out-of-band (e.g. `openssl rand -base64 24`), export it,
   then run the helper. Upload the four printed values to GitHub
   Actions secrets.

   ```bash
   # substitute real values — do not commit them anywhere
   export STORE_PASSWORD="$(openssl rand -base64 24)"
   export KEY_PASSWORD="$(openssl rand -base64 24)"
   bash scripts/android/generate-release-keystore.sh
   ```

   The script prints the four secret names to upload:
   `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`,
   `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`.

2. **CI signing** — `.github/workflows/release.yml` decodes the
   base64 keystore into the build workspace, writes a transient
   `key.properties`, then runs `flutter build apk --release`.
   `build.gradle.kts` picks up the properties file and signs with
   the release config; if the file is absent (e.g. a PR without
   access to secrets) it falls back to the debug keystore so
   local builds keep working.

3. **Release attachment** — `softprops/action-gh-release@v2`
   uploads `app-release.apk` as an asset on the tagged release.
   The `latest/download/app-release.apk` URL in this guide is
   resolved by GitHub automatically.

---

## Related docs

- [`ROADMAP.md`](../../ROADMAP.md) — when iOS joins this guide
- [v2.0.0 productization plan](../_meta/v2.0.0-productization-plan.md)
  — M1 section covers why APK-only is the correct v1.1.0 scope
- [Architecture overview](../architecture/overview.md) — where the
  mobile app fits into the platform
