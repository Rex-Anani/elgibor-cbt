from flask import Flask, render_template_string, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# ==========================================
# 1. APPLICATION CONFIGURATION
# ==========================================
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'elgibor_super_secret_key_2026')

db_url = os.environ.get('DATABASE_URL', 'sqlite:///cbt_engine.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy after configuration
db = SQLAlchemy(app)

# Helper for WAT (UTC+1) local timestamps
def get_local_time():
    return datetime.utcnow() + timedelta(hours=1)

# ==========================================
# 2. DATABASE MODELS
# ==========================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(30), nullable=False)  # 'super_admin', 'school_admin', 'teacher', 'student'
    full_name = db.Column(db.String(120), nullable=False)
    class_level = db.Column(db.String(50), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class AcademicSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_name = db.Column(db.String(50), nullable=False)
    term = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(80), nullable=False)
    class_level = db.Column(db.String(50), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)

class Examination(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    exam_type = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(80), nullable=False)
    class_level = db.Column(db.String(50), nullable=False)
    duration_minutes = db.Column(db.Integer, default=30)
    is_published = db.Column(db.Boolean, default=False)

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('examination.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=get_local_time)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(80))
    action = db.Column(db.String(255))
    timestamp = db.Column(db.DateTime, default=get_local_time)

# ==========================================
# 3. BASE LAYOUT TEMPLATE
# ==========================================

BASE_LAYOUT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Great Elgibor Schools - Academic CBT Portal</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .navbar-brand { font-weight: bold; color: #1e3c72 !important; }
        .card { border: none; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
        .btn-primary { background-color: #1e3c72; border: none; }
        .btn-primary:hover { background-color: #2a5298; }
    </style>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm mb-4">
    <div class="container">
        <a class="navbar-brand" href="#">GREAT ELGIBOR CBT</a>
        <div class="d-flex align-items-center">
            {% if session.get('user_id') %}
                <span class="me-3 text-muted"><strong>{{ session['full_name'] }}</strong> ({{ session['role']|upper }})</span>
                <a href="{{ url_for('logout') }}" class="btn btn-outline-danger btn-sm">Logout</a>
            {% endif %}
        </div>
    </div>
</nav>
<div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, msg in messages %}
                <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                    {{ msg }}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                </div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    {% block content %}{% endblock %}
</div>
</body>
</html>
"""

# ==========================================
# 4. ROUTES
# ==========================================

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    role = session.get('role')
    if role == 'super_admin':
        return redirect(url_for('super_admin_dashboard'))
    elif role in ['school_admin', 'teacher']:
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role
            session['full_name'] = user.full_name
            session['class_level'] = user.class_level
            
            log = AuditLog(user=user.username, action="User logged in")
            db.session.add(log)
            db.session.commit()
            
            flash('Welcome back, ' + user.full_name + '!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
            
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Great Elgibor Schools - Academic CBT Portal</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { background-color: #f4f6f9; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
            .navbar-brand { font-weight: bold; color: #1e3c72 !important; }
            .card { border: none; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
            .btn-primary { background-color: #1e3c72; border: none; }
            .btn-primary:hover { background-color: #2a5298; }
        </style>
    </head>
    <body>
    <nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm mb-4">
        <div class="container">
            <a class="navbar-brand" href="#">GREAT ELGIBOR CBT</a>
        </div>
    </nav>
    <div class="container">
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, msg in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ msg }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <div class="row justify-content-center mt-5">
            <div class="col-md-5">
                <div class="card p-4">
                    <h3 class="text-center mb-4 text-primary">Portal Login</h3>
                    <form method="POST">
                        <div class="mb-3">
                            <label class="form-label">Username / Student ID</label>
                            <input type="text" name="username" class="form-control" required placeholder="Enter your ID">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Password</label>
                            <input type="password" name="password" class="form-control" required placeholder="Enter password">
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Sign In</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
    </body>
    </html>
    """)

@app.route('/super-admin')
def super_admin_dashboard():
    if session.get('role') != 'super_admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('index'))
    
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(20).all()
    users_count = User.query.count()
    exams_count = Examination.query.count()
    
    return render_template_string(BASE_LAYOUT + """
    {% block content %}
    <h2 class="mb-4">Super Admin Control Center</h2>
    <div class="row mb-4">
        <div class="col-md-4">
            <div class="card p-3 bg-primary text-white">
                <h5>Total Users Registered</h5>
                <h3>{{ users_count }}</h3>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card p-3 bg-success text-white">
                <h5>Total Examinations</h5>
                <h3>{{ exams_count }}</h3>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card p-3 bg-dark text-white">
                <h5>System Status</h5>
                <h3>Active / Healthy</h3>
            </div>
        </div>
    </div>
    
    <div class="card p-4 mb-4">
        <h4>System Audit Logs (WAT)</h4>
        <table class="table table-striped table-hover mt-3">
            <thead>
                <tr>
                    <th>User</th>
                    <th>Action</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
                {% for log in logs %}
                <tr>
                    <td>{{ log.user }}</td>
                    <td>{{ log.action }}</td>
                    <td>{{ log.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endblock %}
    """, logs=logs, users_count=users_count, exams_count=exams_count)

@app.route('/admin')
def admin_dashboard():
    if session.get('role') not in ['school_admin', 'teacher', 'super_admin']:
        flash('Access restricted to staff only', 'danger')
        return redirect(url_for('index'))
        
    exams = Examination.query.all()
    questions_count = Question.query.count()
    
    return render_template_string(BASE_LAYOUT + """
    {% block content %}
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>Academic & Examination Management</h2>
        <a href="{{ url_for('create_exam') }}" class="btn btn-primary">+ Create New Exam</a>
    </div>
    
    <div class="card p-4">
        <h4>Active & Scheduled Exams</h4>
        <table class="table table-bordered mt-3">
            <thead class="table-light">
                <tr>
                    <th>Title</th>
                    <th>Type</th>
                    <th>Subject</th>
                    <th>Class Level</th>
                    <th>Duration</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {% for exam in exams %}
                <tr>
                    <td>{{ exam.title }}</td>
                    <td><span class="badge bg-info text-dark">{{ exam.exam_type }}</span></td>
                    <td>{{ exam.subject }}</td>
                    <td>{{ exam.class_level }}</td>
                    <td>{{ exam.duration_minutes }} mins</td>
                    <td>
                        {% if exam.is_published %}
                            <span class="badge bg-success">Published</span>
                        {% else %}
                            <span class="badge bg-secondary">Draft</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endblock %}
    """, exams=exams, questions_count=questions_count)

@app.route('/create-exam', methods=['GET', 'POST'])
def create_exam():
    if session.get('role') not in ['school_admin', 'teacher', 'super_admin']:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = request.form['title']
        exam_type = request.form['exam_type']
        subject = request.form['subject']
        class_level = request.form['class_level']
        duration = int(request.form['duration'])
        
        exam = Examination(
            title=title, exam_type=exam_type, subject=subject, 
            class_level=class_level, duration_minutes=duration, is_published=True
        )
        db.session.add(exam)
        db.session.commit()
        
        flash('Examination created and published successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
        
    return render_template_string(BASE_LAYOUT + """
    {% block content %}
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card p-4">
                <h4>Create New Examination</h4>
                <form method="POST" class="mt-3">
                    <div class="mb-3">
                        <label class="form-label">Exam Title</label>
                        <input type="text" name="title" class="form-control" placeholder="e.g., 1st Term Mathematics Test" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Exam Category</label>
                        <select name="exam_type" class="form-select" required>
                            <option value="Continuous Assessment">Continuous Assessment (CA)</option>
                            <option value="Mid-Term Test">Mid-Term Test</option>
                            <option value="Terminal Exam">Terminal Examination</option>
                            <option value="Holiday Practice">Holiday Practice / Revision</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Subject</label>
                        <input type="text" name="subject" class="form-control" placeholder="e.g., Mathematics" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Target Class</label>
                        <select name="class_level" class="form-select" required>
                            <option value="Primary 1-3">Primary 1 - 3</option>
                            <option value="Primary 4-6">Primary 4 - 6</option>
                            <option value="JSS 1-3">Junior Secondary (JSS 1-3)</option>
                            <option value="SSS 1-3">Senior Secondary (SSS 1-3)</option>
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Duration (Minutes)</label>
                        <input type="number" name="duration" class="form-control" value="30" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Save & Publish Exam</button>
                </form>
            </div>
        </div>
    </div>
    {% endblock %}
    """)

@app.route('/student')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('index'))
        
    student_class = session.get('class_level')
    available_exams = Examination.query.filter_by(class_level=student_class, is_published=True).all()
    past_results = TestResult.query.filter_by(student_id=session['user_id']).all()
    
    return render_template_string(BASE_LAYOUT + """
    {% block content %}
    <h2 class="mb-4">Student Assessment Dashboard</h2>
    <div class="row">
        <div class="col-md-7">
            <div class="card p-4 mb-4">
                <h4>Available Examinations</h4>
                {% if available_exams %}
                    <ul class="list-group mt-3">
                    {% for exam in available_exams %}
                        <li class="list-group-item d-flex justify-content-between align-items-center">
                            <div>
                                <strong>{{ exam.title }}</strong><br>
                                <small class="text-muted">{{ exam.subject }} | {{ exam.duration_minutes }} mins</small>
                            </div>
                            <a href="{{ url_for('take_exam', exam_id=exam.id) }}" class="btn btn-sm btn-primary">Start Exam</a>
                        </li>
                    {% endfor %}
                    </ul>
                {% else %}
                    <p class="text-muted mt-2">No active examinations scheduled for your class at the moment.</p>
                {% endif %}
            </div>
        </div>
        <div class="col-md-5">
            <div class="card p-4">
                <h4>Your Exam Results</h4>
                {% if past_results %}
                    <table class="table table-sm mt-3">
                        <thead>
                            <tr>
                                <th>Exam ID</th>
                                <th>Score</th>
                                <th>Grade</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for res in past_results %}
                            <tr>
                                <td>Exam #{{ res.exam_id }}</td>
                                <td>{{ res.score }} / {{ res.total_questions }}</td>
                                <td><strong>{{ res.percentage }}%</strong></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p class="text-muted mt-2">No exam results recorded yet.</p>
                {% endif %}
            </div>
        </div>
    </div>
    {% endblock %}
    """, available_exams=available_exams, past_results=past_results)

@app.route('/take-exam/<int:exam_id>')
def take_exam(exam_id):
    if session.get('role') != 'student':
        return redirect(url_for('index'))
        
    exam = Examination.query.get_or_404(exam_id)
    questions = Question.query.filter_by(subject=exam.subject, class_level=exam.class_level).all()
    random.shuffle(questions)
    
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Taking Exam: {{ exam.title }}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { user-select: none; background-color: #f8f9fa; }
            .timer-box { position: fixed; top: 20px; right: 20px; background: #dc3545; color: white; padding: 10px 20px; border-radius: 5px; font-weight: bold; }
        </style>
    </head>
    <body oncopy="return false" onpaste="return false" oncontextmenu="return false">
    
    <div class="timer-box" id="timer">Time Remaining: --:--</div>
    
    <div class="container my-5">
        <div class="card p-4 shadow-sm">
            <h3>{{ exam.title }} ({{ exam.subject }})</h3>
            <p class="text-muted">Class: {{ exam.class_level }} | Total Questions: {{ questions|length }}</p>
            <hr>
            
            <form id="examForm" action="{{ url_for('submit_exam', exam_id=exam.id) }}" method="POST">
                {% for q in questions %}
                <div class="mb-4">
                    <h5>Q{{ loop.index }}. {{ q.question_text }}</h5>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="q_{{ q.id }}" value="A" id="q{{ q.id }}a">
                        <label class="form-check-label" for="q{{ q.id }}a">A) {{ q.option_a }}</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="q_{{ q.id }}" value="B" id="q{{ q.id }}b">
                        <label class="form-check-label" for="q{{ q.id }}b">B) {{ q.option_b }}</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="q_{{ q.id }}" value="C" id="q{{ q.id }}c">
                        <label class="form-check-label" for="q{{ q.id }}c">C) {{ q.option_c }}</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input" type="radio" name="q_{{ q.id }}" value="D" id="q{{ q.id }}d">
                        <label class="form-check-label" for="q{{ q.id }}d">D) {{ q.option_d }}</label>
                    </div>
                </div>
                {% endfor %}
                <button type="submit" class="btn btn-success btn-lg w-100">Submit Answers</button>
            </form>
        </div>
    </div>

    <script>
        let durationMinutes = {{ exam.duration_minutes }};
        let secondsLeft = durationMinutes * 60;
        
        let timerInterval = setInterval(function() {
            let minutes = Math.floor(secondsLeft / 60);
            let seconds = secondsLeft % 60;
            document.getElementById('timer').innerText = `Time Remaining: ${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;
            
            if (secondsLeft <= 0) {
                clearInterval(timerInterval);
                alert("Time is up! Your examination will be submitted automatically.");
                document.getElementById('examForm').submit();
            }
            secondsLeft--;
        }, 1000);
    </script>
    </body>
    </html>
    """, exam=exam, questions=questions)

@app.route('/submit-exam/<int:exam_id>', methods=['POST'])
def submit_exam(exam_id):
    if session.get('role') != 'student':
        return redirect(url_for('index'))
        
    exam = Examination.query.get_or_404(exam_id)
    questions = Question.query.filter_by(subject=exam.subject, class_level=exam.class_level).all()
    
    score = 0
    total = len(questions)
    
    for q in questions:
        selected_option = request.form.get(f'q_{q.id}')
        if selected_option and selected_option == q.correct_option:
            score += 1
            
    percentage = round((score / total) * 100, 2) if total > 0 else 0
    
    res = TestResult(
        student_id=session['user_id'],
        exam_id=exam.id,
        score=score,
        total_questions=total,
        percentage=percentage
    )
    db.session.add(res)
    db.session.commit()
    
    flash(f'Exam submitted successfully! You scored {score}/{total} ({percentage}%).', 'success')
    return redirect(url_for('student_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ==========================================
# 5. SAFE DATABASE INITIALIZATION
# ==========================================

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='superadmin').first():
            admin = User(username='superadmin', role='super_admin', full_name='Rex Anani (Super Admin)')
            admin.set_password('Admin@2026')
            db.session.add(admin)

        if not User.query.filter_by(username='teacher1').first():
            teacher = User(username='teacher1', role='teacher', full_name='Mr. Johnson')
            teacher.set_password('Teacher@2026')
            db.session.add(teacher)

        if not User.query.filter_by(username='student1').first():
            student = User(username='student1', role='student', full_name='David Okonkwo', class_level='Primary 4-6')
            student.set_password('Student@2026')
            db.session.add(student)

        if Question.query.count() == 0:
            q1 = Question(
                subject='Mathematics', class_level='Primary 4-6',
                question_text='What is the square root of 144?',
                option_a='10', option_b='11', option_c='12', option_d='14',
                correct_option='C'
            )
            q2 = Question(
                subject='Mathematics', class_level='Primary 4-6',
                question_text='Solve for x: 2x + 5 = 15',
                option_a='5', option_b='10', option_c='15', option_d='20',
                correct_option='A'
            )
            db.session.add_all([q1, q2])

        db.session.commit()

init_db()

if __name__ == '__main__':
    app.run(debug=True)
