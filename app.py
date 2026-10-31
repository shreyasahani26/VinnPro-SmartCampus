import os, io, csv, sqlite3
from functools import wraps
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(APP_DIR, "campus.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-before-deployment")
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        course TEXT NOT NULL,
        year INTEGER NOT NULL DEFAULT 1,
        status TEXT NOT NULL DEFAULT 'Active',
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS faculty (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        department TEXT NOT NULL,
        workload INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        attendance_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present','Absent','Late')),
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
        UNIQUE(student_id, attendance_date)
    );
    CREATE TABLE IF NOT EXISTS timetable (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        day TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        subject TEXT NOT NULL,
        faculty_name TEXT NOT NULL,
        room TEXT NOT NULL
    );
    """)
    db.commit()

@app.before_request
def prepare_db():
    init_db()

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_globals():
    return {"current_user": session.get("user_name"), "today": date.today().isoformat()}

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password with at least 8 characters.", "danger")
            return render_template("register.html")
        db = get_db()
        try:
            db.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                       (name, email, generate_password_hash(password)))
            db.commit()
        except sqlite3.IntegrityError:
            flash("An account with this email already exists.", "danger")
            return render_template("register.html")
        flash("Account created. You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session.permanent = True
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    stats = {
        "students": db.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        "faculty": db.execute("SELECT COUNT(*) FROM faculty").fetchone()[0],
        "present_today": db.execute("SELECT COUNT(*) FROM attendance WHERE attendance_date=? AND status='Present'", (today_iso(),)).fetchone()[0],
        "classes": db.execute("SELECT COUNT(*) FROM timetable").fetchone()[0],
    }
    total_today = db.execute("SELECT COUNT(*) FROM attendance WHERE attendance_date=?", (today_iso(),)).fetchone()[0]
    stats["attendance_rate"] = round(stats["present_today"] * 100 / total_today) if total_today else 0
    recent = db.execute("""SELECT a.attendance_date, a.status, s.name, s.course
                           FROM attendance a JOIN students s ON s.id=a.student_id
                           ORDER BY a.attendance_date DESC, a.id DESC LIMIT 7""").fetchall()
    upcoming = db.execute("SELECT * FROM timetable ORDER BY day, start_time LIMIT 6").fetchall()
    return render_template("dashboard.html", stats=stats, recent=recent, upcoming=upcoming)

def today_iso():
    return date.today().isoformat()

@app.route("/students", methods=["GET", "POST"])
@login_required
def students():
    db = get_db()
    if request.method == "POST":
        name, email = request.form.get("name","").strip(), request.form.get("email","").strip()
        course = request.form.get("course","").strip()
        try: year = max(1, min(8, int(request.form.get("year","1"))))
        except ValueError: year = 1
        if not name or not email or not course:
            flash("Name, email, and course are required.", "danger")
        else:
            db.execute("INSERT INTO students(name,email,course,year,status) VALUES(?,?,?,?,?)",
                       (name,email,course,year,request.form.get("status","Active")))
            db.commit(); flash("Student added.", "success")
        return redirect(url_for("students"))
    rows = db.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    return render_template("students.html", students=rows)

@app.post("/students/<int:student_id>/delete")
@login_required
def delete_student(student_id):
    db = get_db()
    db.execute("DELETE FROM students WHERE id=?", (student_id,))
    db.commit()
    flash("Student deleted if the record existed.", "success")
    return redirect(url_for("students"))

@app.route("/faculty", methods=["GET", "POST"])
@login_required
def faculty():
    db = get_db()
    if request.method == "POST":
        name, email, department = (request.form.get(k,"").strip() for k in ("name","email","department"))
        try: workload = max(0, int(request.form.get("workload","0")))
        except ValueError: workload = 0
        if not name or not email or not department:
            flash("Name, email, and department are required.", "danger")
        else:
            db.execute("INSERT INTO faculty(name,email,department,workload) VALUES(?,?,?,?)",
                       (name,email,department,workload)); db.commit()
            flash("Faculty member added.", "success")
        return redirect(url_for("faculty"))
    rows = db.execute("SELECT * FROM faculty ORDER BY name").fetchall()
    return render_template("faculty.html", faculty=rows)

@app.post("/faculty/<int:faculty_id>/delete")
@login_required
def delete_faculty(faculty_id):
    db = get_db(); db.execute("DELETE FROM faculty WHERE id=?", (faculty_id,)); db.commit()
    flash("Faculty record deleted if it existed.", "success")
    return redirect(url_for("faculty"))

@app.route("/attendance", methods=["GET", "POST"])
@login_required
def attendance():
    db = get_db()
    if request.method == "POST":
        try: student_id = int(request.form.get("student_id",""))
        except ValueError: student_id = 0
        att_date = request.form.get("attendance_date", today_iso())
        status = request.form.get("status", "Present")
        student = db.execute("SELECT id FROM students WHERE id=?", (student_id,)).fetchone()
        if not student or status not in ("Present","Absent","Late"):
            flash("Select a valid student and attendance status.", "danger")
        else:
            try:
                db.execute("INSERT INTO attendance(student_id,attendance_date,status) VALUES(?,?,?)",
                           (student_id,att_date,status)); db.commit()
                flash("Attendance saved.", "success")
            except sqlite3.IntegrityError:
                flash("Attendance already exists for this student on that date.", "warning")
        return redirect(url_for("attendance"))
    students_rows = db.execute("SELECT id,name,course FROM students ORDER BY name").fetchall()
    rows = db.execute("""SELECT a.*, s.name AS student_name, s.course FROM attendance a
                         JOIN students s ON s.id=a.student_id
                         ORDER BY attendance_date DESC, a.id DESC LIMIT 200""").fetchall()
    return render_template("attendance.html", students=students_rows, records=rows)

@app.post("/attendance/<int:record_id>/delete")
@login_required
def delete_attendance(record_id):
    db=get_db(); db.execute("DELETE FROM attendance WHERE id=?", (record_id,)); db.commit()
    flash("Attendance record deleted if it existed.", "success")
    return redirect(url_for("attendance"))

@app.route("/timetable", methods=["GET", "POST"])
@login_required
def timetable():
    db = get_db()
    if request.method == "POST":
        vals = [request.form.get(k,"").strip() for k in ("day","start_time","end_time","subject","faculty_name","room")]
        if not all(vals):
            flash("Complete all timetable fields.", "danger")
        elif vals[1] >= vals[2]:
            flash("End time must be later than start time.", "danger")
        else:
            db.execute("INSERT INTO timetable(day,start_time,end_time,subject,faculty_name,room) VALUES(?,?,?,?,?,?)", vals)
            db.commit(); flash("Class added to timetable.", "success")
        return redirect(url_for("timetable"))
    rows = db.execute("SELECT * FROM timetable ORDER BY CASE day WHEN 'Monday' THEN 1 WHEN 'Tuesday' THEN 2 WHEN 'Wednesday' THEN 3 WHEN 'Thursday' THEN 4 WHEN 'Friday' THEN 5 WHEN 'Saturday' THEN 6 ELSE 7 END, start_time").fetchall()
    return render_template("timetable.html", classes=rows)

@app.post("/timetable/<int:class_id>/delete")
@login_required
def delete_class(class_id):
    db=get_db(); db.execute("DELETE FROM timetable WHERE id=?", (class_id,)); db.commit()
    flash("Class deleted if it existed.", "success")
    return redirect(url_for("timetable"))

@app.route("/reports")
@login_required
def reports():
    db=get_db()
    total_students=db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    attendance_counts=db.execute("SELECT status, COUNT(*) AS n FROM attendance GROUP BY status").fetchall()
    course_counts=db.execute("SELECT course, COUNT(*) AS n FROM students GROUP BY course ORDER BY n DESC").fetchall()
    daily=db.execute("""SELECT attendance_date, SUM(status='Present') AS present,
                        SUM(status='Absent') AS absent, SUM(status='Late') AS late
                        FROM attendance GROUP BY attendance_date ORDER BY attendance_date DESC LIMIT 14""").fetchall()
    return render_template("reports.html", total_students=total_students, attendance_counts=attendance_counts,
                           course_counts=course_counts, daily=daily)

@app.route("/reports/export.csv")
@login_required
def export_report():
    db=get_db()
    rows=db.execute("""SELECT s.name, s.email, s.course, s.year, a.attendance_date, a.status
                       FROM attendance a JOIN students s ON s.id=a.student_id
                       ORDER BY a.attendance_date DESC, s.name""").fetchall()
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(["Student","Email","Course","Year","Date","Attendance Status"])
    writer.writerows([tuple(r) for r in rows])
    response=make_response(output.getvalue())
    response.headers["Content-Type"]="text/csv; charset=utf-8"
    response.headers["Content-Disposition"]="attachment; filename=campus-attendance-report.csv"
    return response

@app.route("/assistant", methods=["GET", "POST"])
@login_required
def assistant():
    answer = None
    if request.method == "POST":
        prompt = request.form.get("question","").strip().lower()
        db=get_db()
        if any(w in prompt for w in ("student","enrollment","admission")):
            n=db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
            answer=f"There are currently {n} student records in your campus database. Use Students to add or remove records."
        elif any(w in prompt for w in ("attendance","present","absent")):
            rows=db.execute("SELECT status, COUNT(*) n FROM attendance WHERE attendance_date=? GROUP BY status",(today_iso(),)).fetchall()
            counts={r["status"]:r["n"] for r in rows}
            answer=f"Today's recorded attendance: {counts.get('Present',0)} present, {counts.get('Absent',0)} absent, and {counts.get('Late',0)} late."
        elif any(w in prompt for w in ("faculty","teacher","staff")):
            n=db.execute("SELECT COUNT(*) FROM faculty").fetchone()[0]
            answer=f"There are {n} faculty records. Open Faculty & workload to manage them."
        elif any(w in prompt for w in ("timetable","class","schedule")):
            n=db.execute("SELECT COUNT(*) FROM timetable").fetchone()[0]
            answer=f"There are {n} timetable entries. Open Timetable to add or manage classes."
        else:
            answer="I can answer questions about student counts, attendance, faculty, and timetable using your current database. Try asking one of those."
    return render_template("assistant.html", answer=answer)

@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="The page you requested could not be found."), 404

@app.errorhandler(500)
def server_error(_error):
    return render_template("error.html", code=500, message="Something went wrong. Please try again."), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
