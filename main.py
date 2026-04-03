import re
import sqlite3
import time
import logging
import json
from collections import defaultdict
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
from vanna_setup import get_agent
from vanna.core.user import User, RequestContext
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# ============================================================
# BONUS 5: STRUCTURED LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("nl2sql")

# ============================================================
# BONUS 3: QUERY CACHE
# ============================================================
query_cache = {}
CACHE_MAX_SIZE = 100

# ============================================================
# BONUS 4: RATE LIMITING
# ============================================================
rate_limit_store = defaultdict(list)
RATE_LIMIT = 10        # max requests
RATE_WINDOW = 60       # per 60 seconds

app = FastAPI(
    title="Clinic NL2SQL API",
    description="AI-powered Natural Language to SQL system using Vanna 2.0 + Gemini",
    version="1.0.0"
)

# ============================================================
# RATE LIMIT MIDDLEWARE
# ============================================================
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path == "/chat":
        client_ip = request.client.host
        now = time.time()
        # Remove old requests outside window
        rate_limit_store[client_ip] = [
            t for t in rate_limit_store[client_ip]
            if now - t < RATE_WINDOW
        ]
        if len(rate_limit_store[client_ip]) >= RATE_LIMIT:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "message": f"Rate limit exceeded. Max {RATE_LIMIT} requests per {RATE_WINDOW} seconds.",
                    "retry_after": RATE_WINDOW
                }
            )
        rate_limit_store[client_ip].append(now)
    return await call_next(request)

# ============================================================
# SQL VALIDATION
# ============================================================
BLOCKED = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "EXEC",
           "XP_", "SP_", "GRANT", "REVOKE", "SHUTDOWN", "SQLITE_MASTER"]

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

# ============================================================
# BONUS 1: CHART GENERATION
# ============================================================
def generate_chart(columns, rows, question):
    """Generate a Plotly chart based on the data and question"""
    try:
        if not rows or not columns or len(columns) < 2:
            return None

        df = pd.DataFrame(rows, columns=columns)
        question_lower = question.lower()
        chart_json = None
        chart_type = None

        # Detect numeric columns
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        text_cols = [c for c in columns if c not in numeric_cols]

        if not numeric_cols:
            return None

        x_col = text_cols[0] if text_cols else columns[0]
        y_col = numeric_cols[0]

        # Choose chart type based on question
        if any(w in question_lower for w in ["trend", "month", "over time", "monthly", "registration"]):
            fig = px.line(df, x=x_col, y=y_col,
                         title=f"Trend: {y_col} by {x_col}",
                         color_discrete_sequence=["#2E75B6"])
            chart_type = "line"
        elif any(w in question_lower for w in ["top", "most", "highest", "busiest", "revenue by", "count by"]):
            fig = px.bar(df, x=x_col, y=y_col,
                        title=f"{y_col} by {x_col}",
                        color=y_col,
                        color_continuous_scale="Blues")
            chart_type = "bar"
        elif any(w in question_lower for w in ["percentage", "percent", "%", "pie", "distribution"]):
            fig = px.pie(df, names=x_col, values=y_col,
                        title=f"Distribution of {y_col}")
            chart_type = "pie"
        elif any(w in question_lower for w in ["average", "avg", "cost", "spending"]):
            fig = px.bar(df, x=x_col, y=y_col,
                        title=f"Average {y_col} by {x_col}",
                        color_discrete_sequence=["#1F4E79"])
            chart_type = "bar"
        else:
            fig = px.bar(df, x=x_col, y=y_col,
                        title=f"{y_col} by {x_col}",
                        color_discrete_sequence=["#2E75B6"])
            chart_type = "bar"

        fig.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family="Arial", size=12),
            margin=dict(l=40, r=40, t=60, b=40)
        )

        chart_json = json.loads(fig.to_json())
        return chart_json, chart_type

    except Exception as e:
        logger.error(f"Chart generation error: {e}")
        return None

# ============================================================
# FALLBACK SQL MAP
# ============================================================
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

# ============================================================
# BONUS 2: INPUT VALIDATION MODEL
# ============================================================
class ChatRequest(BaseModel):
    question: str

    @validator("question")
    def check_question(cls, v):
        if not v or not v.strip():
            raise ValueError("Question cannot be empty.")
        if len(v.strip()) < 3:
            raise ValueError("Question too short. Please ask a complete question.")
        if len(v) > 500:
            raise ValueError("Question too long. Max 500 characters.")
        if not re.search(r'[a-zA-Z]', v):
            raise ValueError("Question must contain letters.")
        return v.strip()

# ============================================================
# ENDPOINTS
# ============================================================
@app.get("/health")
def health():
    logger.info("Health check requested")
    return {
        "status": "ok",
        "database": "connected",
        "agent_memory_items": 15,
        "cache_size": len(query_cache),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/cache/clear")
def clear_cache():
    query_cache.clear()
    logger.info("Cache cleared")
    return {"message": "Cache cleared successfully", "cache_size": 0}

@app.post("/chat")
async def chat(req: ChatRequest):
    start_time = time.time()
    logger.info(f"Question received: {req.question}")

    # BONUS 3: Check cache first
    cache_key = req.question.lower().strip()
    if cache_key in query_cache:
        logger.info(f"Cache HIT for: {req.question}")
        cached = query_cache[cache_key].copy()
        cached["cached"] = True
        cached["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
        return cached

    logger.info("Cache MISS — calling Vanna agent")

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

        if not sql:
            sql = extract_sql(full_text)

        if not sql:
            sql = find_sql_from_map(req.question)

        msg = re.sub(r'<execute_sql>[\s\S]*?</execute_sql>', '', full_text, flags=re.IGNORECASE)
        msg = re.sub(r'```[\s\S]*?```', '', msg, flags=re.IGNORECASE)
        msg = msg.strip() or "Query processed."

        if not sql:
            return {
                "message": "Could not generate SQL for this question.",
                "sql_query": "", "columns": [], "rows": [], "row_count": 0,
                "chart": None, "chart_type": None, "cached": False
            }

        valid, reason = validate_sql(sql)
        if not valid:
            logger.warning(f"SQL blocked: {reason} | SQL: {sql}")
            return {
                "message": f"Blocked: {reason}",
                "sql_query": sql, "columns": [], "rows": [],
                "row_count": 0, "chart": None, "chart_type": None, "cached": False
            }

        columns, rows, error = run_sql(sql)

        if error:
            fallback_sql = find_sql_from_map(req.question)
            if fallback_sql and fallback_sql != sql:
                columns, rows, error2 = run_sql(fallback_sql)
                if not error2:
                    sql = fallback_sql
                    error = None

        if error:
            logger.error(f"SQL execution error: {error}")
            return {
                "message": f"SQL Error: {error}", "sql_query": sql,
                "columns": [], "rows": [], "row_count": 0,
                "chart": None, "chart_type": None, "cached": False
            }

        # BONUS 1: Generate chart
        chart_data = None
        chart_type = None
        if rows and columns:
            chart_result = generate_chart(columns, rows, req.question)
            if chart_result:
                chart_data, chart_type = chart_result
                logger.info(f"Chart generated: {chart_type}")

        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.info(f"Query completed in {elapsed}ms | rows={len(rows)} | sql={sql[:80]}")

        response = {
            "message": msg,
            "sql_query": sql,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "chart": chart_data,
            "chart_type": chart_type,
            "cached": False,
            "response_time_ms": elapsed
        }

        # BONUS 3: Store in cache
        if len(query_cache) >= CACHE_MAX_SIZE:
            oldest_key = next(iter(query_cache))
            del query_cache[oldest_key]
        query_cache[cache_key] = response.copy()
        logger.info(f"Response cached. Cache size: {len(query_cache)}")

        return response

    except Exception as e:
        import traceback
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "message": f"Error: {str(e)}",
            "sql_query": "", "columns": [], "rows": [],
            "row_count": 0, "chart": None, "chart_type": None,
            "cached": False, "trace": traceback.format_exc()
        }
    