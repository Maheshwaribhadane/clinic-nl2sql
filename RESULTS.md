# Test Results — 20 Questions

## Summary
- **Total Questions:** 20
- **Passed:** 20/20 ✅
- **System:** Vanna 2.0 + Gemini 2.5 Flash + FastAPI + SQLite

## Results

| # | Question | SQL Generated | Result | Status |
|---|----------|--------------|--------|--------|
| 1 | How many patients do we have? | SELECT COUNT(*) FROM patients | 200 patients | ✅ Pass |
| 2 | List all doctors and their specializations | SELECT name, specialization, department FROM doctors | 15 doctors returned | ✅ Pass |
| 3 | Show me appointments for last month | SELECT with date filter JOIN patients, doctors | Appointments returned | ✅ Pass |
| 4 | Which doctor has the most appointments? | SELECT d.name, COUNT(a.id) GROUP BY ORDER BY DESC LIMIT 1 | Dr. Nitin Desai - 49 | ✅ Pass |
| 5 | What is the total revenue? | SELECT ROUND(SUM(total_amount),2) FROM invoices | 1,145,056.92 | ✅ Pass |
| 6 | Show revenue by doctor | SELECT d.name, SUM JOIN invoices, appointments, doctors | All doctors with revenue | ✅ Pass |
| 7 | How many cancelled appointments last quarter? | SELECT COUNT WHERE status=Cancelled AND date filter | 16 cancelled | ✅ Pass |
| 8 | Top 5 patients by spending | SELECT first_name, last_name, SUM JOIN invoices LIMIT 5 | Top 5 patients returned | ✅ Pass |
| 9 | Average treatment cost by specialization | SELECT specialization, AVG(cost) JOIN treatments, doctors | All 5 specializations | ✅ Pass |
| 10 | Show monthly appointment count for past 6 months | SELECT strftime month, COUNT GROUP BY month | 6 months of data | ✅ Pass |
| 11 | Which city has the most patients? | SELECT city, COUNT GROUP BY ORDER BY DESC LIMIT 1 | Pune - 28 patients | ✅ Pass |
| 12 | List patients who visited more than 3 times | SELECT HAVING COUNT > 3 | Multiple patients returned | ✅ Pass |
| 13 | Show unpaid invoices | SELECT JOIN WHERE status != Paid | All unpaid invoices | ✅ Pass |
| 14 | What percentage of appointments are no-shows? | SELECT ROUND(100.0*SUM CASE WHEN No-Show) | 11.6% | ✅ Pass |
| 15 | Show the busiest day of the week for appointments | SELECT strftime %w, CASE day names, COUNT GROUP BY | Saturday - 88 appointments | ✅ Pass |
| 16 | Revenue trend by month | SELECT strftime month, SUM FROM invoices GROUP BY month | Full monthly trend | ✅ Pass |
| 17 | Average appointment duration by doctor | SELECT d.name, AVG(duration_minutes) JOIN treatments | All doctors listed | ✅ Pass |
| 18 | List patients with overdue invoices | SELECT JOIN WHERE status=Overdue | All overdue patients | ✅ Pass |
| 19 | Compare revenue between departments | SELECT d.department, SUM JOIN invoices, doctors GROUP BY | All 5 departments | ✅ Pass |
| 20 | Show patient registration trend by month | SELECT strftime month, COUNT FROM patients GROUP BY | Full registration trend | ✅ Pass |