#!/bin/sh
set -eu

if [ "$(id -u)" -ne 0 ]; then echo "ERROR: jalankan sebagai root"; exit 1; fi
export ANDROID_HOME=/opt/android-sdk
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:/opt/gradle-8.13/bin:$PATH"

apt-get update
apt-get install -y ca-certificates curl unzip openjdk-17-jdk-headless

if [ ! -x "$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager" ]; then
  mkdir -p "$ANDROID_HOME/cmdline-tools"
  curl -fL "https://dl.google.com/android/repository/commandlinetools-linux-15859902_latest.zip" -o /tmp/android-tools.zip
  echo "4e4c464f145a7512b57d088ac6c278c03c9eea610886b35a5e0804e74eedf583  /tmp/android-tools.zip" | sha256sum -c -
  unzip -q /tmp/android-tools.zip -d /tmp/android-tools
  mkdir -p "$ANDROID_HOME/cmdline-tools/latest"
  cp -a /tmp/android-tools/cmdline-tools/. "$ANDROID_HOME/cmdline-tools/latest/"
fi

if [ ! -x /opt/gradle-8.13/bin/gradle ]; then
  curl -fL "https://downloads.gradle.org/distributions/gradle-8.13-bin.zip" -o /tmp/gradle.zip
  unzip -q /tmp/gradle.zip -d /opt
fi

yes | sdkmanager --licenses >/dev/null || true
sdkmanager "platform-tools" "platforms;android-36" "build-tools;36.0.0"

if [ ! -f rw10plus-release.jks ]; then
  printf "Masukkan password signing APK: "
  stty -echo; read -r KEY_PASS; stty echo; printf "\n"
  if [ "${#KEY_PASS}" -lt 10 ]; then echo "ERROR: password minimal 10 karakter"; exit 1; fi
  keytool -genkeypair -v -keystore rw10plus-release.jks -storepass "$KEY_PASS" -keypass "$KEY_PASS" -alias rw10plus -keyalg RSA -keysize 4096 -validity 10000 -dname "CN=RW10 Plus, OU=Digital RW10, O=RW10, L=Bogor, ST=Jawa Barat, C=ID"
  umask 077
  printf 'storeFile=rw10plus-release.jks\nstorePassword=%s\nkeyAlias=rw10plus\nkeyPassword=%s\n' "$KEY_PASS" "$KEY_PASS" > keystore.properties
fi

gradle --no-daemon clean lintRelease assembleRelease -PRW10_SERVER_URL=http://192.168.100.50:8188/
mkdir -p output
cp app/build/outputs/apk/release/app-release.apk output/RW10PLUS-INTERNAL-v0.3.0.apk
sha256sum output/RW10PLUS-INTERNAL-v0.3.0.apk
echo "APK berhasil: $(pwd)/output/RW10PLUS-INTERNAL-v0.3.0.apk"
