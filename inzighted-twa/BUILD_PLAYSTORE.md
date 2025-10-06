This document explains how to build a Play Store-ready Android App Bundle (AAB) for the Trusted Web Activity (TWA) project in this folder.

Prerequisites
- JDK 11+ installed and available on PATH.
- Android SDK (command-line tools) and required platforms installed (compileSdkVersion 36).
- Gradle wrapper (the repo provides `gradlew` / `gradlew.bat`).
- A signing key (keystore). This repo contains `android.keystore` as an example bundled keystore. For Play Store you should use a secure, private keystore.

1) Configure signing
Option A - Local properties file (recommended for local dev):
- Copy `keystore.properties.example` to `keystore.properties` in this directory.
- Update values: `storeFile`, `storePassword`, `keyAlias`, `keyPassword`.

Option B - Environment variables (recommended for CI):
- Set `KEYSTORE_FILE`, `KEYSTORE_PASSWORD`, `KEY_ALIAS`, `KEY_PASSWORD`.

2) Build an AAB locally (Windows CMD)
Open a terminal at the `inzighted-twa` folder and run:

```cmd
gradlew.bat bundleRelease
```

The generated AAB will be under `app\build\outputs\bundle\release\app-release.aab`.

3) Test the release build (optional)
- You can install the release APK (if you build `assembleRelease`) on a testing device or test the AAB with internal app sharing on Play Console.

4) Upload to Play Console
- Sign into Play Console and follow steps to create a new app or use existing.
- Use the produced AAB and upload to the release track you want (internal, closed, or production).
- Fill store listing, screenshots, content rating, privacy policy, and other Play requirements.

Notes and recommendations
- Use a unique applicationId and bump `versionCode` and `versionName` in `app/build.gradle` before releasing.
- Use Google Play App Signing (recommended): when you enroll, Play will manage the app signing key and you upload an upload key instead.
- Remove the bundled `android.keystore` from source control when switching to a real production key.

CI Example
- In your CI pipeline, set environment variables and call `gradlew bundleRelease` in the `inzighted-twa` directory. Ensure the SDK, JDK, and licenses are installed.

If you'd like, I can:
- Add a small script to bump version codes automatically.
- Add a `proguard-rules.pro` file if you want to customize obfuscation rules.
- Remove the bundled `android.keystore` and add instructions for creating a new keystore.
