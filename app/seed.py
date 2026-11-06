import random
from datetime import datetime, timedelta
from app.database import Base, engine, SessionLocal
from app.models import Ghat, Vendor, Work, Asset, WorkUpdate, Alert

def seed_db():
    # Recreate tables cleanly
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if already seeded; if so, clear and reseed cleanly
        db.query(Alert).delete()
        db.query(WorkUpdate).delete()
        db.query(Asset).delete()
        db.query(Work).delete()
        db.query(Vendor).delete()
        db.query(Ghat).delete()
        db.commit()

        now = datetime.now()

        # 1. 5 Ghats near 17.00N, 81.78E (Rajamahendravaram)
        ghats_data = [
            Ghat(name="Pushkar Ghat", latitude=17.0018, longitude=81.7768),
            Ghat(name="Kotilingala Ghat", latitude=17.0085, longitude=81.7742),
            Ghat(name="Saraswati Ghat", latitude=16.9962, longitude=81.7801),
            Ghat(name="Markandeya Ghat", latitude=17.0042, longitude=81.7758),
            Ghat(name="VIP Gautami Ghat", latitude=16.9925, longitude=81.7834),
        ]
        db.add_all(ghats_data)
        db.commit()

        # 2. 10 Vendors
        vendors_data = [
            Vendor(name="Godavari Infra Projects Ltd", contact_person="Ravi Varma", on_time_pct=88.5, quality_rating=4.6, staff_deployed=45),
            Vendor(name="Andhra Civic Solutions", contact_person="K. Satyanarayana", on_time_pct=92.0, quality_rating=4.8, staff_deployed=60),
            Vendor(name="Rajamahendra Electricals", contact_person="Venkatesh Rao", on_time_pct=78.0, quality_rating=4.1, staff_deployed=30),
            Vendor(name="Pushkaralu Sanitation Corp", contact_person="P. Lakshmi", on_time_pct=94.5, quality_rating=4.7, staff_deployed=85),
            Vendor(name="Deccan Barricades & Safety", contact_person="Suresh Reddy", on_time_pct=72.0, quality_rating=3.9, staff_deployed=25),
            Vendor(name="Gautami Fabricators & Shelters", contact_person="B. Nagesh", on_time_pct=85.0, quality_rating=4.3, staff_deployed=40),
            Vendor(name="Riverbank Civil Works", contact_person="T. Rama Krishna", on_time_pct=68.5, quality_rating=3.7, staff_deployed=35),
            Vendor(name="Apex Crowd Control Infrastructure", contact_person="M. Anitha", on_time_pct=96.0, quality_rating=4.9, staff_deployed=50),
            Vendor(name="Jaladhara Water Systems", contact_person="Ch. Subba Rao", on_time_pct=89.0, quality_rating=4.5, staff_deployed=28),
            Vendor(name="Suraksha CCTV & Power Systems", contact_person="K. Kishore", on_time_pct=81.0, quality_rating=4.2, staff_deployed=22),
        ]
        db.add_all(vendors_data)
        db.commit()

        # 3. 30 Works across categories: ghat steps / toilet / lighting / barricade / parking / shelter / water point
        # Exactly 9 delayed (30%), 12 on track (40%), 5 completed (~17%), 4 not started (~13%)
        categories = ["ghat steps", "toilet", "lighting", "barricade", "parking", "shelter", "water point"]
        
        works_specs = [
            # 9 DELAYED works (30%)
            ("Main Steps Granite Cladding & Anti-Skid Grooving", "ghat steps", 1, 1, "delayed", 42, 4500000.0, -25, 10),
            ("Modular Bio-Toilet Block A (16 Units)", "toilet", 1, 4, "delayed", 35, 2200000.0, -20, 8),
            ("High-Mast Flood Lighting Installation", "lighting", 2, 3, "delayed", 50, 1800000.0, -30, 5),
            ("Heavy-Duty Crowd Segregation Barricading", "barricade", 2, 5, "delayed", 48, 1400000.0, -18, 12),
            ("VIP Transit Parking Bay Leveling & Pavers", "parking", 5, 7, "delayed", 28, 3100000.0, -22, 14),
            ("Pilgrim Holding Area Sunshade Tensile Shelter", "shelter", 3, 6, "delayed", 55, 3800000.0, -28, 7),
            ("Continuous RO Drinking Water Dispensing Kiosks", "water point", 4, 9, "delayed", 40, 1200000.0, -15, 10),
            ("Riverbank Submerged Safety Railings Retrofitting", "barricade", 4, 7, "delayed", 30, 1950000.0, -20, 15),
            ("Emergency Evacuation Corridor Steps Widening", "ghat steps", 2, 1, "delayed", 62, 2800000.0, -35, 4),

            # 12 ON TRACK works (40%)
            ("Kotilingala North Steps Desilting & Repair", "ghat steps", 2, 2, "on track", 72, 1600000.0, -20, 15),
            ("Mobile Toilet Complex Installation (South Entry)", "toilet", 2, 4, "on track", 65, 1850000.0, -15, 20),
            ("LED Solar Mast Installation along Promenade", "lighting", 1, 3, "on track", 80, 2100000.0, -25, 10),
            ("Waterfront Deep Barricade Steel Mesh Grid", "barricade", 1, 8, "on track", 78, 2500000.0, -30, 8),
            ("Pushkar Holding Ground 1 Vehicle Parking", "parking", 1, 2, "on track", 85, 3400000.0, -35, 5),
            ("Pilgrim Rest Shelter Bamboo-Thatch Canopy", "shelter", 2, 6, "on track", 70, 1500000.0, -18, 18),
            ("Pushkar Main Promenade Cold Water Fountain Network", "water point", 1, 9, "on track", 82, 1750000.0, -22, 12),
            ("Saraswati Ghat Bathing Platform Stone Paving", "ghat steps", 3, 1, "on track", 68, 2900000.0, -20, 22),
            ("VIP Ghat Protocol Lounge Prefab Shelter", "shelter", 5, 6, "on track", 75, 4200000.0, -25, 15),
            ("Saraswati River Approach Safety Netting", "barricade", 3, 8, "on track", 60, 1300000.0, -14, 21),
            ("Markandeya East Vehicle Staging Area", "parking", 4, 2, "on track", 64, 2600000.0, -16, 25),
            ("Gautami Ghat High-Flow Potable Water Tank Station", "water point", 5, 9, "on track", 74, 2100000.0, -19, 16),

            # 5 COMPLETED works (~17%)
            ("Pushkar Central Bathing Steps Re-Alignment", "ghat steps", 1, 2, "completed", 100, 3200000.0, -45, -5),
            ("Saraswati Ghat Solar Streetlight Grid", "lighting", 3, 10, "completed", 100, 1400000.0, -40, -10),
            ("Markandeya Main Entry Crowd Channelling Gates", "barricade", 4, 8, "completed", 100, 1100000.0, -30, -2),
            ("Kotilingala North Public Drinking Water Point", "water point", 2, 9, "completed", 100, 950000.0, -35, -8),
            ("VIP Ghat Sanitation Modular Facility", "toilet", 5, 4, "completed", 100, 2400000.0, -50, -12),

            # 4 NOT STARTED works (~13%)
            ("Riverbed Silt Dredging & Stabilization Steps", "ghat steps", 5, 1, "not started", 0, 5200000.0, 5, 35),
            ("Eco-Friendly Vacuum Toilets near Markandeya", "toilet", 4, 4, "not started", 0, 3100000.0, 8, 40),
            ("Smart Solar Bollard Lighting Phase II", "lighting", 5, 3, "not started", 0, 1650000.0, 10, 35),
            ("Bus Transit Hub 3 Paving & Solar Roofs", "parking", 3, 2, "not started", 0, 4800000.0, 12, 45),
        ]

        works_data = []
        for title, cat, g_id, v_id, status, prog, budget, start_delta, end_delta in works_specs:
            ghat = ghats_data[g_id - 1]
            # Offset latitude/longitude slightly around the ghat coordinate
            lat = round(ghat.latitude + random.uniform(-0.0015, 0.0015), 5)
            lng = round(ghat.longitude + random.uniform(-0.0015, 0.0015), 5)
            p_start = now + timedelta(days=start_delta)
            p_end = now + timedelta(days=end_delta)
            last_up = now - timedelta(hours=random.randint(1, 48))
            
            w = Work(
                title=title,
                category=cat,
                ghat_id=g_id,
                vendor_id=v_id,
                planned_start=p_start,
                planned_end=p_end,
                progress_pct=prog,
                status=status,
                budget=budget,
                latitude=lat,
                longitude=lng,
                last_updated=last_up
            )
            works_data.append(w)
            
        db.add_all(works_data)
        db.commit()

        # 4. 40 Assets: types (mobile toilet / bin / light / CCTV / generator)
        # Exactly 4 faulty (10%), 4 under maintenance (10%), 32 working (80%)
        asset_types = ["mobile toilet", "bin", "light", "CCTV", "generator"]
        assets_data = []
        
        statuses = ["faulty"] * 4 + ["under maintenance"] * 4 + ["working"] * 32
        random.seed(42) # deterministic for clean demo
        random.shuffle(statuses)

        asset_names_map = {
            "mobile toilet": ["Bio-Toilet Trailer A", "Express Sanitation Pod B", "Women's Hygiene Unit C", "Elder-Accessible Cabin D"],
            "bin": ["Twin Smart Compactor Bin", "Stainless Litter Receptacle", "Segregated High-Cap Drum", "Wet-Dry Recycling Station"],
            "light": ["High-Mast Mast 1", "Solar Flood Unit 4", "LED Tower Beacon 2", "Promenade Strip Array"],
            "CCTV": ["360 PTZ Surveillance Cam", "Facial Density Cam 08", "Waterfront Night-Vision IP Cam", "Crowd Flow Sensor Unit"],
            "generator": ["125 kVA Silent DG Set", "250 kVA Prime Power Genset", "75 kVA Mobile Backup Trailer", "160 kVA Emergency Genset"]
        }

        for i in range(40):
            a_type = asset_types[i % len(asset_types)]
            ghat_id = (i % 5) + 1
            st = statuses[i]
            prefix = asset_names_map[a_type][i % 4]
            a_name = f"{prefix} #{i+1:02d} ({ghats_data[ghat_id - 1].name.split()[0]})"
            
            last_srv = now - timedelta(days=random.randint(5, 60))
            next_srv = now + timedelta(days=random.randint(2, 45))
            if st == "faulty":
                next_srv = now - timedelta(days=1) # overdue service

            a = Asset(
                name=a_name,
                type=a_type,
                ghat_id=ghat_id,
                status=st,
                last_service_date=last_srv,
                next_service_date=next_srv
            )
            assets_data.append(a)

        db.add_all(assets_data)
        db.commit()

        # 5. 15 Alerts (severity: high / medium / low; status: open / resolved)
        alerts_data = [
            # High severity alerts
            Alert(
                type="Work Delay", severity="high", status="open",
                message="Granite cladding work delayed by 18 days due to material supply bottleneck at Pushkar Ghat.",
                related_work_id=1, related_asset_id=None,
                created_at=now - timedelta(hours=3)
            ),
            Alert(
                type="Asset Breakdown", severity="high", status="open",
                message="Critical 250 kVA Prime Power Genset #05 shutdown due to radiator leak near Kotilingala main pump.",
                related_work_id=None, related_asset_id=5,
                created_at=now - timedelta(hours=5)
            ),
            Alert(
                type="Safety Hazard", severity="high", status="open",
                message="Crowd segregation barricade structural weld failure identified during load test.",
                related_work_id=4, related_asset_id=None,
                created_at=now - timedelta(hours=8)
            ),
            Alert(
                type="Asset Failure", severity="high", status="open",
                message="360 PTZ Surveillance Cam #14 video feed offline; fiber cable damaged by trenching works.",
                related_work_id=None, related_asset_id=14,
                created_at=now - timedelta(hours=12)
            ),
            Alert(
                type="Work Stoppage", severity="high", status="resolved",
                message="Saraswati approach road excavation halted due to high tide flooding; dewatering complete.",
                related_work_id=8, related_asset_id=None,
                created_at=now - timedelta(days=2)
            ),

            # Medium severity alerts
            Alert(
                type="Schedule Variance", severity="medium", status="open",
                message="Mobile toilet installation milestone lagging by 8 days behind critical path.",
                related_work_id=2, related_asset_id=None,
                created_at=now - timedelta(hours=14)
            ),
            Alert(
                type="Maintenance Due", severity="medium", status="open",
                message="Bio-Toilet Trailer A #01 bio-digester bacteria recharge pending for 48 hours.",
                related_work_id=None, related_asset_id=1,
                created_at=now - timedelta(hours=18)
            ),
            Alert(
                type="Quality Warning", severity="medium", status="open",
                message="Tensile fabric weld seam test showed minor tension variance on Sunshade Canopy.",
                related_work_id=6, related_asset_id=None,
                created_at=now - timedelta(days=1)
            ),
            Alert(
                type="Service Overdue", severity="medium", status="open",
                message="High-Mast Flood Lighting Mast 1 #11 ballast inspection overdue.",
                related_work_id=None, related_asset_id=11,
                created_at=now - timedelta(days=1, hours=6)
            ),
            Alert(
                type="Vendor Performance", severity="medium", status="resolved",
                message="Deccan Barricades contractor issued notice for under-staffing on site; 15 additional personnel deployed.",
                related_work_id=4, related_asset_id=None,
                created_at=now - timedelta(days=3)
            ),

            # Low severity alerts
            Alert(
                type="Asset Bin Full", severity="low", status="open",
                message="Twin Smart Compactor Bin #07 capacity reached 95% at Saraswati Ghat entrance.",
                related_work_id=None, related_asset_id=7,
                created_at=now - timedelta(hours=2)
            ),
            Alert(
                type="Routine Inspection", severity="low", status="open",
                message="RO Drinking Water Point pressure gauge requires standard re-calibration.",
                related_work_id=7, related_asset_id=None,
                created_at=now - timedelta(hours=6)
            ),
            Alert(
                type="Minor Damage", severity="low", status="resolved",
                message="Temporary pedestrian signage bracket dislodged by wind; replaced and secured.",
                related_work_id=3, related_asset_id=None,
                created_at=now - timedelta(days=4)
            ),
            Alert(
                type="Filter Cleaning", severity="low", status="resolved",
                message="Intake filters cleaned on 160 kVA Genset #20 at VIP Ghat.",
                related_work_id=None, related_asset_id=20,
                created_at=now - timedelta(days=5)
            ),
            Alert(
                type="Inventory Check", severity="low", status="resolved",
                message="LED replacement bulb reserves replenished at Pushkar storehouse.",
                related_work_id=None, related_asset_id=3,
                created_at=now - timedelta(days=6)
            ),
        ]
        db.add_all(alerts_data)
        db.commit()

        # 6. 20 Work Updates
        updates_data = [
            WorkUpdate(work_id=1, progress_pct=42, note="Received 12 trucks of non-slip granite slabs from Betamcherla quarries. Masonry crew deployed on north steps.", photo_url="/static/img/updates/steps_cladding.jpg", updated_by="Er. M. Rao (Executive Engineer)", created_at=now - timedelta(hours=4)),
            WorkUpdate(work_id=1, progress_pct=38, note="Anti-skid core testing approved by quality auditor; sub-base curing ongoing.", photo_url=None, updated_by="Er. S. Kumar (Site Engineer)", created_at=now - timedelta(days=2)),
            WorkUpdate(work_id=2, progress_pct=35, note="Underground septic tank excavation complete; plumbing manifolds being fitted.", photo_url="/static/img/updates/toilet_pod.jpg", updated_by="Er. Anusha (Sanitation Incharge)", created_at=now - timedelta(hours=8)),
            WorkUpdate(work_id=3, progress_pct=50, note="Foundation casting done for 4 high-mast poles; awaiting delivery of 30m galvanised masts.", photo_url=None, updated_by="Er. Venkatesh (Electrical Lead)", created_at=now - timedelta(days=1)),
            WorkUpdate(work_id=4, progress_pct=48, note="Fabrication of 250 heavy-duty crowd barriers finished at workshop; dispatching to site.", photo_url="/static/img/updates/barricades.jpg", updated_by="Suresh Reddy (Contractor)", created_at=now - timedelta(hours=16)),
            WorkUpdate(work_id=5, progress_pct=28, note="Subgrade compaction finished for VIP parking area; heavy roller deployed for gravel base.", photo_url=None, updated_by="Er. M. Rao (Executive Engineer)", created_at=now - timedelta(days=3)),
            WorkUpdate(work_id=6, progress_pct=55, note="Steel truss framework erected for pilgrim shelter; fire-retardant fabric stretched over Bay 1.", photo_url="/static/img/updates/shelter.jpg", updated_by="B. Nagesh (Fabricator)", created_at=now - timedelta(hours=22)),
            WorkUpdate(work_id=7, progress_pct=40, note="High-capacity RO membrane unit delivered to Kotilingala pump house; electrical wiring in progress.", photo_url=None, updated_by="Ch. Subba Rao (Jaladhara)", created_at=now - timedelta(days=1, hours=10)),
            WorkUpdate(work_id=8, progress_pct=30, note="Stainless steel safety railings anchor bolting underway along downstream stairs.", photo_url=None, updated_by="Er. S. Kumar (Site Engineer)", created_at=now - timedelta(days=2, hours=5)),
            WorkUpdate(work_id=9, progress_pct=62, note="South ramp steps widening shuttering removed; concrete compressive strength test passed 28 MPa.", photo_url="/static/img/updates/concrete_test.jpg", updated_by="Er. M. Rao (Executive Engineer)", created_at=now - timedelta(hours=36)),
            WorkUpdate(work_id=10, progress_pct=72, note="Kotilingala north steps desilted; pressure washing completed across 18 tier levels.", photo_url=None, updated_by="K. Satyanarayana (Contractor)", created_at=now - timedelta(days=1, hours=2)),
            WorkUpdate(work_id=11, progress_pct=65, note="Mobile toilet drainage line connected to main sewer trunk line with backflow valve.", photo_url=None, updated_by="P. Lakshmi (Sanitation)", created_at=now - timedelta(hours=14)),
            WorkUpdate(work_id=12, progress_pct=80, note="16 out of 20 solar LED streetlights erected and tested along Pushkar promenade.", photo_url="/static/img/updates/solar_lights.jpg", updated_by="Er. Venkatesh (Electrical Lead)", created_at=now - timedelta(hours=18)),
            WorkUpdate(work_id=13, progress_pct=78, note="Riverfront deep-water security barricade floating buoys anchored with 5-tonne concrete blocks.", photo_url=None, updated_by="M. Anitha (Apex Safety)", created_at=now - timedelta(days=2)),
            WorkUpdate(work_id=14, progress_pct=85, note="Pushkar Holding Area bitumen top-coat laying completed; lane demarcation painting underway.", photo_url=None, updated_by="Er. M. Rao (Executive Engineer)", created_at=now - timedelta(hours=30)),
            WorkUpdate(work_id=15, progress_pct=70, note="Eco-friendly bamboo-thatch shelter roof completed; provides shade for 3,000 waiting pilgrims.", photo_url="/static/img/updates/shelter_bamboo.jpg", updated_by="B. Nagesh (Fabricator)", created_at=now - timedelta(days=1, hours=12)),
            WorkUpdate(work_id=16, progress_pct=82, note="Water chilling plant operational; output temperature maintained at 18 degrees Celsius.", photo_url=None, updated_by="Ch. Subba Rao (Jaladhara)", created_at=now - timedelta(hours=12)),
            WorkUpdate(work_id=17, progress_pct=68, note="Saraswati bathing platform flagstone joints sealed with epoxy water-resistant mortar.", photo_url=None, updated_by="Ravi Varma (Godavari Infra)", created_at=now - timedelta(days=2, hours=8)),
            WorkUpdate(work_id=18, progress_pct=75, note="VIP protocol air-conditioned waiting cabin interior acoustic paneling installed.", photo_url=None, updated_by="B. Nagesh (Fabricator)", created_at=now - timedelta(hours=20)),
            WorkUpdate(work_id=19, progress_pct=100, note="Commissioning certificate issued for Pushkar Central Steps. Handed over to Municipal Commissioner.", photo_url="/static/img/updates/commissioning.jpg", updated_by="Superintending Engineer (R&B)", created_at=now - timedelta(days=4)),
        ]
        db.add_all(updates_data)
        db.commit()

        # Count summary
        ghat_count = db.query(Ghat).count()
        vendor_count = db.query(Vendor).count()
        work_count = db.query(Work).count()
        asset_count = db.query(Asset).count()
        alert_count = db.query(Alert).count()
        update_count = db.query(WorkUpdate).count()

        delayed_works = db.query(Work).filter(Work.status == "delayed").count()
        delayed_pct = round((delayed_works / work_count) * 100, 1)

        faulty_assets = db.query(Asset).filter(Asset.status == "faulty").count()
        faulty_pct = round((faulty_assets / asset_count) * 100, 1)

        print("=" * 60)
        print("PUSHKAR WORKS TRACKER — DATABASE SEEDED SUCCESSFULLY")
        print("=" * 60)
        print(f"• Ghats:        {ghat_count}")
        print(f"• Vendors:      {vendor_count}")
        print(f"• Works:        {work_count}  (Delayed: {delayed_works} -> {delayed_pct}%)")
        print(f"• Assets:       {asset_count}  (Faulty: {faulty_assets} -> {faulty_pct}%)")
        print(f"• Alerts:       {alert_count}")
        print(f"• Work Updates: {update_count}")
        print("=" * 60)

        return {
            "ghats": ghat_count,
            "vendors": vendor_count,
            "works": work_count,
            "delayed_works": delayed_works,
            "delayed_pct": delayed_pct,
            "assets": asset_count,
            "faulty_assets": faulty_assets,
            "faulty_pct": faulty_pct,
            "alerts": alert_count,
            "work_updates": update_count
        }
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()

