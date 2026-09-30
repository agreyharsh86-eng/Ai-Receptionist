import os
import shutil
from pathlib import Path
import aiosqlite
from datetime import datetime, date, timedelta
from app.config import DB_PATH

_db_initialized = False

def get_effective_db_path() -> Path:
    if os.getenv("VERCEL"):
        tmp_db = Path("/tmp") / "receptionist.db"
        if not tmp_db.exists() and DB_PATH.exists():
            try:
                shutil.copy2(DB_PATH, tmp_db)
            except Exception:
                pass
        return tmp_db
    return DB_PATH

async def get_db():
    global _db_initialized
    db_path = get_effective_db_path()
    if not _db_initialized:
        await init_db()
        _db_initialized = True
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    """Create tables and populate seed data if not present."""
    global _db_initialized
    db_path = get_effective_db_path()
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        _db_initialized = True

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
        (
            "parking",
            "Facility",
            "Visitor Parking Information",
            "Visitor parking is available on levels P1 and P2 in the West Garage. Please take a parking ticket at entry and bring it to reception for validation. Validated parking is complimentary for up to 4 hours."
        ),
        (
            "conference",
            "Facility",
            "Conference Room Booking",
            "Conference rooms are available on floors 8, 10, and 12. Rooms accommodate 6 to 20 guests. External visitors should coordinate through their host for room reservations. Video conferencing equipment is available in all rooms."
        ),
    ]

    await db.executemany(
        "INSERT INTO company_info (key, category, title, content) VALUES (?, ?, ?, ?)",
        company_entries
    )

    # Seed Staff Directory — Indian professionals
    staff_members = [
        (
            "Dr. Ananya Sharma",
            "Chief Executive Officer",
            "Executive Leadership",
            "ananya.sharma@apexhorizon.com",
            "101",
            "In Board Meeting",
            "Oversees strategic direction, investor relations, and global partnerships. 15+ years in enterprise tech leadership. Urgent executive matters should be directed to executive assistant."
        ),
        (
            "Rajesh Krishnamurthy",
            "VP of Enterprise Sales",
            "Enterprise Sales",
            "rajesh.k@apexhorizon.com",
            "201",
            "Available",
            "Leads enterprise client accounts across APAC and Americas. Handles pricing negotiations, enterprise software demo bookings, and strategic alliances."
        ),
        (
            "Meera Iyer",
            "Senior Solutions Architect",
            "Enterprise Sales",
            "meera.iyer@apexhorizon.com",
            "204",
            "In Client Call",
            "Technical architecture consultations, cloud migrations, and proof-of-concept demos for enterprise clients."
        ),
        (
            "Vikram Desai",
            "Head of Engineering & Cloud",
            "Engineering",
            "vikram.desai@apexhorizon.com",
            "301",
            "Available",
            "Directs core platform engineering, cloud reliability, AI infrastructure, and DevOps. Previously at Google Cloud and Infosys."
        ),
        (
            "Priya Nair",
            "Director of People & Talent",
            "Human Resources",
            "priya.nair@apexhorizon.com",
            "401",
            "Available",
            "Handles executive recruiting, job applicant interviews, campus hiring programs, and vendor HR inquiries."
        ),
        (
            "Arjun Mehta",
            "Senior Financial Controller",
            "Finance & Billing",
            "arjun.mehta@apexhorizon.com",
            "501",
            "Out of Office",
            "Manages vendor invoicing, enterprise accounts receivable, audits, and billing inquiries. Returns next Monday."
        ),
        (
            "Kavitha Sundaram",
            "Lead Support Engineer",
            "Client Technical Support",
            "kavitha.s@apexhorizon.com",
            "601",
            "Available",
            "Handles tier-3 technical escalations, SLA client emergencies, and system uptime alerts. On-call rotation lead."
        ),
        (
            "Rohit Agarwal",
            "Senior Product Manager",
            "Product Management",
            "rohit.agarwal@apexhorizon.com",
            "701",
            "Available",
            "Leads product roadmap for AI orchestration platform. Coordinates between engineering, design, and enterprise clients."
        ),
        (
            "Deepa Venkatesh",
            "Chief Marketing Officer",
            "Marketing & Communications",
            "deepa.v@apexhorizon.com",
            "801",
            "In Team Standup",
            "Oversees brand strategy, digital campaigns, analyst relations, and corporate communications."
        ),
        (
            "Suresh Reddy",
            "Director of IT & Security",
            "Information Technology",
            "suresh.reddy@apexhorizon.com",
            "901",
            "Available",
            "Manages enterprise IT infrastructure, cybersecurity operations, compliance certifications, and network operations center."
        ),
    ]

    await db.executemany(
        "INSERT INTO staff_directory (name, title, department, email, phone_extension, status, bio) VALUES (?, ?, ?, ?, ?, ?, ?)",
        staff_members
    )

    # Seed Appointments — Indian patient/visitor names
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    day_after = (date.today() + timedelta(days=2)).isoformat()

    sample_appointments = [
        (
            "Amit Kulkarni",
            "+91-98765-43210 / amit.kulkarni@tatahealth.in",
            "Rajesh Krishnamurthy",
            "Enterprise Sales",
            today,
            "09:30 AM",
            "Enterprise Cloud Healthcare Platform Demo & Pricing Discussion",
            "Confirmed",
            (datetime.now() - timedelta(hours=18)).isoformat()
        ),
        (
            "Sneha Bhatia",
            "+91-87654-32109 / sneha.bhatia@apollogroup.com",
            "Dr. Ananya Sharma",
            "Executive Leadership",
            today,
            "11:00 AM",
            "Strategic Partnership Review — AI Diagnostics Integration",
            "Confirmed",
            (datetime.now() - timedelta(hours=12)).isoformat()
        ),
        (
            "Dr. Ravi Shankar Gupta",
            "+91-99887-76543 / ravi.gupta@maxhealthcare.in",
            "Vikram Desai",
            "Engineering",
            today,
            "02:00 PM",
            "Q3 Patient Data Pipeline Architecture Review & HIPAA Compliance",
            "Confirmed",
            (datetime.now() - timedelta(hours=8)).isoformat()
        ),
        (
            "Pooja Malhotra",
            "+91-76543-21098 / pooja.m@fortishospitals.com",
            "Priya Nair",
            "Human Resources",
            today,
            "03:30 PM",
            "Final Round Interview — Senior DevOps Engineer Position",
            "Confirmed",
            (datetime.now() - timedelta(hours=6)).isoformat()
        ),
        (
            "Kiran Joshi",
            "+91-88776-65544 / kiran.joshi@manipalhealth.org",
            "Meera Iyer",
            "Enterprise Sales",
            tomorrow,
            "10:00 AM",
            "Cloud Migration Consultation for Hospital ERP Systems",
            "Confirmed",
            (datetime.now() - timedelta(hours=4)).isoformat()
        ),
        (
            "Nandini Rao",
            "+91-99001-12233 / nandini.rao@narayanahealth.com",
            "Rohit Agarwal",
            "Product Management",
            tomorrow,
            "11:30 AM",
            "Product Roadmap Preview — AI-Powered Diagnostic Scheduling",
            "Confirmed",
            (datetime.now() - timedelta(hours=3)).isoformat()
        ),
        (
            "Sanjay Pillai",
            "+91-70098-87766 / sanjay.pillai@medanta.org",
            "Kavitha Sundaram",
            "Client Technical Support",
            tomorrow,
            "02:30 PM",
            "Priority Escalation — Production System Downtime Investigation",
            "Confirmed",
            (datetime.now() - timedelta(hours=2)).isoformat()
        ),
        (
            "Divya Choudhary",
            "+91-81234-56789 / divya.c@aiaboratories.in",
            "Vikram Desai",
            "Engineering",
            day_after,
            "10:30 AM",
            "Technical Deep-Dive — Federated ML Model Deployment on Azure",
            "Confirmed",
            (datetime.now() - timedelta(hours=1)).isoformat()
        ),
    ]

    await db.executemany(
        """INSERT INTO appointments
        (visitor_name, contact_info, staff_name, department, date, time_slot, purpose, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        sample_appointments
    )

    # Seed Caller Messages — Indian callers/patients
    sample_messages = [
        (
            "Ramesh Venkataraman",
            "+91-98123-45678",
            "Arjun Mehta",
            "Inquiring about status of invoice #INV-2026-4521 for the Cloud Security Audit project billed to Fortis Healthcare. Please call back at earliest convenience.",
            "Normal",
            0,
            (datetime.now() - timedelta(hours=1)).isoformat()
        ),
        (
            "Dr. Sunita Kapoor",
            "sunita.kapoor@apollohospitals.com",
            "Dr. Ananya Sharma",
            "Urgent follow-up regarding our discussion at the AI in Healthcare Summit. Need to finalize the Q4 advisory board composition before Friday's board meeting.",
            "Urgent",
            0,
            (datetime.now() - timedelta(hours=3)).isoformat()
        ),
        (
            "Manoj Kumar Singh",
            "+91-77889-90011",
            "Rajesh Krishnamurthy",
            "Our hospital group is interested in upgrading from Standard to Enterprise tier for 12 facilities across North India. Requesting a callback to discuss volume pricing and onboarding timeline.",
            "Normal",
            0,
            (datetime.now() - timedelta(hours=5)).isoformat()
        ),
        (
            "Lakshmi Narayanan",
            "+91-90012-34567 / lakshmi.n@medanta.org",
            "Kavitha Sundaram",
            "CRITICAL: Production patient portal is showing intermittent 502 errors since 9 AM today. Approximately 2,000 patients affected. Need immediate escalation and status update.",
            "Urgent",
            0,
            (datetime.now() - timedelta(minutes=45)).isoformat()
        ),
        (
            "Anil Dhawan",
            "+91-85567-78899",
            "Vikram Desai",
            "Following up on the API integration specs shared last week for the lab results module. Our dev team has some questions about the webhook payload format.",
            "Normal",
            0,
            (datetime.now() - timedelta(hours=7)).isoformat()
        ),
        (
            "Geeta Bhardwaj",
            "geeta.bhardwaj@narayanahealth.com",
            "Priya Nair",
            "Requesting reschedule of tomorrow's campus hiring presentation from 2 PM to 4 PM due to a board commitment. Please confirm availability of the auditorium.",
            "Normal",
            1,
            (datetime.now() - timedelta(hours=10)).isoformat()
        ),
        (
            "Dr. Harsh Vardhan Patel",
            "+91-99234-56780",
            "Rohit Agarwal",
            "Would like to provide beta feedback on the new AI scheduling module. We've been testing it across 3 departments at our Gujarat facility and have detailed notes to share.",
            "Normal",
            0,
            (datetime.now() - timedelta(hours=2)).isoformat()
        ),
    ]

    await db.executemany(
        """INSERT INTO caller_messages
        (caller_name, contact_info, recipient_name, message, urgency, is_read, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)""",
        sample_messages
    )

    # Seed Call Logs / Session History
    import uuid
    sample_call_logs = [
        (
            str(uuid.uuid4())[:8],
            "Amit Kulkarni (+91-98765-43210)",
            (datetime.now() - timedelta(hours=6, minutes=30)).isoformat(),
            (datetime.now() - timedelta(hours=6, minutes=22)).isoformat(),
            480,
            "Caller inquired about enterprise cloud platform pricing for a multi-hospital deployment. Transferred to Rajesh Krishnamurthy (Enterprise Sales). Appointment booked for today at 9:30 AM.",
            "Caller: Hello, I'd like to discuss pricing for deploying your cloud platform across our hospital network.\\nJack: Welcome to Apex Horizon Enterprises! I'd be happy to connect you with our Enterprise Sales team. Let me check availability for Rajesh Krishnamurthy.\\nCaller: That would be great, we have 8 facilities.\\nJack: I've booked an appointment with Rajesh for today at 9:30 AM. Shall I transfer you now?\\nCaller: Yes please. Thank you!",
            '[{"tool":"check_availability","args":{"staff":"Rajesh Krishnamurthy"}},{"tool":"book_appointment","args":{"visitor":"Amit Kulkarni","slot":"09:30 AM"}},{"tool":"transfer_call","args":{"recipient":"Rajesh Krishnamurthy"}}]'
        ),
        (
            str(uuid.uuid4())[:8],
            "Dr. Sunita Kapoor (Apollo Hospitals)",
            (datetime.now() - timedelta(hours=4, minutes=15)).isoformat(),
            (datetime.now() - timedelta(hours=4, minutes=10)).isoformat(),
            300,
            "Urgent call from Dr. Kapoor regarding AI Healthcare Summit follow-up. CEO was in board meeting. Urgent message recorded for Dr. Ananya Sharma.",
            "Caller: This is Dr. Sunita Kapoor from Apollo Hospitals. I need to speak with Ananya urgently about the advisory board.\\nJack: Good afternoon, Dr. Kapoor. Dr. Ananya Sharma is currently in a board meeting. Would you like me to take an urgent message?\\nCaller: Yes, please mark it urgent. We need to finalize the Q4 advisory board composition before Friday.\\nJack: I've recorded your urgent message and will ensure Dr. Sharma receives it immediately after her meeting.",
            '[{"tool":"lookup_directory","args":{"query":"Ananya Sharma"}},{"tool":"leave_message","args":{"caller":"Dr. Sunita Kapoor","recipient":"Dr. Ananya Sharma","urgency":"Urgent"}}]'
        ),
        (
            str(uuid.uuid4())[:8],
            "Lakshmi Narayanan (Medanta)",
            (datetime.now() - timedelta(minutes=50)).isoformat(),
            (datetime.now() - timedelta(minutes=42)).isoformat(),
            480,
            "Critical support escalation — production patient portal errors. Urgent message left for Kavitha Sundaram (Technical Support). Caller informed of estimated response time.",
            "Caller: We have a critical issue! Our patient portal is returning 502 errors and about 2,000 patients are affected.\\nJack: I understand the urgency. Let me check the status of our support team lead. Kavitha Sundaram is currently available — would you like me to transfer you directly?\\nCaller: Yes, and please also log this as a priority ticket.\\nJack: I've recorded an urgent message for Kavitha with all the details and I'm transferring you now. Your reference number is ESC-2026-0930.",
            '[{"tool":"lookup_directory","args":{"query":"Kavitha Sundaram"}},{"tool":"leave_message","args":{"caller":"Lakshmi Narayanan","recipient":"Kavitha Sundaram","urgency":"Urgent"}},{"tool":"transfer_call","args":{"recipient":"Kavitha Sundaram"}}]'
        ),
        (
            str(uuid.uuid4())[:8],
            "Pooja Malhotra (Fortis Hospitals)",
            (datetime.now() - timedelta(hours=2, minutes=20)).isoformat(),
            (datetime.now() - timedelta(hours=2, minutes=15)).isoformat(),
            300,
            "Candidate calling about final round interview. Confirmed appointment with Priya Nair (HR) at 3:30 PM today. Provided visitor check-in instructions.",
            "Caller: Hi, I'm Pooja Malhotra. I have an interview scheduled today.\\nJack: Welcome, Pooja! Let me pull up your appointment details. I can see you have a final round interview with Priya Nair at 3:30 PM today.\\nCaller: That's right. What do I need for check-in?\\nJack: Please bring a valid government-issued photo ID to the reception security desk on the ground floor. You'll receive a temporary visitor badge and Priya will escort you from the lobby.",
            '[{"tool":"check_availability","args":{"staff":"Priya Nair"}},{"tool":"get_company_info","args":{"topic":"visitor_policy"}}]'
        ),
        (
            str(uuid.uuid4())[:8],
            "Web Visitor",
            (datetime.now() - timedelta(hours=8)).isoformat(),
            (datetime.now() - timedelta(hours=7, minutes=52)).isoformat(),
            480,
            "General inquiry about office hours, visitor parking, and guest Wi-Fi. All information provided from knowledge base.",
            "Caller: What are your office hours and where can I park?\\nJack: Our office is open Monday through Friday, 8:30 AM to 5:30 PM EST. Visitor parking is available on levels P1 and P2 in the West Garage — just bring your ticket to reception for complimentary validation.\\nCaller: And is there guest Wi-Fi?\\nJack: Yes! Connect to 'Apex-Guest' with password 'HorizonGuest2026!' and accept the terms on the portal.",
            '[{"tool":"get_company_info","args":{"topic":"hours"}},{"tool":"get_company_info","args":{"topic":"parking"}},{"tool":"get_company_info","args":{"topic":"wifi"}}]'
        ),
    ]

    await db.executemany(
        """INSERT INTO call_logs
        (session_id, caller_identifier, started_at, ended_at, duration_seconds, summary, full_transcript, actions_taken)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        sample_call_logs
    )

    await db.commit()

