# 📱 Google Play Console Setup & Internal/Closed Testing Guide

This guide walks you step-by-step through setting up **Jev AI Flow** in the **Google Play Console**, uploading your build, and distributing it to **Internal Testing** and **Closed Testing** groups.

---

## 📦 1. Artifacts Ready for Deployment

The build pipeline has generated signed, production-ready binaries in `releases/`:
- **Debug APK (For Instant Demo via USB/ADB):**  
  `releases/jev-ai-flow-v1.0.0-debug.apk` (3.7 MB)
- **Signed Release App Bundle (For Play Console Upload):**  
  `releases/jev-ai-flow-v1.0.0-release.aab` (2.8 MB)
- **Keystore Location:**  
  `mobile/android/jev-ai-release.jks`
- **Keystore Alias:** `jevaiflow`

---

## 📲 2. Quick Demo on Physical Android Device (Without Waiting for Play Store)

You can run the app directly on your Android phone right now:
1. Connect your Android phone via USB cable.
2. Enable **Developer Options** and turn on **USB Debugging** on your phone:
   - Go to *Settings > About Phone > Tap 'Build Number' 7 times*.
   - In *System > Developer Options*, toggle on *USB Debugging*.
3. Verify connection:
   ```powershell
   & "C:\Users\Tarun\AppData\Local\Android\Sdk\platform-tools\adb.exe" devices
   ```
4. Install the debug APK directly:
   ```powershell
   & "C:\Users\Tarun\AppData\Local\Android\Sdk\platform-tools\adb.exe" install -r "releases/jev-ai-flow-v1.0.0-debug.apk"
   ```
5. Launch **Jev AI Flow** from your app drawer!

---

## 🌐 3. Setting Up Google Play Console

### Step 3.1: Create New App
1. Go to [Google Play Console](https://play.google.com/console).
2. Click **Create app** (top-right).
3. Fill in the initial details:
   - **App name:** `Jev AI Corporate Actions` (or `Jev AI Flow`)
   - **Default language:** English (United States) - `en-US`
   - **App or game:** `App`
   - **Free or paid:** `Free`
   - Accept the Developer Program Policies and US export laws declarations.
   - Click **Create app**.

---

### Step 3.2: Complete Mandatory App Content Tasks (Dashboard Checklist)
Google requires completing the **Set up your app** tasks before publishing:
1. **Privacy Policy**:
   - Host `PRIVACY_POLICY.md` (e.g. via GitHub Gist or GitHub Pages).
   - Enter your public URL in *Policy and programs > App content > Privacy policy*.
2. **App Access**: Select *"All functionality is available without special access"* (since the demo runs standalone).
3. **Ads**: Select *"No, my app does not contain ads"*.
4. **Content Ratings**:
   - Start questionnaire.
   - Category: `Enterprise / Productivity / Utility`.
   - Answer "No" to violence, sexuality, offensive language, controlled substances.
   - Save and calculate rating (will receive PEGI 3 / Everyone rating).
5. **Target Audience and Content**:
   - Select age groups: `18 and over`.
   - Could it unintentionally appeal to children: Select `No`.
6. **Financial Features**:
   - Select *"My app doesn't provide any financial features"* or *"Financial workflow management"* (not a direct lending/banking consumer service).
7. **Data Safety**:
   - Does your app collect or share user data: Select **No** for this standalone demo.

---

### Step 3.3: Set Up Store Listing Assets
Navigate to **Grow > Store presence > Main store listing**:
- **Short description:** `Intelligent corporate actions email parsing and decision engine.`
- **Full description:**
  ```text
  Jev AI Corporate Actions Flow is an intelligent email parsing, document OCR, and workflow automation solution powered by TypeSafe AI's Jev System One decision engine and Gemini Vision.
  
  Features:
  - 4-stage automated processing: Ingestion Gate, Vision OCR, Core Decision, and Smart Routing.
  - Urgency scoring (1-10) with automatic operational priority sorting.
  - Automated Gemini drafting of localized client notice election messages.
  - Human-in-the-Loop exception handling desk for breaks and high-risk notifications.
  ```
- **App icon:** 512 x 512 px PNG (32-bit color).
- **Feature graphic:** 1024 x 500 px JPEG or PNG.
- **Phone screenshots:** Minimum 2 screenshots (upload screenshots taken from the mobile app).

---

## 🚀 4. Releasing to Internal Testing (Instant Demo Access)

**Internal Testing** is the fastest path: builds become available **within minutes** without going through standard Google review queues!

1. In Play Console sidebar, navigate to **Testing > Internal testing**.
2. Click **Create new release** (top-right).
3. Under **App bundles**, upload `releases/jev-ai-flow-v1.0.0-release.aab`.
4. Enter **Release name:** `1.0.0 (Initial Demo)`.
5. Enter **Release notes:**
   ```text
   Initial demo release of Jev AI Corporate Actions Flow mobile application featuring 4-stage decision pipeline, Gemini OCR, and urgency sorting.
   ```
6. Click **Next** and **Save and publish**.
7. **Add Testers**:
   - Switch to the **Testers** tab in Internal testing.
   - Create an email list (e.g., `Demo Testers`) and enter your email address (and your colleagues' Google accounts).
   - Under **How testers join your test**, copy the **Join link (Web or Android)**.
   - Open that link on your Android smartphone, click **Become a tester**, and tap **Download on Google Play** to install directly!

---

## 👥 5. Releasing to Closed Testing (Alpha / Beta Groups)

Once Internal testing is confirmed:
1. Navigate to **Testing > Closed testing**.
2. Click **Create track** (or select default `Alpha` track).
3. Name your track (e.g., `Internal Stakeholders Alpha`).
4. Click **Create release**:
   - You can click **Add from library** and pick the `1.0.0` bundle you already uploaded for internal testing, or upload a new `.aab`.
5. Under the **Testers** tab:
   - Select your test group email list or Google Group.
   - Set feedback URL/email.
6. Review and submit for Closed Testing review.
