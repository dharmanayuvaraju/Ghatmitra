# 🚀 Deployment Guide: GhatMitra on Render (Free Tier)

This guide walks you through deploying **GhatMitra** to [Render](https://render.com) and testing the real-time flow across two devices (e.g. desktop control room and phone field guard).

---

## 📋 Prerequisites
1. A free [GitHub](https://github.com) account.
2. A free [Render](https://render.com) account.
3. Git installed locally.

---

## 🛠️ Step 1: Push Code to GitHub

From your local project folder:

```bash
git init
git add .
git commit -m "feat: GhatMitra final submission release"
git branch -M main
git remote add origin https://github.com/<your-username>/ghatmitra.git
git push -u origin main
```

---

## 🌐 Step 2: Deploy to Render

1. Log in to your **[Render Dashboard](https://dashboard.render.com)**.
2. Click **New +** &rarr; Select **Web Service**.
3. Choose **Build and deploy from a Git repository** &rarr; Select your `ghatmitra` repository.
4. Fill in the settings:
   - **Name:** `ghatmitra` (or your chosen name)
   - **Region:** Singapore / Frankfurt / Oregon (choose closest)
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** `Free`
5. *(Optional)* If using a managed Render PostgreSQL database:
   - Under **Environment Variables**, add:
     - `DATABASE_URL` = `<your-render-postgres-internal-or-external-url>`
   - If not set, GhatMitra automatically uses SQLite with automatic auto-seeding on first boot.
6. Click **Deploy Web Service**.
7. Wait 1–2 minutes for the build to complete. Once deployed, Render will display your live URL:
   `https://ghatmitra.onrender.com`

---

## 📱 Step 3: Two-Phone Real-Time Demo Test

Test the real-time incident resolution workflow across two devices:

### Device 1: Control Room (Desktop or Phone 1)
1. Open `https://ghatmitra.onrender.com/#home`
2. Notice the live hero countdown, budget at risk, and the 7 feature tiles.
3. Observe the green **Live: Synced** indicator in the top header.
4. Click **Sound: Off** to toggle it to **🔔 Beep: On**.

### Device 2: Patrol Guard (Phone 2)
1. Open `https://ghatmitra.onrender.com/guard`
2. The page loads in milliseconds (under 35 KB, offline-ready).
3. Tap your location (e.g. **పుష్కర్ ఘాట్ / Pushkar Ghat**).
4. Tap an issue (e.g. **🚽 మరుగుదొడ్డి / Toilet not working**).
5. Snap or select a photo & tap **సమస్యను పంపండి / Submit Report**.

### Immediate Verification in Control Room (Within 10 seconds):
- Device 1 plays an audio chime and displays a notification toast: `🛡️ New Guard Report received!`.
- The **Guard Reports** tile badge updates and pulses red.
- Switch to **Guard Reports** (`/#guard`) &rarr; Click the new report row.
- In the **Detail Drawer**:
  - Review the photo and incident description.
  - Tap **👤 Assign** &rarr; Select `K. Satyanarayana (Sanitation Supervisor)`.
  - Tap **✓ Resolve** &rarr; Attach a fix photo & note &rarr; Click **Confirm**.
  - Review the **Before / After** side-by-side comparison and the green `✓ Resolved in X minutes` certification badge.

---

## 🩺 System Health Check
Verify uptime monitor status at any time:
```
GET https://ghatmitra.onrender.com/health?quick=true
```
Response:
```json
{"status": "healthy", "project": "GhatMitra", "version": "2.0.0"}
```

