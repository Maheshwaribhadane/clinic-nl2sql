import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "clinic.db"

def create_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.executescript("""
    DROP TABLE IF EXISTS treatments;
    DROP TABLE IF EXISTS invoices;
    DROP TABLE IF EXISTS appointments;
    DROP TABLE IF EXISTS patients;
    DROP TABLE IF EXISTS doctors;

    CREATE TABLE patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL, last_name TEXT NOT NULL,
        email TEXT, phone TEXT, date_of_birth DATE,
        gender TEXT, city TEXT, registered_date DATE
    );
    CREATE TABLE doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, specialization TEXT,
        department TEXT, phone TEXT
    );
    CREATE TABLE appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER, doctor_id INTEGER,
        appointment_date DATETIME, status TEXT, notes TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(id),
        FOREIGN KEY(doctor_id) REFERENCES doctors(id)
    );
    CREATE TABLE treatments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        appointment_id INTEGER, treatment_name TEXT,
        cost REAL, duration_minutes INTEGER,
        FOREIGN KEY(appointment_id) REFERENCES appointments(id)
    );
    CREATE TABLE invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER, invoice_date DATE,
        total_amount REAL, paid_amount REAL, status TEXT,
        FOREIGN KEY(patient_id) REFERENCES patients(id)
    );
    """)

    doctor_names = [
        ("Dr. Anil Sharma","Cardiology","Cardiology Dept"),
        ("Dr. Priya Mehta","Dermatology","Skin Clinic"),
        ("Dr. Ravi Kumar","Orthopedics","Bone & Joint"),
        ("Dr. Sunita Patel","General","OPD"),
        ("Dr. Manish Gupta","Pediatrics","Child Health"),
        ("Dr. Deepa Nair","Cardiology","Cardiology Dept"),
        ("Dr. Arjun Singh","Dermatology","Skin Clinic"),
        ("Dr. Kavya Rao","Orthopedics","Bone & Joint"),
        ("Dr. Vikram Joshi","General","OPD"),
        ("Dr. Rekha Verma","Pediatrics","Child Health"),
        ("Dr. Nitin Desai","Cardiology","Cardiology Dept"),
        ("Dr. Pooja Iyer","General","OPD"),
        ("Dr. Suresh Patil","Orthopedics","Bone & Joint"),
        ("Dr. Anjali Das","Dermatology","Skin Clinic"),
        ("Dr. Kiran Bhatt","Pediatrics","Child Health"),
    ]
    for name, spec, dept in doctor_names:
        cur.execute(
            "INSERT INTO doctors(name,specialization,department,phone) VALUES(?,?,?,?)",
            (name, spec, dept, f"98{random.randint(10000000,99999999)}")
        )

    first_names = ["Aarav","Ananya","Rohit","Priya","Sanjay","Kavita",
                   "Rahul","Sneha","Amit","Pooja","Vikas","Meera",
                   "Suresh","Nisha","Rajesh","Divya","Arun","Swati",
                   "Manoj","Rekha"]
    last_names = ["Sharma","Patel","Singh","Kumar","Mehta",
                  "Joshi","Gupta","Nair","Verma","Desai"]
    cities = ["Mumbai","Pune","Delhi","Bangalore","Nashik",
              "Hyderabad","Chennai","Surat","Jaipur","Kolkata"]
    base_date = datetime.now()

    for i in range(200):
        dob = base_date - timedelta(days=random.randint(6570,25550))
        reg = base_date - timedelta(days=random.randint(1,365))
        email = f"user{i}@example.com" if random.random() > 0.15 else None
        phone = f"9{random.randint(100000000,999999999)}" if random.random() > 0.1 else None
        cur.execute(
            "INSERT INTO patients(first_name,last_name,email,phone,date_of_birth,gender,city,registered_date) VALUES(?,?,?,?,?,?,?,?)",
            (random.choice(first_names), random.choice(last_names),
             email, phone, dob.date(),
             random.choice(["M","F"]),
             random.choice(cities), reg.date())
        )

    statuses = ["Scheduled","Completed","Cancelled","No-Show"]
    weights = [0.2, 0.55, 0.15, 0.10]
    completed_ids = []
    for _ in range(500):
        pid = random.randint(1,200)
        did = random.randint(1,15)
        appt_date = base_date - timedelta(days=random.randint(0,365))
        status = random.choices(statuses, weights)[0]
        notes = "Regular checkup" if random.random() > 0.3 else None
        cur.execute(
            "INSERT INTO appointments(patient_id,doctor_id,appointment_date,status,notes) VALUES(?,?,?,?,?)",
            (pid, did, appt_date.strftime("%Y-%m-%d %H:%M"), status, notes)
        )
        if status == "Completed":
            completed_ids.append(cur.lastrowid)

    treatment_names = ["Blood Test","X-Ray","ECG","Skin Biopsy",
                       "Vaccination","MRI Scan","Consultation","Physiotherapy"]
    for appt_id in random.sample(completed_ids, min(350, len(completed_ids))):
        cur.execute(
            "INSERT INTO treatments(appointment_id,treatment_name,cost,duration_minutes) VALUES(?,?,?,?)",
            (appt_id, random.choice(treatment_names),
             round(random.uniform(50,5000),2),
             random.randint(15,120))
        )

    inv_statuses = ["Paid","Pending","Overdue"]
    inv_weights = [0.5, 0.3, 0.2]
    for _ in range(300):
        pid = random.randint(1,200)
        inv_date = base_date - timedelta(days=random.randint(0,365))
        total = round(random.uniform(200,8000),2)
        status = random.choices(inv_statuses, inv_weights)[0]
        paid = total if status == "Paid" else round(total * random.uniform(0,0.5),2)
        cur.execute(
            "INSERT INTO invoices(patient_id,invoice_date,total_amount,paid_amount,status) VALUES(?,?,?,?,?)",
            (pid, inv_date.date(), total, paid, status)
        )

    conn.commit()
    conn.close()
    print("✅ Database created successfully!")
    print("✅ Created 15 doctors")
    print("✅ Created 200 patients")
    print("✅ Created 500 appointments")
    print("✅ Created treatments & 300 invoices")
    print("✅ clinic.db file is ready!")

if __name__ == "__main__":
    create_database()