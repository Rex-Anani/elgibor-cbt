from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random
from datetime import datetime, timedelta
import os
import csv
import io

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

db = SQLAlchemy(app)

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
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # Admin lockout flag

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    id = db.Column(db.Integer, primary_primary=True) if hasattr(db, 'Integer') else None
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
        <a class="navbar-brand" href="{{ url_for('index') }}">GREAT ELGIBOR CBT</a>
        <div class="d-flex align-items-center">
            {% if session.get('user_id') %}
                {% if session.get('role') in ['super_admin', 'school_admin'] %}
                    <a href="{{ url_for('manage_users') }}" class="btn btn-outline-primary btn-sm me-2">User Management</a>
                {% endif %}
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

def render_layout(content_html, **context):
    full_template = BASE_LAYOUT.replace("{% block content %}{% endblock %}", content_html)
    return render_template_string(full_template, **context)

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
            if not user.is_active:
                flash('Your account has been locked by the Super Admin. Access denied.', 'danger')
                return redirect(url_for('login'))

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

@app.route('/manage-users', methods=['GET', 'POST'])
def manage_users():
    current_role = session.get('role')
    if current_role not in ['super_admin', 'school_admin']:
        flash('Access restricted to administrators only', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_user':
            target_role = request.form['role']
            if current_role != 'super_admin' and target_role == 'school_admin':
                flash('Only Super Admin can assign School Admins.', 'danger')
                return redirect(url_for('manage_users'))

            new_user = User(
                username=request.form['username'].strip(),
                full_name=request.form['full_name'].strip(),
                role=target_role,
                class_level=request.form.get('class_level', '')
            )
            new_user.set_password(request.form['password'].strip())
            db.session.add(new_user)
            db.session.commit()
            
            log = AuditLog(user=session['username'], action=f"Created {target_role} account: {new_user.username}")
            db.session.add(log)
            db.session.commit()
            flash(f'Account created successfully for {new_user.full_name}!', 'success')

        elif action == 'toggle_lock':
            user_id = request.form.get('user_id')
            user_to_toggle = User.query.get_or_404(user_id)
            
            if current_role != 'super_admin':
                flash('Only Super Admin can lock or unlock accounts.', 'danger')
                return redirect(url_for('manage_users'))

            user_to_toggle.is_active = not user_to_toggle.is_active
            status_text = "unlocked" if user_to_toggle.is_active else "locked"
            
            log = AuditLog(user=session['username'], action=f"Super Admin {status_text} account: {user_to_toggle.username}")
            db.session.add(log)
            db.session.commit()
            flash(f'Account for {user_to_toggle.full_name} has been {status_text}.', 'info')

        elif action == 'delete_user':
            user_id = request.form.get('user_id')
            user_to_delete = User.query.get_or_404(user_id)
            
            if current_role != 'super_admin' and user_to_delete.role in ['school_admin', 'super_admin']:
                flash('You do not have permission to delete administrative accounts.', 'danger')
                return redirect(url_for('manage_users'))

            db.session.delete(user_to_delete)
            log = AuditLog(user=session['username'], action=f"Deleted user account: {user_to_delete.username}")
            db.session.add(log)
            db.session.commit()
            flash('User deleted successfully.', 'warning')

        return redirect(url_for('manage_users'))

    users = User.query.all()
    html = """
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>User Account Management Center</h2>
    </div>

    <div class="row">
        <div class="col-md-4">
            <div class="card p-4 mb-4">
                <h4>Create New User</h4>
                <form method="POST" class="mt-3">
                    <input type="hidden" name="action" value="add_user">
                    <div class="mb-3">
                        <label class="form-label">Full Name</label>
                        <input type="text" name="full_name" class="form-control" required placeholder="e.g. Jane Doe">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Username / Student ID</label>
                        <input type="text" name="username" class="form-control" required placeholder="e.g. teacher2">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Password</label>
                        <input type="password" name="password" class="form-control" required placeholder="Enter password">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Assign Role</label>
                        <select name="role" class="form-select" required>
                            <option value="student">Student</option>
                            <option value="teacher">Teacher</option>
                            {% if session.get('role') == 'super_admin' %}
                            <option value="school_admin">School Admin</option>
                            {% endif %}
                        </select>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Target Class (If Student)</label>
                        <select name="class_level" class="form-select">
                            <option value="">None</option>
                            <option value="Primary 1-3">Primary 1 - 3</option>
                            <option value="Primary 4-6">Primary 4 - 6</option>
                            <option value="JSS 1-3">Junior Secondary (JSS 1-3)</option>
                            <option value="SSS 1-3">Senior Secondary (SSS 1-3)</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Create Account</button>
                </form>
            </div>
        </div>

        <div class="col-md-8">
            <div class="card p-4">
                <h4>System Users</h4>
                <table class="table table-hover mt-3">
                    <thead>
                        <tr>
                            <th>User</th>
                            <th>Role</th>
                            <th>Class</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for u in users %}
                        <tr>
                            <td><strong>{{ u.full_name }}</strong><br><small class="text-muted">@{{ u.username }}</small></td>
                            <td><span class="badge bg-secondary">{{ u.role|upper }}</span></td>
                            <td>{{ u.class_level if u.class_level else '-' }}</td>
                            <td>
                                {% if u.is_active %}
                                    <span class="badge bg-success">Active</span>
                                {% else %}
                                    <span class="badge bg-danger">Locked Out</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if u.role != 'super_admin' %}
                                    {% if session.get('role') == 'super_admin' %}
                                        <form method="POST" style="display:inline-block;">
                                            <input type="hidden" name="action" value="toggle_lock">
                                            <input type="hidden" name="user_id" value="{{ u.id }}">
                                            {% if u.is_active %}
                                                <button type="submit" class="btn btn-sm btn-warning">Lock</button>
                                            {% else %}
                                                <button type="submit" class="btn btn-sm btn-info">Unlock</button>
                                            {% endif %}
                                        </form>
                                    {% endif %}
                                    <form method="POST" style="display:inline-block;" onsubmit="return confirm('Are you sure you want to remove this user?');">
                                        <input type="hidden" name="action" value="delete_user">
                                        <input type="hidden" name="user_id" value="{{ u.id }}">
                                        <button type="submit" class="btn btn-sm btn-danger">Delete</button>
                                    </form>
                                {% endif %}
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    """
    return render_layout(html, users=users)

@app.route('/super-admin')
def super_admin_dashboard():
    if session.get('role') != 'super_admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('index'))
    
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(20).all()
    users_count = User.query.count()
    exams_count = Examination.query.count()
    
    html = """
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>Super Admin Control Center</h2>
        <a href="{{ url_for('manage_users') }}" class="btn btn-primary">Manage Portal Users</a>
    </div>
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
                <h3>Active / Operational</h3>
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
    """
    return render_layout(html, logs=logs, users_count=users_count, exams_count=exams_count)

@app.route('/admin')
def admin_dashboard():
    if session.get('role') not in ['school_admin', 'teacher', 'super_admin']:
        flash('Access restricted to staff only', 'danger')
        return redirect(url_for('index'))
        
    exams = Examination.query.all()
    questions_count = Question.query.count()
    
    html = """
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>Teacher / Admin Management</h2>
        <div>
            <a href="{{ url_for('manage_users') }}" class="btn btn-outline-secondary me-2">Manage Users</a>
            <a href="{{ url_for('add_question') }}" class="btn btn-outline-primary me-2">+ Add Questions</a>
            <a href="{{ url_for('create_exam') }}" class="btn btn-primary">+ Create New Exam</a>
        </div>
    </div>
    
    <div class="row mb-4">
        <div class="col-md-6">
            <div class="card p-3 bg-light border">
                <h5>Question Bank Size</h5>
                <h3>{{ questions_count }} Questions Available</h3>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card p-3 bg-light border">
                <h5>Active Exams</h5>
                <h3>{{ exams|length }} Scheduled</h3>
            </div>
        </div>
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
    """
    return render_layout(html, exams=exams, questions_count=questions_count)

import csv
import io
from flask import Flask, render_template_string, request, redirect, url_for, session, flash

@app.route('/add-question', methods=['GET', 'POST'])
def add_question():
    if session.get('role') not in ['super_admin', 'school_admin', 'teacher']:
        flash('Access restricted to administrators and teachers only.', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        # Single Question Addition
        if 'single_submit' in request.form:
            try:
                new_q = Question(
                    subject=request.form['subject'].strip(),
                    class_level=request.form['class_level'].strip(),
                    question_text=request.form['question_text'].strip(),
                    option_a=request.form['option_a'].strip(),
                    option_b=request.form['option_b'].strip(),
                    option_c=request.form['option_c'].strip(),
                    option_d=request.form['option_d'].strip(),
                    correct_option=request.form['correct_option'].strip().upper()
                )
                db.session.add(new_q)
                db.session.commit()
                flash('Question saved to bank successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving question: {str(e)}', 'danger')
                
            return redirect(url_for('add_question'))
            
        # Bulk CSV Upload with Auto-Delimiter Sniffer
        elif 'csv_submit' in request.form:
            csv_file = request.files.get('file')
            
            if not csv_file or not csv_file.filename.lower().endswith('.csv'):
                flash('Please select a valid .csv file to upload.', 'danger')
                return redirect(url_for('add_question'))
                
            try:
                raw_bytes = csv_file.stream.read()
                decoded_file = raw_bytes.decode("utf-8-sig")
                
                # Auto-detect delimiter (commas vs semicolons)
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(decoded_file[:2048])
                except Exception:
                    dialect = 'excel'
                    
                stream = io.StringIO(decoded_file, newline=None)
                csv_reader = csv.DictReader(stream, dialect=dialect)
                
                if csv_reader.fieldnames:
                    csv_reader.fieldnames = [str(header).strip().lower() for header in csv_reader.fieldnames if header]
                
                required_cols = {'subject', 'class_level', 'question_text', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option'}
                actual_cols = set(csv_reader.fieldnames or [])
                
                if not required_cols.issubset(actual_cols):
                    missing = required_cols - actual_cols
                    flash(f'CSV is missing required headers: {", ".join(missing)}', 'danger')
                    return redirect(url_for('add_question'))

                added_count = 0
                for row in csv_reader:
                    if not any(row.values()):
                        continue
                        
                    q = Question(
                        subject=row.get('subject', '').strip(),
                        class_level=row.get('class_level', '').strip(),
                        question_text=row.get('question_text', '').strip(),
                        option_a=row.get('option_a', '').strip(),
                        option_b=row.get('option_b', '').strip(),
                        option_c=row.get('option_c', '').strip(),
                        option_d=row.get('option_d', '').strip(),
                        correct_option=row.get('correct_option', '').strip().upper()
                    )
                    db.session.add(q)
                    added_count += 1
                    
                db.session.commit()
                flash(f'Successfully imported {added_count} questions from CSV!', 'success')
                return redirect(url_for('admin_dashboard'))
                
            except Exception as e:
                db.session.rollback()
                flash(f'Error processing CSV file: {str(e)}', 'danger')
                return redirect(url_for('add_question'))

    return render_layout("""
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card p-4 mb-4">
                <h4>Option 1: Add Single Question</h4>
                <form method="POST" class="mt-3">
                    <input type="hidden" name="single_submit" value="1">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <label class="form-label">Subject</label>
                            <input type="text" name="subject" class="form-control" placeholder="e.g., Mathematics" required>
                        </div>
                        <div class="col-md-6">
                            <label class="form-label">Target Class</label>
                            <select name="class_level" class="form-select" required>
                                <option value="Primary 1-3">Primary 1 - 3</option>
                                <option value="Primary 4-6">Primary 4 - 6</option>
                                <option value="JSS 1-3">Junior Secondary (JSS 1-3)</option>
                                <option value="SSS 1-3">Senior Secondary (SSS 1-3)</option>
                            </select>
                        </div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Question Text</label>
                        <textarea name="question_text" class="form-control" rows="2" required></textarea>
                    </div>
                    <div class="row mb-3">
                        <div class="col-md-6"><label>Option A</label><input type="text" name="option_a" class="form-control" required></div>
                        <div class="col-md-6"><label>Option B</label><input type="text" name="option_b" class="form-control" required></div>
                    </div>
                    <div class="row mb-3">
                        <div class="col-md-6"><label>Option C</label><input type="text" name="option_c" class="form-control" required></div>
                        <div class="col-md-6"><label>Option D</label><input type="text" name="option_d" class="form-control" required></div>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Correct Option</label>
                        <select name="correct_option" class="form-select" required>
                            <option value="A">Option A</option>
                            <option value="B">Option B</option>
                            <option value="C">Option C</option>
                            <option value="D">Option D</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-success w-100">Save Question</button>
                </form>
            </div>
            
            <div class="card p-4">
                <h4>Option 2: Bulk Upload via CSV File</h4>
                <p class="text-muted small">Upload a <code>.csv</code> file with headers: <code>subject, class_level, question_text, option_a, option_b, option_c, option_d, correct_option</code></p>
                <form method="POST" enctype="multipart/form-data" class="mt-2">
                    <input type="hidden" name="csv_submit" value="1">
                    <div class="mb-3">
                        <input type="file" name="file" class="form-control" accept=".csv" required>
                    </div>
                    <button type="submit" class="btn btn-outline-primary w-100">Upload CSV Questions</button>
                </form>
            </div>
        </div>
    </div>
    """)
    
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
        
    html = """
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
    """
    return render_layout(html)

@app.route('/student')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('index'))
        
    student_class = session.get('class_level')
    available_exams = Examination.query.filter_by(class_level=student_class, is_published=True).all()
    past_results = TestResult.query.filter_by(student_id=session['user_id']).all()
    
    html = """
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
    """
    return render_layout(html, available_exams=available_exams, past_results=past_results)

from sqlalchemy import func

@app.route('/take-exam/<int:exam_id>', methods=['GET', 'POST'])
def take_exam(exam_id):
    if session.get('role') != 'student':
        flash('Only students can take examinations.', 'danger')
        return redirect(url_for('index'))

    # 1. Matches your original 'Examination' model name
    exam = Examination.query.get_or_404(exam_id)

    # 2. Flexible, case-insensitive string matching for Subject and Class Level
    # Note: If you haven't added 'is_deleted' to your Question model, remove that condition.
    questions = Question.query.filter(
        func.lower(func.trim(Question.subject)) == exam.subject.strip().lower(),
        func.lower(func.trim(Question.class_level)) == exam.class_level.strip().lower()
    ).all()

    if request.method == 'POST':
        score = 0
        total = len(questions)
        for q in questions:
            user_answer = request.form.get(f'q_{q.id}')
            if user_answer and user_answer.strip().upper() == q.correct_option.strip().upper():
                score += 1

        percentage = round((score / total) * 100, 2) if total > 0 else 0

        # 3. Matches your original 'TestResult' model name
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

    # HTML Layout Render
    html = """
    <div class="row justify-content-center">
        <div class="col-md-9">
            <div class="card p-4 shadow-sm position-relative">
                <div class="position-absolute top-0 end-0 p-3">
                    <span class="badge bg-danger fs-6" id="timer">Time Remaining: {{ exam.duration_minutes }}:00</span>
                </div>
                
                <h3>{{ exam.title }} ({{ exam.subject }})</h3>
                <p class="text-muted">Class: {{ exam.class_level }} | Total Questions: {{ questions|length }}</p>
                <hr>

                {% if questions %}
                <form method="POST">
                    {% for q in questions %}
                    <div class="mb-4">
                        <p class="fw-bold">{{ loop.index }}. {{ q.question_text }}</p>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="q_{{ q.id }}" value="A" id="q{{ q.id }}_a">
                            <label class="form-check-label" for="q{{ q.id }}_a">A) {{ q.option_a }}</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="q_{{ q.id }}" value="B" id="q{{ q.id }}_b">
                            <label class="form-check-label" for="q{{ q.id }}_b">B) {{ q.option_b }}</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="q_{{ q.id }}" value="C" id="q{{ q.id }}_c">
                            <label class="form-check-label" for="q{{ q.id }}_c">C) {{ q.option_c }}</label>
                        </div>
                        <div class="form-check">
                            <input class="form-check-input" type="radio" name="q_{{ q.id }}" value="D" id="q{{ q.id }}_d">
                            <label class="form-check-label" for="q{{ q.id }}_d">D) {{ q.option_d }}</label>
                        </div>
                    </div>
                    {% endfor %}
                    <button type="submit" class="btn btn-success w-100 fs-5 mt-3">Submit Answers</button>
                </form>
                {% else %}
                <div class="alert alert-warning text-center">
                    No questions found for <strong>{{ exam.subject }}</strong> under <strong>{{ exam.class_level }}</strong>.
                </div>
                <a href="{{ url_for('student_dashboard') }}" class="btn btn-secondary w-100">Return to Dashboard</a>
                {% endif %}
            </div>
        </div>
    </div>
    """
    return render_layout(html, exam=exam, questions=questions)
    
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
            admin = User(username='superadmin', role='super_admin', full_name='Super Admin', is_active=True)
            admin.set_password('Admin@2026')
            db.session.add(admin)

        if not User.query.filter_by(username='teacher1').first():
            teacher = User(username='teacher1', role='teacher', full_name='Mr. Johnson', is_active=True)
            teacher.set_password('Teacher@2026')
            db.session.add(teacher)

        if not User.query.filter_by(username='student1').first():
            student = User(username='student1', role='student', full_name='David Okonkwo', class_level='Primary 4-6', is_active=True)
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
