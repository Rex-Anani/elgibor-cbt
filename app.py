import os
import sqlite3
import random
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "elgibor_cbt_production_key_2026")

DATABASE = "database.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Students Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reg_number TEXT UNIQUE NOT NULL,
            fullname TEXT NOT NULL,
            class_level TEXT NOT NULL,
            section TEXT NOT NULL -- 'Primary' or 'Secondary'
        )
    ''')
    
    # Teachers Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            subject TEXT NOT NULL
        )
    ''')
    
    # Questions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            class_level TEXT NOT NULL,
            question_text TEXT NOT NULL,
            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,
            correct_option TEXT NOT NULL
        )
    ''')
    
    # Results Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            student_name TEXT,
            class_level TEXT,
            subject TEXT,
            score INTEGER,
            total_questions INTEGER,
            date_taken TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- TEMPLATES (Inline HTML for complete single-file deployment) ---

BASE_LAYOUT = '''
<!DOCTYPE html>
<html>
<head>
    <title>Great Elgibor Schools - CBT Portal</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; margin: 0; padding: 0; }
        .navbar { background: #1a365d; color: white; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; }
        .navbar h1 { margin: 0; font-size: 20px; }
        .container { max-width: 1000px; margin: 30px auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .btn { padding: 10px 18px; background: #2b6cb0; color: white; border: none; border-radius: 5px; text-decoration: none; cursor: pointer; display: inline-block; }
        .btn-danger { background: #e53e3e; }
        .btn-success { background: #38a169; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #e2e8f0; padding: 12px; text-align: left; }
        th { background: #edf2f7; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #cbd5e0; border-radius: 5px; box-sizing: border-box; }
        .timer-box { font-size: 20px; font-weight: bold; color: #e53e3e; background: #fff5f5; padding: 10px; border: 1px solid #feb2b2; border-radius: 5px; display: inline-block; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>Great Elgibor Schools CBT</h1>
        <div>
            {% if session.get('user') %}
                <span>Hello, {{ session['user_name'] }}</span> | 
                <a href="/logout" style="color:#feb2b2;">Logout</a>
            {% endif %}
        </div>
    </div>
    <div class="container">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

# --- PUBLIC & PORTAL ROUTES ---

@app.route('/')
def index():
    return render_template_string(BASE_LAYOUT + '''
    {% block content %}
    <h2 style="text-align:center;">Welcome to Great Elgibor Schools CBT Portal</h2>
    <div style="display:flex; justify-content:space-around; margin-top:40px;">
        <a href="/student/login" class="btn btn-success" style="padding:20px 40px; font-size:18px;">Student Portal</a>
        <a href="/teacher/login" class="btn" style="padding:20px 40px; font-size:18px;">Teacher Portal</a>
        <a href="/admin/login" class="btn btn-danger" style="padding:20px 40px; font-size:18px;">Admin Control</a>
    </div>
    {% endblock %}
    ''')

# --- STUDENT PORTAL & EXAM ENGINE ---

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        reg_num = request.form.get('reg_number').strip()
        conn = get_db_connection()
        student = conn.execute('SELECT * FROM students WHERE reg_number = ?', (reg_num,)).fetchone()
        conn.close()
        
        if student:
            session['user'] = 'student'
            session['student_id'] = student['id']
            session['user_name'] = student['fullname']
            session['class_level'] = student['class_level']
            return redirect('/student/dashboard')
        flash('Invalid Registration Number!')
        
    return render_template_string(BASE_LAYOUT + '''
    {% block content %}
    <h2>Student Login</h2>
    <form method="POST">
        <div class="form-group">
            <label>Registration Number</label>
            <input type="text" name="reg_number" placeholder="e.g., GES/2026/001" required>
        </div>
        <button type="submit" class="btn btn-success">Start Exam Session</button>
    </form>
    {% endblock %}
    ''')

@app.route('/student/dashboard')
def student_dashboard():
    if session.get('user') != 'student':
        return redirect('/student/login')
        
    conn = get_db_connection()
    subjects = conn.execute('SELECT DISTINCT subject FROM questions WHERE class_level = ?', (session['class_level'],)).fetchall()
    results = conn.execute('SELECT * FROM results WHERE student_id = ?', (session['student_id'],)).fetchall()
    conn.close()
    
    return render_template_string(BASE_LAYOUT + '''
    {% block content %}
    <h2>Student Dashboard ({{ session['class_level'] }})</h2>
    <h3>Available Tests</h3>
    <ul>
    {% for s in subjects %}
        <li><strong>{{ s['subject'] }}</strong> - <a href="/exam/take/{{ s['subject'] }}" class="btn">Take Exam</a></li>
    {% else %}
        <p>No exams currently set up for your class level.</p>
    {% endfor %}
    </ul>
    
    <h3 style="margin-top:30px;">Past Results</h3>
    <table>
        <tr><th>Subject</th><th>Score</th><th>Date</th></tr>
        {% for r in results %}
        <tr><td>{{ r['subject'] }}</td><td>{{ r['score'] }} / {{ r['total_questions'] }}</td><td>{{ r['date_taken'] }}</td></tr>
        {% endfor %}
    </table>
    {% endblock %}
    ''')

@app.route('/exam/take/<subject>')
def take_exam(subject):
    if session.get('user') != 'student':
        return redirect('/student/login')
        
    conn = get_db_connection()
    questions = conn.execute('SELECT * FROM questions WHERE subject = ? AND class_level = ?', 
                             (subject, session['class_level'])).fetchall()
    conn.close()
    
    if not questions:
        return redirect('/student/dashboard')
        
    q_list = [dict(q) for q in questions]
    random.shuffle(q_list) # Anti-cheat randomization
    
    return render_template_string(BASE_LAYOUT + '''
    {% block content %}
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <h2>Exam: {{ subject }}</h2>
        <div class="timer-box">Time Remaining: <span id="time">15:00</span></div>
    </div>
    
    <form id="examForm" action="/submit_exam" method="POST">
        <input type="hidden" name="subject" value="{{ subject }}">
        {% for q in questions %}
        <div style="background:#f7fafc; padding:15px; border-radius:8px; margin-bottom:20px;">
            <p><strong>Q{{ loop.index }}: {{ q['question_text'] }}</strong></p>
            <label><input type="radio" name="question_{{ q['id'] }}" value="A"> A) {{ q['option_a'] }}</label><br>
            <label><input type="radio" name="question_{{ q['id'] }}" value="B"> B) {{ q['option_b'] }}</label><br>
            <label><input type="radio" name="question_{{ q['id'] }}" value="C"> C) {{ q['option_c'] }}</label><br>
            <label><input type="radio" name="question_{{ q['id'] }}" value="D"> D) {{ q['option_d'] }}</label>
        </div>
        {% endfor %}
        <button type="submit" class="btn btn-success" style="width:100%; font-size:18px;">Submit Final Answers</button>
    </form>

    <script>
        // Anti-cheat & Timer Engine
        var duration = 15 * 60;
        var display = document.querySelector('#time');
        var timer = setInterval(function () {
            var minutes = int = parseInt(duration / 60, 10);
            var seconds = parseInt(duration % 60, 10);
            minutes = minutes < 10 ? "0" + minutes : minutes;
            seconds = seconds < 10 ? "0" + seconds : seconds;
            display.textContent = minutes + ":" + seconds;
            if (--duration < 0) {
                clearInterval(timer);
                alert("Time is up! Submitting automatically.");
                document.getElementById("examForm").submit();
            }
        }, 1000);

        // Tab focus detection alert
        document.addEventListener("visibilitychange", function() {
            if (document.hidden) {
                alert("Warning: Leaving exam tab is logged for anti-cheat tracking.");
            }
        });
    </script>
    {% endblock %}
    ''', questions=q_list, subject=subject)

@app.route('/submit_exam', methods=['POST'])
def submit_exam():
    if session.get('user') != 'student':
        return redirect('/student/login')
        
    subject = request.form.get('subject')
    conn = get_db_connection()
    questions = conn.execute('SELECT * FROM questions WHERE subject = ? AND class_level = ?', 
                             (subject, session['class_level'])).fetchall()
    
    score = 0
    total = len(questions)
    
    for q in questions:
        selected = request.form.get(f'question_{q["id"]}')
        if selected and selected.strip().upper() == q['correct_option'].strip().upper():
            score += 1
            
    conn.execute('''
        INSERT INTO results (student_id, student_name, class_level, subject, score, total_questions)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (session['student_id'], session['user_name'], session['class_level'], subject, score, total))
    conn.commit()
    conn.close()
    
    return render_template_string(BASE_LAYOUT + '''
    {% block content %}
    <div style="text-align:center; padding:30px;">
        <h2 style="color:#27ae60;">Exam Successfully Completed!</h2>
        <p>Student: <strong>{{ session['user_name'] }}</strong></p>
        <p>Subject: <strong>{{ subject }}</strong></p>
        <div style="font-size:42px; margin:20px 0; font-weight:bold;">Score: {{ score }} / {{ total }}</div>
        <a href="/student/dashboard" class="btn">Return to Dashboard</a>
    </div>
    {% endblock %}
    ''', subject=subject, score=score, total=total)

# --- ADMIN DASHBOARD & USER MANAGEMENT ---

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.form.get('password') == 'admin123': # Default initial password
            session['user'] = 'admin'
            session['user_name'] = 'Administrator'
            return redirect('/admin/dashboard')
    return render_template_string(BASE_LAYOUT + '''
    {% block content %}
    <h2>Admin Login</h2>
    <form method="POST">
        <div class="form-group">
            <label>Master Passcode</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit" class="btn btn-danger">Admin Access</button>
    </form>
    {% endblock %}
    ''')

@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('user') != 'admin':
        return redirect('/admin/login')
        
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students').fetchall()
    teachers = conn.execute('SELECT * FROM teachers').fetchall()
    results = conn.execute('SELECT * FROM results').fetchall()
    conn.close()
    
    return render_template_string(BASE_LAYOUT + '''
    {% block content %}
    <h2>Admin Control Center</h2>
    
    <h3>Add New Student</h3>
    <form action="/admin/add_student" method="POST" style="display:flex; gap:10px; margin-bottom:20px;">
        <input type="text" name="fullname" placeholder="Full Name" required>
        <input type="text" name="reg_number" placeholder="Reg Number" required>
        <select name="class_level">
            <option value="Primary 1">Primary 1</option>
            <option value="Primary 5">Primary 5</option>
            <option value="JSS 1">JSS 1</option>
            <option value="SSS 2">SSS 2</option>
        </select>
        <button type="submit" class="btn btn-success">Add Student</button>
    </form>

    <h3>Student Registry</h3>
    <table>
        <tr><th>Reg No</th><th>Name</th><th>Class</th><th>Action</th></tr>
        {% for s in students %}
        <tr>
            <td>{{ s['reg_number'] }}</td>
            <td>{{ s['fullname'] }}</td>
            <td>{{ s['class_level'] }}</td>
            <td>
                <form action="/admin/delete_student/{{ s['id'] }}" method="POST" onsubmit="return confirm('Delete {{ s['fullname'] }}?');">
                    <button type="submit" class="btn btn-danger">Delete</button>
                </form>
            </td>
        </tr>
        {% endfor %}
    </table>
    
    <h3 style="margin-top:30px;">School Master Results Record</h3>
    <table>
        <tr><th>Student</th><th>Class</th><th>Subject</th><th>Score</th><th>Date</th></tr>
        {% for r in results %}
        <tr><td>{{ r['student_name'] }}</td><td>{{ r['class_level'] }}</td><td>{{ r['subject'] }}</td><td>{{ r['score'] }}/{{ r['total_questions'] }}</td><td>{{ r['date_taken'] }}</td></tr>
        {% endfor %}
    </table>
    {% endblock %}
    ''', students=students, teachers=teachers, results=results)

@app.route('/admin/add_student', methods=['POST'])
def add_student():
    if session.get('user') == 'admin':
        conn = get_db_connection()
        conn.execute('INSERT INTO students (fullname, reg_number, class_level, section) VALUES (?, ?, ?, ?)',
                     (request.form['fullname'], request.form['reg_number'], request.form['class_level'], 'General'))
        conn.commit()
        conn.close()
    return redirect('/admin/dashboard')

@app.route('/admin/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    if session.get('user') == 'admin':
        conn = get_db_connection()
        conn.execute('DELETE FROM students WHERE id = ?', (student_id,))
        conn.commit()
        conn.close()
    return redirect('/admin/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --- PORT BINDING ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
