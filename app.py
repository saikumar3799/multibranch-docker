from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime

app = Flask(__name__)

app.config["SECRET_KEY"] = "smart-attendance-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///attendance.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# --------------------------------------------------
# DATABASE MODELS
# --------------------------------------------------

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    attendance = db.relationship(
        "Attendance",
        backref="student",
        lazy=True,
        cascade="all, delete-orphan"
    )


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("student.id"),
        nullable=False
    )
    attendance_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False)

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "attendance_date",
            name="unique_student_date"
        ),
    )


# --------------------------------------------------
# DASHBOARD
# --------------------------------------------------

@app.route("/")
def dashboard():

    students = Student.query.all()

    total_students = len(students)

    today = date.today()

    present_today = Attendance.query.filter_by(
        attendance_date=today,
        status="Present"
    ).count()

    absent_today = Attendance.query.filter_by(
        attendance_date=today,
        status="Absent"
    ).count()

    total_attendance = Attendance.query.count()

    present_count = Attendance.query.filter_by(
        status="Present"
    ).count()

    if total_attendance > 0:
        attendance_percentage = round(
            (present_count / total_attendance) * 100,
            2
        )
    else:
        attendance_percentage = 0

    recent_attendance = (
        Attendance.query
        .order_by(Attendance.id.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "dashboard.html",
        total_students=total_students,
        present_today=present_today,
        absent_today=absent_today,
        attendance_percentage=attendance_percentage,
        recent_attendance=recent_attendance
    )


# --------------------------------------------------
# STUDENTS
# --------------------------------------------------

@app.route("/students")
def students():

    search = request.args.get("search", "")

    if search:
        students = Student.query.filter(
            db.or_(
                Student.name.ilike(f"%{search}%"),
                Student.student_id.ilike(f"%{search}%"),
                Student.department.ilike(f"%{search}%")
            )
        ).all()
    else:
        students = Student.query.order_by(Student.name).all()

    return render_template(
        "students.html",
        students=students,
        search=search
    )


# --------------------------------------------------
# ADD STUDENT
# --------------------------------------------------

@app.route("/students/add", methods=["POST"])
def add_student():

    student_id = request.form["student_id"].strip()
    name = request.form["name"].strip()
    department = request.form["department"].strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()

    existing_student = Student.query.filter_by(
        student_id=student_id
    ).first()

    if existing_student:
        flash("Student ID already exists.", "error")
        return redirect(url_for("students"))

    student = Student(
        student_id=student_id,
        name=name,
        department=department,
        email=email,
        phone=phone
    )

    db.session.add(student)
    db.session.commit()

    flash("Student added successfully.", "success")

    return redirect(url_for("students"))


# --------------------------------------------------
# DELETE STUDENT
# --------------------------------------------------

@app.route("/students/delete/<int:id>", methods=["POST"])
def delete_student(id):

    student = Student.query.get_or_404(id)

    db.session.delete(student)
    db.session.commit()

    flash("Student deleted successfully.", "success")

    return redirect(url_for("students"))


# --------------------------------------------------
# ATTENDANCE PAGE
# --------------------------------------------------

@app.route("/attendance")
def attendance():

    selected_date = request.args.get(
        "date",
        date.today().isoformat()
    )

    selected_date_obj = datetime.strptime(
        selected_date,
        "%Y-%m-%d"
    ).date()

    students = Student.query.order_by(Student.name).all()

    attendance_records = Attendance.query.filter_by(
        attendance_date=selected_date_obj
    ).all()

    attendance_map = {
        record.student_id: record.status
        for record in attendance_records
    }

    return render_template(
        "attendance.html",
        students=students,
        attendance_map=attendance_map,
        selected_date=selected_date
    )


# --------------------------------------------------
# SAVE ATTENDANCE
# --------------------------------------------------

@app.route("/attendance/save", methods=["POST"])
def save_attendance():

    attendance_date = request.form["attendance_date"]

    selected_date = datetime.strptime(
        attendance_date,
        "%Y-%m-%d"
    ).date()

    students = Student.query.all()

    for student in students:

        status = request.form.get(
            f"status_{student.id}"
        )

        if status not in ["Present", "Absent"]:
            continue

        existing = Attendance.query.filter_by(
            student_id=student.id,
            attendance_date=selected_date
        ).first()

        if existing:
            existing.status = status
        else:
            record = Attendance(
                student_id=student.id,
                attendance_date=selected_date,
                status=status
            )

            db.session.add(record)

    db.session.commit()

    flash("Attendance saved successfully.", "success")

    return redirect(
        url_for(
            "attendance",
            date=attendance_date
        )
    )


# --------------------------------------------------
# REPORT
# --------------------------------------------------

@app.route("/report")
def report():

    students = Student.query.order_by(Student.name).all()

    report_data = []

    for student in students:

        total = Attendance.query.filter_by(
            student_id=student.id
        ).count()

        present = Attendance.query.filter_by(
            student_id=student.id,
            status="Present"
        ).count()

        absent = Attendance.query.filter_by(
            student_id=student.id,
            status="Absent"
        ).count()

        if total > 0:
            percentage = round(
                (present / total) * 100,
                2
            )
        else:
            percentage = 0

        report_data.append({
            "student": student,
            "total": total,
            "present": present,
            "absent": absent,
            "percentage": percentage
        })

    return render_template(
        "attendance.html",
        students=students,
        report_data=report_data
    )


# --------------------------------------------------
# INITIALIZE DATABASE
# --------------------------------------------------

with app.app_context():
    db.create_all()


# --------------------------------------------------
# RUN APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
