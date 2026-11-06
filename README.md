# 🛕 GhatMitra (ఘాట్ మిత్ర)

> **"Every ghat, every asset, every pilgrim looked after"**  
> Civic Works, Ghat Asset Readiness & Field Incident Monitoring Platform for **Godavari Pushkaralu 2027 (Rajamahendravaram)**.  
> Built with **FastAPI**, **SQLAlchemy ORM**, **SQLite**, and **Jinja2 Templates**.

---

## 📖 Overview

**GhatMitra** provides municipal engineers, district administration, and field supervisors with a unified single-page control room hub to monitor all civil construction packages, vendor performance, physical asset readiness, and on-ground guard incident reports across the 5 primary bathing ghats of Rajamahendravaram.

### 🌟 Core Capabilities
- **Single-Page Home Hub:** Fast, zero-reload client-side hash routing (`#home`, `#guard`, `#field`, `#works`, `#assets`, `#vendors`, `#alerts`, `#report`).
- **Data Isolation:** Each module strictly displays its own records:
  - **Guard Reports:** Incident complaints submitted by on-ground patrol guards with 56px photo thumbnails, status tracking, and 1-click resolve.
  - **Engineer Updates:** Physical progress checks, milestone photos, and inspection notes.
  - **Works Packages:** 30 civil infrastructure works (ghat steps, bio-toilets, floodlights, barricading, parking, shelters, water points).
  - **Assets Fleet:** 40 field assets (bio-toilets, bins, high-mast floodlights, CCTV cameras, generators).
  - **Vendors Scorecard:** Empanelled contractors ranked by composite score (50% on-time, 30% quality rating, 20% alert penalties).
  - **Alerts Feed:** Central consolidated stream with priority tags and supervisor actions.
  - **Readiness Report:** Print-ready audit summary with CSV downloads.
- **On-Ground Guard App (`/guard`):** Ultra-lightweight, offline-first mobile app for field guards. Zero images, zero animations, bilingual Telugu/English 3-tap reporting.
- **Engineer Update App (`/field`):** Mobile milestone logger with automatic client-side photo compression.
- **Control Room Visuals:** Saffron & navy government theme with layered SVG Godavari river waves, temple gopuram silhouette, drifting boats, rising diyas, and golden particles.
- **Detail Drawer & Photo Zoom:** Tap any incident row to slide out high-resolution photos, coordinates, and assignment workflows.

---

## 🗄️ Database Schema & Entities

The application utilizes SQLAlchemy with SQLite (`pushkar_works.db`):

| Table | Primary Columns | Description |
|---|---|---|
| **`ghats`** | `id`, `name`, `latitude`, `longitude` | 5 Pushkar bathing ghats around Rajamahendravaram. |
| **`vendors`** | `id`, `name`, `contact_person`, `on_time_pct`, `quality_rating`, `staff_deployed` | 10 infrastructure and civic service contractors. |
| **`works`** | `id`, `title`, `category`, `ghat_id`, `vendor_id`, `planned_start`, `planned_end`, `progress_pct`, `status`, `budget`, `latitude`, `longitude`, `last_updated` | 30 work packages categorized across 7 types; ~30% delayed. |
| **`assets`** | `id`, `name`, `type`, `ghat_id`, `status`, `last_service_date`, `next_service_date` | 40 field assets (mobile toilet, bin, light, CCTV, generator); ~10% faulty. |
| **`work_updates`** | `id`, `work_id`, `progress_pct`, `note`, `photo_url`, `updated_by`, `created_at` | Site inspection logs, progress updates, and photos. |
| **`alerts`** | `id`, `type`, `severity`, `message`, `photo_url`, `related_work_id`, `related_asset_id`, `status`, `created_at` | Central alerts and guard complaints. |

> 💡 **Photo Storage Note:** In this deployment, photos are compressed client-side (<150 KB) and persisted under `/static/uploads/`. In an enterprise multi-region deployment, uploads would be routed directly to S3 / Google Cloud Storage signed buckets.

---

## 🚀 Quick Start & Seed Command

### 1. Requirements
Python 3.9+ installed.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Database Seed Command
```bash
python -m app.seed
```
*Output:*
```
============================================================
GHATMITRA — DATABASE SEEDED SUCCESSFULLY
============================================================
• Ghats:        5
• Vendors:      10
• Works:        30  (Delayed: 9 -> 30.0%)
• Assets:       40  (Faulty: 4 -> 10.0%)
• Alerts:       15
• Work Updates: 20
============================================================
```

### 4. Start the Application
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Open your browser to: **[http://localhost:8000](http://localhost:8000)**

---

## 🔍 API & System Endpoints

- **`GET /health`** &rarr; JSON health check returning database status and row counts.
- **`GET /api/hub/counts`** &rarr; Live counts for 7 feature tiles (polled every 10s by control room).
- **`GET /api/guard/reports`** &rarr; Guard incident reports with clean message and relative photo URLs.
- **`POST /api/guard/report`** &rarr; Submit 3-tap guard incident with base64 photo.
- **`GET /api/engineer/updates`** &rarr; Chronological list of civil progress checks and asset inspections.
- **`GET /api/alerts/{id}`** &rarr; Full case detail for detail drawer.
- **`POST /api/alerts/{id}/status`** &rarr; Update alert status (`open`, `in_progress`, `resolved`).
- **`POST /api/works/{id}/update`** &rarr; Log physical progress and site photos.
- **`POST /api/assets/{id}/status`** &rarr; Set asset condition (`working`, `faulty`, `under maintenance`) and trigger alerts.
- **`GET /api/export/works.csv`** &rarr; Direct CSV export of all works packages.
- **`POST /api/seed`** &rarr; Reset and reseed the database to clean demo state.
