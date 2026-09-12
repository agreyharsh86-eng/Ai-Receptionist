import aiosqlite
from datetime import datetime, date, timedelta
from app.config import DB_PATH

async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    """Create tables and populate seed data if not present."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")

        # 1. Company Information / Knowledge Base
        await db.execute("""
            CREATE TABLE IF NOT EXISTS company_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)

        # 2. Staff Directory
        await db.execute("""
            CREATE TABLE IF NOT EXISTS staff_directory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                title TEXT NOT NULL,
                department TEXT NOT NULL,
                email TEXT NOT NULL,
                phone_extension TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Available',
                bio TEXT
            )
        """)

        # 3. Appointments
        await db.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                visitor_name TEXT NOT NULL,
                contact_info TEXT NOT NULL,
                staff_name TEXT NOT NULL,
                department TEXT NOT NULL,
                date TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                purpose TEXT,
                status TEXT NOT NULL DEFAULT 'Confirmed',
                created_at TEXT NOT NULL
            )
        """)

        # 4. Caller Messages / Inquiries
        await db.execute("""
            CREATE TABLE IF NOT EXISTS caller_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                caller_name TEXT NOT NULL,
                contact_info TEXT NOT NULL,
                recipient_name TEXT NOT NULL,
                message TEXT NOT NULL,
                urgency TEXT NOT NULL DEFAULT 'Normal',
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        # 5. Call Logs / Transcripts
        await db.execute("""
            CREATE TABLE IF NOT EXISTS call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                caller_identifier TEXT DEFAULT 'Web Visitor',
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_seconds INTEGER DEFAULT 0,
                summary TEXT,
                full_transcript TEXT,
                actions_taken TEXT
            )
        """)

        await db.commit()

        # Seed data if empty
        async with db.execute("SELECT COUNT(*) FROM staff_directory") as cursor:
            row = await cursor.fetchone()
            if row[0] == 0:
                await seed_database(db)

async def seed_database(db):
    """Seed corporate directory and knowledge base with rich enterprise context."""
    # Seed Company Info
    company_entries = [
        (
            "hours",
            "General",
            "Operating Hours",
            "Our corporate office is open Monday through Friday, 8:30 AM to 5:30 PM EST. We are closed on weekends and major federal holidays."
        ),
        (
            "location",
            "Facility",
            "Office Address & Directions",
            "Apex Horizon Enterprises is located at Tower 4, Suite 1200, 500 Silicon Vista Way, Innovation District. Visitor parking is located on levels P1 and P2 in the West Garage (validated at reception). Public transit: Metro Red Line to Silicon Center Station, Exit B."
        ),
        (
            "visitor_policy",
            "Security",
            "Visitor Check-in & Security",
            "All visitors must present a valid government-issued photo ID at the reception security desk on the ground floor to obtain a temporary visitor badge. Visitors must be escorted by their host beyond the turnstiles."
        ),
        (
            "wifi",
            "Facility",
            "Guest Wi-Fi Network",
            "High-speed guest Wi-Fi is available across all floors. Network name: 'Apex-Guest'. Password: 'HorizonGuest2026!'. Accept the terms of service on the captive portal to connect."
        ),
        (
            "deliveries",
            "Operations",
            "Mail, Packages & Courier Drop-offs",
            "Deliveries and courier drop-offs (FedEx, UPS, DHL, food delivery) should be directed to the Central Loading Dock on B1 between 8:00 AM and 4:30 PM, or left with security at the 1st floor courier desk."
        ),
        (
            "amenities",
            "Facility",
            "Dining & Amenities",
            "The 4th Floor Sky Lounge Bistro offers artisan coffee, breakfast, and lunch from 7:30 AM to 3:00 PM. Mother's nursing rooms and quiet wellness rooms are available on floors 11 and 12."
        ),
        (
            "about",
            "Company",
            "About Apex Horizon Enterprises",
            "Apex Horizon Enterprises provides enterprise cloud infrastructure, AI orchestration platforms, and high-performance business solutions for Fortune 500 organizations worldwide."
        ),
    ]

    await db.executemany(
        "INSERT INTO company_info (key, category, title, content) VALUES (?, ?, ?, ?)",
        company_entries
    )

    # Seed Staff Directory
    staff_members = [
        (
            "Elena Vance",
            "Chief Executive Officer",
            "Executive Leadership",
            "elena.vance@apexhorizon.com",
            "101",
            "In Board Meeting",
            "Oversees strategic direction and partnerships. Urgent executive matters should be directed to executive assistant."
        ),
        (
            "Marcus Sterling",
            "VP of Enterprise Sales",
            "Enterprise Sales",
            "marcus.sterling@apexhorizon.com",
            "201",
            "Available",
            "Leads enterprise client accounts, pricing negotiations, and enterprise software demo bookings."
        ),
        (
            "Sarah Jenkins",
            "Senior Solutions Architect",
            "Enterprise Sales",
            "sarah.jenkins@apexhorizon.com",
            "204",
            "In Client Call",
            "Technical architecture consultations, cloud migrations, and proof-of-concept demos."
        ),
        (
            "David Chen",
            "Head of Engineering & Cloud",
            "Engineering",
            "david.chen@apexhorizon.com",
            "301",
            "Available",
            "Directs core platform engineering, cloud reliability, and AI infrastructure."
        ),
        (
            "Priya Patel",
            "Director of People & Talent",
            "Human Resources",
            "priya.patel@apexhorizon.com",
            "401",
            "Available",
            "Handles executive recruiting, job applicant interviews, campus hiring, and vendor HR inquiries."
        ),
        (
            "Michael Torres",
            "Senior Financial Controller",
            "Finance & Billing",
            "michael.torres@apexhorizon.com",
            "501",
            "Out of Office",
            "Manages vendor invoicing, enterprise accounts receivable, audits, and billing inquiries. Returns Monday."
        ),
        (
            "Jessica Wong",
            "Lead Support Engineer",
            "Client Technical Support",
            "jessica.wong@apexhorizon.com",
            "601",
            "Available",
            "Handles tier-3 technical escalations, SLA client emergencies, and system uptime alerts."
        ),
    ]

    await db.executemany(
        "INSERT INTO staff_directory (name, title, department, email, phone_extension, status, bio) VALUES (?, ?, ?, ?, ?, ?, ?)",
        staff_members
    )

    # Seed Upcoming Appointments for today and tomorrow
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    sample_appointments = [
        (
            "Arthur Pendelton",
            "+1-555-0192 / arthur@acmecorp.com",
            "Marcus Sterling",
            "Enterprise Sales",
            today,
            "10:00 AM",
            "Annual Enterprise Cloud Renewal Discussion",
            "Confirmed",
            datetime.now().isoformat()
        ),
        (
            "Samantha Reed",
            "+1-555-0144 / s.reed@fintechgroup.io",
            "Priya Patel",
            "Human Resources",
            tomorrow,
            "11:30 AM",
            "Final round interview for Principal Engineer",
            "Confirmed",
            datetime.now().isoformat()
        ),
        (
            "Carlos Mendez",
            "+1-555-0188 / c.mendez@cloudsystems.net",
            "David Chen",
            "Engineering",
            tomorrow,
            "03:00 PM",
            "Q3 Data Pipeline Architecture Review",
            "Confirmed",
            datetime.now().isoformat()
        ),
    ]

    await db.executemany(
        """INSERT INTO appointments
        (visitor_name, contact_info, staff_name, department, date, time_slot, purpose, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        sample_appointments
    )

    # Seed Sample Messages
    sample_messages = [
        (
            "Robert Taylor",
            "+1-555-0129",
            "Michael Torres",
            "Inquiring about status of invoice #INV-2026-981 for Cloud Security audit.",
            "Normal",
            0,
            (datetime.now() - timedelta(hours=2)).isoformat()
        ),
        (
            "Evelyn Cross",
            "evelyn.cross@summitcapital.com",
            "Elena Vance",
            "Following up on our discussion at the AI Governance Summit regarding Q4 advisory board.",
            "Urgent",
            0,
            (datetime.now() - timedelta(hours=5)).isoformat()
        )
    ]

    await db.executemany(
        """INSERT INTO caller_messages
        (caller_name, contact_info, recipient_name, message, urgency, is_read, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        sample_messages
    )

    await db.commit()
