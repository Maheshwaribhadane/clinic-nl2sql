from vanna_setup import get_agent
from vanna.core.user import User
from vanna.core.tool import ToolContext

EXAMPLE_PAIRS = [
    ("How many patients do we have?",
     "SELECT COUNT(*) AS total_patients FROM patients"),
    ("List all doctors and their specializations",
     "SELECT name, specialization FROM doctors"),
    ("Which doctor has the most appointments?",
     "SELECT d.name, COUNT(a.id) AS appt_count FROM appointments a JOIN doctors d ON d.id = a.doctor_id GROUP BY d.name ORDER BY appt_count DESC LIMIT 1"),
    ("What is the total revenue?",
     "SELECT SUM(total_amount) AS total_revenue FROM invoices"),
    ("Show revenue by doctor",
     "SELECT d.name, SUM(i.total_amount) AS revenue FROM invoices i JOIN appointments a ON a.patient_id = i.patient_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.name ORDER BY revenue DESC"),
    ("Which city has the most patients?",
     "SELECT city, COUNT(*) AS count FROM patients GROUP BY city ORDER BY count DESC LIMIT 1"),
    ("Show unpaid invoices",
     "SELECT * FROM invoices WHERE status != 'Paid'"),
    ("Top 5 patients by spending",
     "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS spending FROM invoices i JOIN patients p ON p.id = i.patient_id GROUP BY p.id ORDER BY spending DESC LIMIT 5"),
    ("How many cancelled appointments last quarter?",
     "SELECT COUNT(*) AS cancelled FROM appointments WHERE status='Cancelled' AND appointment_date >= date('now','-3 months')"),
    ("Average treatment cost by specialization",
     "SELECT d.specialization, ROUND(AVG(t.cost),2) AS avg_cost FROM treatments t JOIN appointments a ON a.id = t.appointment_id JOIN doctors d ON d.id = a.doctor_id GROUP BY d.specialization"),
    ("Show monthly appointment count for past 6 months",
     "SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS count FROM appointments WHERE appointment_date >= date('now','-6 months') GROUP BY month ORDER BY month"),
    ("List patients who visited more than 3 times",
     "SELECT p.first_name, p.last_name, COUNT(a.id) AS visits FROM appointments a JOIN patients p ON p.id = a.patient_id GROUP BY p.id HAVING visits > 3"),
    ("What percentage of appointments are no-shows?",
     "SELECT ROUND(100.0 * SUM(CASE WHEN status='No-Show' THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct FROM appointments"),
    ("Revenue trend by month",
     "SELECT strftime('%Y-%m', invoice_date) AS month, SUM(total_amount) AS revenue FROM invoices GROUP BY month ORDER BY month"),
    ("List patients with overdue invoices",
     "SELECT DISTINCT p.first_name, p.last_name, p.email FROM invoices i JOIN patients p ON p.id = i.patient_id WHERE i.status='Overdue'"),
]

if __name__ == "__main__":
    print("Loading agent...")
    agent, memory = get_agent()
    print("Seeding memory with example Q&A pairs...")

    user = User(id="default_user", name="Clinic User")
    tool_context = ToolContext(
        user=user,
        conversation_id="seed-001",
        request_id="seed-req-001",
        agent_memory=memory,
        metadata={}
    )

    for i, (question, sql) in enumerate(EXAMPLE_PAIRS, 1):
        content = f"Question: {question}\nSQL: {sql}"
        memory.save_text_memory(content=content, context=tool_context)
        print(f"✅ {i}/15 Saved: {question[:55]}...")

    print(f"\n🎯 Done! Seeded {len(EXAMPLE_PAIRS)} Q&A pairs into agent memory.")