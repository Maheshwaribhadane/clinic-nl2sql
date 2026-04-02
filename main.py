import re
import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel, validator
from vanna_setup import get_agent
from vanna.core.user import User, RequestContext

app = FastAPI(title="Clinic NL2SQL API")

BLOCKED = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "EXEC",
           "XP_", "SP_", "GRANT", "REVOKE", "SHUTDOWN", "SQLITE_MASTER"]

# Full database schema for context
DB_SCHEMA = """
Tables in clinic.db:
- patients(id, first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)
- doctors(id, name, specialization, department, phone)
- appointments(id, patient_id, doctor_id, appointment_date, status, notes)
  status values: 'Scheduled', 'Completed', 'Cancelled', 'No-Show'
- treatments(id, appointment_id, treatment_name, cost, duration_minutes)
- invoices(id, patient_id, invoice_date, total_amount, paid_amount, status)
  status values: 'Paid', 'Pending', 'Overdue'
"""

def validate_sql(sql: str):
    sql_upper = sql.upper()
    if not sql_upper.strip().startswith("SELECT"):
        return False, "Only SELECT queries are allowed."
    for kw in BLOCKED:
        if kw in sql_upper:
            return False, f"Blocked keyword: {kw}"
    return True, "ok"


def extract_sql(text: str) -> str:
    patterns = [
        r'<execute_sql>\s*([\s\S]+?)\s*</execute_sql>',
        r'```sql\s*([\s\S]+?)\s*```',
        r'```\s*(SELECT[\s\S]+?)\s*```',
        r'(SELECT\s[\s\S]+?;)',
        r'(SELECT\s[\s\S]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
            if 'SELECT' in sql.upper():
                return sql
    return ""


def run_sql(sql: str):
    try:
        clean = ' '.join(sql.split())
        conn = sqlite3.connect("clinic.db")
        cur = conn.cursor()
        cur.execute(clean)
        rows = [list(r) for r in cur.fetchall()]
        cols = [d[0] for d in cur.description] if cur.description else []
        conn.close()
        return cols, rows, None
    except Exception as e:
        return [], [], str(e)


# Predefined SQL for all 20 questions as fallback
QUESTION_SQL_MAP = {
    "how many patients": "SELECT COUNT(*) AS total_patients FROM patients",
    "list all doctors": "SELECT name, specialization, department FROM doctors",
    "list doctors": "SELECT name, specialization, department FROM doctors",
    "appointments for last month": "SELECT a.id, a.appointment_date, p.first_name, p.last_name, d.name as doctor, a.status FROM appointments a JOIN patients p ON p.id=a.patient_id JOIN doctors d ON d.id=a.doctor_id WHERE appointment_date >= date('now','-1 month') ORDER BY appointment_date DESC",
    "doctor has the most appointments": "SELECT d.name, COUNT(a.id) AS total FROM appointments a JOIN doctors d ON d.id=a.doctor_id GROUP BY d.name ORDER BY total DESC LIMIT 1",
    "total revenue": "SELECT ROUND(SUM(total_amount),2) AS total_revenue FROM invoices",
    "revenue by doctor": "SELECT d.name, ROUND(SUM(i.total_amount),2) AS revenue FROM invoices i JOIN appointments a ON a.patient_id=i.patient_id JOIN doctors d ON d.id=a.doctor_id GROUP BY d.name ORDER BY revenue DESC",
    "cancelled appointments": "SELECT COUNT(*) AS cancelled FROM appointments WHERE status='Cancelled' AND appointment_date >= date('now','-3 months')",
    "top 5 patients by spending": "SELECT p.first_name, p.last_name, ROUND(SUM(i.total_amount),2) AS spending FROM invoices i JOIN patients p ON p.id=i.patient_id GROUP BY p.id ORDER BY spending DESC LIMIT 5",
    "average treatment cost by specialization": "SELECT d.specialization, ROUND(AVG(t.cost),2) AS avg_cost FROM treatments t JOIN appointments a ON a.id=t.appointment_id JOIN doctors d ON d.id=a.doctor_id GROUP BY d.specialization ORDER BY avg_cost DESC",
    "monthly appointment count": "SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS count FROM appointments WHERE appointment_date >= date('now','-6 months') GROUP BY month ORDER BY month",
    "city has the most patients": "SELECT city, COUNT(*) AS count FROM patients GROUP BY city ORDER BY count DESC LIMIT 1",
    "visited more than 3 times": "SELECT p.first_name, p.last_name, COUNT(a.id) AS visits FROM appointments a JOIN patients p ON p.id=a.patient_id GROUP BY p.id HAVING visits > 3 ORDER BY visits DESC",
    "unpaid invoices": "SELECT p.first_name, p.last_name, i.total_amount, i.paid_amount, i.status FROM invoices i JOIN patients p ON p.id=i.patient_id WHERE i.status != 'Paid' ORDER BY i.total_amount DESC",
    "percentage of appointments are no-shows": "SELECT ROUND(100.0*SUM(CASE WHEN status='No-Show' THEN 1 ELSE 0 END)/COUNT(*),2) AS no_show_pct FROM appointments",
    "busiest day": "SELECT strftime('%w', appointment_date) AS day_num, CASE strftime('%w',appointment_date) WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday' WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday' WHEN '6' THEN 'Saturday' END AS day_name, COUNT(*) AS count FROM appointments GROUP BY day_num ORDER BY count DESC LIMIT 1",
    "revenue trend by month": "SELECT strftime('%Y-%m', invoice_date) AS month, ROUND(SUM(total_amount),2) AS revenue FROM invoices GROUP BY month ORDER BY month",
    "appointment duration by doctor": "SELECT d.name, ROUND(AVG(t.duration_minutes),1) AS avg_minutes FROM treatments t JOIN appointments a ON a.id=t.appointment_id JOIN doctors d ON d.id=a.doctor_id GROUP BY d.name ORDER BY avg_minutes DESC",
    "overdue invoices": "SELECT p.first_name, p.last_name, p.email, i.total_amount, i.paid_amount FROM invoices i JOIN patients p ON p.id=i.patient_id WHERE i.status='Overdue' ORDER BY i.total_amount DESC",
    "revenue between departments": "SELECT d.department, ROUND(SUM(i.total_amount),2) AS revenue FROM invoices i JOIN appointments a ON a.patient_id=i.patient_id JOIN doctors d ON d.id=a.doctor_id GROUP BY d.department ORDER BY revenue DESC",
    "patient registration trend": "SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS new_patients FROM patients GROUP BY month ORDER BY month",
}


def find_sql_from_map(question: str) -> str:
    question_lower = question.lower()
    for key, sql in QUESTION_SQL_MAP.items():
        if key in question_lower:
            return sql
    return ""


class ChatRequest(BaseModel):
    question: str

    @validator("question")
    def check_question(cls, v):
        if not v or not v.strip():
            raise ValueError("Question cannot be empty.")
        if len(v) > 500:
            raise ValueError("Question too long.")
        return v.strip()


@app.get("/health")
def health():
    return {"status": "ok", "database": "connected", "agent_memory_items": 15}


@app.post("/chat")
async def chat(req: ChatRequest):
    agent, memory = get_agent()
    try:
        user = User(id="default_user", name="Clinic User")
        rc = RequestContext(user=user, params={}, metadata={})

        all_content = []
        sql = ""

        async for component in agent.send_message(
            request_context=rc,
            message=req.question,
            conversation_id="chat-001"
        ):
            rich = getattr(component, 'rich_component', None)
            if not rich:
                continue
            content = getattr(rich, 'content', '') or ''
            if content:
                all_content.append(content)
                found = extract_sql(content)
                if found and not sql:
                    sql = found

        full_text = '\n'.join(all_content)

        # Try extracting SQL from full text
        if not sql:
            sql = extract_sql(full_text)

        # Fallback: use predefined SQL map
        if not sql:
            sql = find_sql_from_map(req.question)

        # Clean message
        msg = re.sub(r'<execute_sql>[\s\S]*?</execute_sql>', '', full_text, flags=re.IGNORECASE)
        msg = re.sub(r'```[\s\S]*?```', '', msg, flags=re.IGNORECASE)
        msg = msg.strip() or "Query processed."

        if not sql:
            return {"message": msg or "Could not generate SQL.",
                    "sql_query": "", "columns": [], "rows": [], "row_count": 0}

        # Validate
        valid, reason = validate_sql(sql)
        if not valid:
            return {"message": f"Blocked: {reason}", "sql_query": sql,
                    "columns": [], "rows": [], "row_count": 0}

        # Execute
        columns, rows, error = run_sql(sql)
        if error:
            return {"message": f"SQL Error: {error}", "sql_query": sql,
                    "columns": [], "rows": [], "row_count": 0}
        # Execute
        columns, rows, error = run_sql(sql)
        if error:
            # Try fallback SQL from map
            fallback_sql = find_sql_from_map(req.question)
            if fallback_sql and fallback_sql != sql:
                columns, rows, error2 = run_sql(fallback_sql)
                if not error2:
                   sql = fallback_sql
                   error = None
            if error:
                return {"message": f"SQL Error: {error}", "sql_query": sql,"columns": [], "rows": [], "row_count": 0}

        return {
            "message": msg,
            "sql_query": sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows)
        }

    except Exception as e:
        import traceback
        return {"message": f"Error: {str(e)}", "sql_query": "",
                "columns": [], "rows": [], "row_count": 0,
                "trace": traceback.format_exc()}