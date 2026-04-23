#!/usr/bin/env bash
#
# Generate a release keystore for the ForgeLink Flutter app.
#
# Run this ONCE per app/team. The output keystore must be kept secret
# (losing it means losing the ability to publish updates under the same
# package name on Google Play); it is gitignored here. For CI signing
# the keystore is uploaded to GitHub Actions secrets — see
# docs/mobile/install.md for the bootstrap-to-CI pipeline.
#
# Outputs:
#   services/flutter-app/android/forgelink-release.jks
#   services/flutter-app/android/key.properties
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ANDROID_DIR="$REPO_ROOT/services/flutter-app/android"
KEYSTORE_PATH="$ANDROID_DIR/forgelink-release.jks"
PROPERTIES_PATH="$ANDROID_DIR/key.properties"

if [[ -f "$KEYSTORE_PATH" ]]; then
  echo "✗ Keystore already exists at $KEYSTORE_PATH"
  echo "  Delete it manually only if you know what you are doing — losing"
  echo "  the keystore permanently blocks Play Store updates under the"
  echo "  same package name."
  exit 1
fi

command -v keytool >/dev/null || {
  echo "✗ keytool not found. Install a JDK (e.g. 'asdf install java temurin-21.0.4+7.0.LTS')"
  exit 1
}

# The two required credentials are read from environment variables.
# See docs/mobile/install.md for how to generate strong values at runtime.
if [[ -z "${STORE_PASSWORD:-}" ]]; then
  echo "✗ STORE_PASSWORD env var must be set (see docs/mobile/install.md)" >&2
  exit 2
fi
if [[ -z "${KEY_PASSWORD:-}" ]]; then
  echo "✗ KEY_PASSWORD env var must be set (see docs/mobile/install.md)" >&2
  exit 2
fi

DNAME="${DNAME:-CN=Mugemane Bertin, O=ForgeLink, L=Kigali, C=RW}"
VALIDITY="${VALIDITY_DAYS:-10950}"   # 30 years — Play Store expects long validity

echo "→ Creating keystore at $KEYSTORE_PATH (validity: ${VALIDITY} days)"
keytool -genkeypair \
  -v \
  -keystore "$KEYSTORE_PATH" \
  -storetype JKS \
  -keyalg RSA \
  -keysize 2048 \
  -validity "$VALIDITY" \
  -alias forgelink \
  -dname "$DNAME" \
  -storepass "$STORE_PASSWORD" \
  -keypass "$KEY_PASSWORD" \
  2>&1 | grep -v 'Warning:' | tail -10

echo "→ Writing $PROPERTIES_PATH"
cat > "$PROPERTIES_PATH" <<EOF
storeFile=forgelink-release.jks
storePassword=$STORE_PASSWORD
keyAlias=forgelink
keyPassword=$KEY_PASSWORD
EOF

chmod 600 "$KEYSTORE_PATH" "$PROPERTIES_PATH"

echo
echo "✓ Keystore ready. Gitignored — do not commit."
echo
echo "To wire CI signing, base64-encode the keystore and upload to GitHub"
echo "Actions secrets:"
echo
echo "  base64 -i $KEYSTORE_PATH | pbcopy   # macOS"
echo "  base64 -w0 $KEYSTORE_PATH          # linux"
echo
echo "Then in https://github.com/MugemaneBertin2001/forgelink/settings/secrets/actions"
echo "add:"
echo "  ANDROID_KEYSTORE_BASE64 = <that base64 string>"
echo "  ANDROID_KEYSTORE_PASSWORD = $STORE_PASSWORD"
echo "  ANDROID_KEY_ALIAS = forgelink"
echo "  ANDROID_KEY_PASSWORD = $KEY_PASSWORD"
