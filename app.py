import sqlite3
import random
import string
from flask import Flask, render_template_string, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "elgibor_secret_key_cbt_2026"

# ---------------------------------------------------------
# DATABASE INITIALIZATION
# ---------------------------------------------------------
def init_db():
    conn = sqlite3.connect('cbt_database.db')
    cursor = conn.cursor()
    
    # Users Table (Admin & Teachers)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    
    # Students Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            student_class TEXT NOT NULL,
            pin TEXT UNIQUE NOT NULL
        )
    ''')
    
    # Question Bank Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_class TEXT NOT NULL,
            subject TEXT NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option INTEGER NOT NULL
        )
    ''')
    
    # Exam Attempts / Scores Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            student_name TEXT NOT NULL,
            student_class TEXT NOT NULL,
            subject TEXT NOT NULL,
            score_percent INTEGER NOT NULL,
            status TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    ''')
    
    # Create Default Admin if none exists
    cursor.execute("SELECT * FROM users WHERE role = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin123", "admin"))
        
    conn.commit()
    conn.close()

init_db()

# Helper function to generate 6-digit PIN
def generate_pin():
    return ''.join(random.choices(string.digits, k=6))

# ---------------------------------------------------------
# HTML TEMPLATE
# ---------------------------------------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Great Elgibor CBT Portal</title>
    <style>
        :root { --primary: #0d47a1; --secondary: #f57c00; --success: #2e7d32; --fail: #c62828; --bg: #f4f6f9; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; }
        body { background: var(--bg); color: #333; padding-bottom: 50px; }
        header { background: var(--primary); color: white; text-align: center; padding: 1.5rem; border-bottom: 5px solid var(--secondary); }
        nav { background: #1565c0; padding: 0.5rem 2rem; display: flex; justify-content: space-between; align-items: center; color: white; }
        nav a { color: white; text-decoration: none; font-weight: bold; margin-left: 1rem; }
        .container { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); margin-bottom: 1.5rem; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
        .form-group { margin-bottom: 1rem; }
        .form-group label { display: block; margin-bottom: 0.4rem; font-weight: 600; }
        .form-group input, .form-group select { width: 100%; padding: 0.7rem; border: 1px solid #ccc; border-radius: 4px; }
        .btn { display: inline-block; background: var(--primary); color: white; padding: 0.7rem 1.5rem; border: none; border-radius: 4px; font-weight: 600; cursor: pointer; text-decoration: none; width: 100%; text-align: center; }
        .btn-secondary { background: var(--secondary); }
        .btn-danger { background: var(--fail); }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        table, th, td { border: 1px solid #ddd; padding: 0.8rem; text-align: left; }
        th { background: #f1f1f1; }
        .badge { padding: 0.3rem 0.6rem; border-radius: 4px; color: white; font-weight: bold; font-size: 0.85rem; }
        .badge-pass { background: var(--success); }
        .badge-fail { background: var(--fail); }
        .question-box { margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid #eee; }
        .alert { background: #ffebee; color: var(--fail); padding: 0.8rem; border-radius: 4px; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <header>
        <h1>Great Elgibor Secondary School</h1>
        <p>Managed CBT & Holiday Assessment Engine</p>
    </header>

    {% if session.get('user_id') or session.get('student_id') %}
    <nav>
        <span>Logged in as: <strong>{{ session.get('name') }}</strong> ({{ session.get('role', 'Student') }})</span>
        <a href="{{ url_for('logout') }}">Logout</a>
    </nav>
    {% endif %}

    <div class="container">
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            {% for message in messages %}
              <div class="alert">{{ message }}</div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <!-- LANDING / LOGIN SELECTION -->
        {% if page == 'index' %}
        <div class="grid">
            <div class="card">
                <h2>🎓 Student Access</h2>
                <p style="margin-bottom: 1rem; color: #666;">Enter your assigned 6-Digit PIN to start your test.</p>
                <form action="{{ url_for('student_login') }}" method="POST">
                    <div class="form-group">
                        <label>6-Digit PIN:</label>
                        <input type="text" name="pin" maxlength="6" required placeholder="e.g. 123456">
                    </div>
                    <button type="submit" class="btn">Login to Take Test</button>
                </form>
            </div>
            <div class="card">
                <h2>👨‍🏫 Staff Access</h2>
                <p style="margin-bottom: 1rem; color: #666;">Teachers and Admin portal login.</p>
                <form action="{{ url_for('staff_login') }}" method="POST">
                    <div class="form-group">
                        <label>Username:</label>
                        <input type="text" name="username" required>
                    </div>
                    <div class="form-group">
                        <label>Password:</label>
                        <input type="password" name="password" required>
                    </div>
                    <button type="submit" class="btn btn-secondary">Staff Login</button>
                </form>
            </div>
        </div>

        <!-- STAFF DASHBOARD -->
        {% elif page == 'dashboard' %}
        <div class="card">
            <h2>Welcome, {{ session['name'] }}</h2>
            <p style="color:#666;">Role: <strong>{{ session['role']|upper }}</strong></p>
        </div>

        {% if session['role'] == 'admin' %}
        <div class="card">
            <h3>Register Teacher Account</h3>
            <form action="{{ url_for('add_teacher') }}" method="POST" class="grid" style="margin-top:1rem;">
                <div class="form-group">
                    <label>Teacher Username:</label>
                    <input type="text" name="username" required>
                </div>
                <div class="form-group">
                    <label>Assign Password:</label>
                    <input type="text" name="password" required>
                </div>
                <button type="submit" class="btn" style="grid-column: span 2;">Register Teacher</button>
            </form>
        </div>
        {% endif %}

        <div class="grid">
            <div class="card">
                <h3>Register New Student</h3>
                <form action="{{ url_for('add_student') }}" method="POST" style="margin-top:1rem;">
                    <div class="form-group">
                        <label>Full Name:</label>
                        <input type="text" name="fullname" required>
                    </div>
                    <div class="form-group">
                        <label>Class:</label>
                        <select name="student_class" required>
                            <option value="JSS 1">JSS 1</option>
                            <option value="JSS 2">JSS 2</option>
                            <option value="JSS 3">JSS 3</option>
                            <option value="SSS 1">SSS 1</option>
                            <option value="SSS 2">SSS 2</option>
                            <option value="SSS 3">SSS 3</option>
                        </select>
                    </div>
                    <button type="submit" class="btn btn-secondary">Generate Student PIN</button>
                </form>
            </div>

            <div class="card">
                <h3>Add Question to Question Pool</h3>
                <form action="{{ url_for('add_question') }}" method="POST" style="margin-top:1rem;">
                    <div class="form-group">
                        <label>Target Class:</label>
                        <select name="student_class" required>
                            <option value="JSS 1">JSS 1</option>
                            <option value="JSS 2">JSS 2</option>
                            <option value="JSS 3">JSS 3</option>
                            <option value="SSS 1">SSS 1</option>
                            <option value="SSS 2">SSS 2</option>
                            <option value="SSS 3">SSS 3</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Subject:</label>
                        <input type="text" name="subject" placeholder="e.g. Mathematics" required>
                    </div>
                    <div class="form-group">
                        <label>Question Text:</label>
                        <input type="text" name="question_text" required>
                    </div>
                    <div class="grid">
                        <div class="form-group"><label>Option A:</label><input type="text" name="opt_a" required></div>
                        <div class="form-group"><label>Option B:</label><input type="text" name="opt_b" required></div>
                        <div class="form-group"><label>Option C:</label><input type="text" name="opt_c" required></div>
                        <div class="form-group"><label>Option D:</label><input type="text" name="opt_d" required></div>
                    </div>
                    <div class="form-group">
                        <label>Correct Option:</label>
                        <select name="correct_opt">
                            <option value="0">Option A</option>
                            <option value="1">Option B</option>
                            <option value="2">Option C</option>
                            <option value="3">Option D</option>
                        </select>
                    </div>
                    <button type="submit" class="btn">Add to Question Bank</button>
                </form>
            </div>
        </div>

        <div class="card">
            <h3>Registered Students & Access PINs</h3>
            <table>
                <thead>
                    <tr><th>Name</th><th>Class</th><th>Assigned PIN</th></tr>
                </thead>
                <tbody>
                    {% for s in students %}
                    <tr><td>{{ s[1] }}</td><td>{{ s[2] }}</td><td><strong style="color:var(--primary); font-size:1.1rem;">{{ s[3] }}</strong></td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="card">
            <h3>Live Exam Performance & Attempt Tracker</h3>
            <table>
                <thead>
                    <tr><th>Student</th><th>Class</th><th>Subject</th><th>Score %</th><th>Status</th><th>Total Attempts</th><th>Time</th></tr>
                </thead>
                <tbody>
                    {% for a in attempts %}
                    <tr>
                        <td>{{ a[2] }}</td>
                        <td>{{ a[3] }}</td>
                        <td>{{ a[4] }}</td>
                        <td><strong>{{ a[5] }}%</strong></td>
                        <td>
                            {% if a[6] == 'PASSED' %}
                            <span class="badge badge-pass">PASSED</span>
                            {% else %}
                            <span class="badge badge-fail">FAILED</span>
                            {% endif %}
                        </td>
                        <td>Attempt #{{ a[8] }}</td>
                        <td>{{ a[7] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- STUDENT EXAM SCREEN -->
        {% elif page == 'student_exam' %}
        <div class="card">
            <h2>Welcome, {{ session['name'] }}</h2>
            <p>Class: <strong>{{ session['class'] }}</strong></p>
        </div>

        <div class="card">
            <h3>Randomized Holiday Assessment</h3>
            {% if questions %}
            <form action="{{ url_for('submit_exam') }}" method="POST" style="margin-top: 1.5rem;">
                <input type="hidden" name="subject" value="{{ questions[0][2] }}">
                {% for q in questions %}
                <div class="question-box">
                    <p style="font-weight:bold; margin-bottom:0.5rem;">{{ loop.index }}. {{ q[3] }}</p>
                    <label style="display:block; margin:0.3rem 0;"><input type="radio" name="q_{{ q[0] }}" value="0" required> {{ q[4] }}</label>
                    <label style="display:block; margin:0.3rem 0;"><input type="radio" name="q_{{ q[0] }}" value="1"> {{ q[5] }}</label>
                    <label style="display:block; margin:0.3rem 0;"><input type="radio" name="q_{{ q[0] }}" value="2"> {{ q[6] }}</label>
                    <label style="display:block; margin:0.3rem 0;"><input type="radio" name="q_{{ q[0] }}" value="3"> {{ q[7] }}</label>
                </div>
                {% endfor %}
                <button type="submit" class="btn">Submit Assessment</button>
            </form>
            {% else %}
            <p style="margin-top:1rem; color:#666;">No questions available for your class yet. Please inform your teacher.</p>
            {% endif %}
        </div>

        <!-- RESULT SCREEN -->
        {% elif page == 'result' %}
        <div class="card" style="text-align:center;">
            <h2>Assessment Result</h2>
            <div style="font-size:3rem; font-weight:bold; margin:1rem 0; color: {{ 'var(--success)' if status == 'PASSED' else 'var(--fail)' }};">
                {{ score }}%
            </div>
            {% if status == 'PASSED' %}
            <h3 style="color:var(--success);">CONGRATULATIONS! YOU PASSED.</h3>
            <p style="margin:1rem 0;">Your score has been logged on the school dashboard.</p>
            <a href="{{ url_for('logout') }}" class="btn">Logout</a>
            {% else %}
            <h3 style="color:var(--fail);">SCORE BELOW 50%. RETAKE REQUIRED.</h3>
            <p style="margin:1rem 0;">School rules require a minimum pass mark of 50%. You must repeat this test.</p>
            <a href="{{ url_for('student_portal') }}" class="btn btn-secondary">Re-Take Test Now</a>
            {% endif %}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# ---------------------------------------------------------
# ROUTES AND LOGIC
# ---------------------------------------------------------
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, page='index')

@app.route('/staff_login', methods=['POST'])
def staff_login():
    username = request.form['username']
    password = request.form['password']
    
    conn = sqlite3.connect('cbt_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        session['user_id'] = user[0]
        session['name'] = user[1]
        session['role'] = user[2]
        return redirect(url_for('dashboard'))
    else:
        flash("Invalid Staff Credentials")
        return redirect(url_for('index'))

@app.route('/student_login', methods=['POST'])
def student_login():
    pin = request.form['pin']
    
    conn = sqlite3.connect('cbt_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, fullname, student_class FROM students WHERE pin = ?", (pin,))
    student = cursor.fetchone()
    conn.close()
    
    if student:
        session['student_id'] = student[0]
        session['name'] = student[1]
        session['class'] = student[2]
        return redirect(url_for('student_portal'))
    else:
        flash("Invalid 6-Digit PIN. Please check with your teacher.")
        return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
        
    conn = sqlite3.connect('cbt_database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, fullname, student_class, pin FROM students")
    students = cursor.fetchall()
    
    # Query attempts with total attempt counts aggregated per student
    cursor.execute('''
        SELECT a.id, a.student_id, a.student_name, a.student_class, a.subject, a.score_percent, a.status, a.timestamp,
        (SELECT COUNT(*) FROM attempts a2 WHERE a2.student_id = a.student_id) as total_attempts
        FROM attempts a ORDER BY a.timestamp DESC
    ''')
    attempts = cursor.fetchall()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, page='dashboard', students=students, attempts=attempts)

@app.route('/add_teacher', methods=['POST'])
def add_teacher():
    if session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    username = request.form['username']
    password = request.form['password']
    
    conn = sqlite3.connect('cbt_database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, 'teacher')", (username, password))
        conn.commit()
    except sqlite3.IntegrityError:
        flash("Username already exists!")
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/add_student', methods=['POST'])
def add_student():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    fullname = request.form['fullname']
    student_class = request.form['student_class']
    pin = generate_pin()
    
    conn = sqlite3.connect('cbt_database.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO students (fullname, student_class, pin) VALUES (?, ?, ?)", (fullname, student_class, pin))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/add_question', methods=['POST'])
def add_question():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    student_class = request.form['student_class']
    subject = request.form['subject']
    q_text = request.form['question_text']
    opt_a = request.form['opt_a']
    opt_b = request.form['opt_b']
    opt_c = request.form['opt_c']
    opt_d = request.form['opt_d']
    correct = int(request.form['correct_opt'])
    
    conn = sqlite3.connect('cbt_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO questions (student_class, subject, question_text, option_a, option_b, option_c, option_d, correct_option)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (student_class, subject, q_text, opt_a, opt_b, opt_c, opt_d, correct))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/student_portal')
def student_portal():
    if 'student_id' not in session:
        return redirect(url_for('index'))
        
    student_class = session['class']
    conn = sqlite3.connect('cbt_database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, student_class, subject, question_text, option_a, option_b, option_c, option_d FROM questions WHERE student_class = ?", (student_class,))
    all_questions = cursor.fetchall()
    conn.close()
    
    # Randomly shuffle and select up to 10 questions from class pool
    random.shuffle(all_questions)
    selected_questions = all_questions[:10]
    
    return render_template_string(HTML_TEMPLATE, page='student_exam', questions=selected_questions)

@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    if 'student_id' not in session:
        return redirect(url_for('index'))
        
    subject = request.form.get('subject', 'General')
    conn = sqlite3.connect('cbt_database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, correct_option FROM questions WHERE student_class = ?", (session['class'],))
    questions = cursor.fetchall()
    
    correct_count = 0
    total = len(questions)
    
    for q in questions:
        q_id = str(q[0])
        correct_opt = q[1]
        user_ans = request.form.get(f'q_{q_id}')
        if user_ans is not None and int(user_ans) == correct_opt:
            correct_count += 1
            
    score_percent = Math.round((correct_count / total) * 100) if total > 0 else 0
    status = "PASSED" if score_percent >= 50 else "FAILED"
    
    # Log attempt into database
    cursor.execute('''
        INSERT INTO attempts (student_id, student_name, student_class, subject, score_percent, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session['student_id'], session['name'], session['class'], subject, score_percent, status))
    conn.commit()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, page='result', score=score_percent, status=status)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
