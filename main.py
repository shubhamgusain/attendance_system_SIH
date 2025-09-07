import os
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    workbook_path = db.Column(db.String(255), nullable=True)
    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

with app.app_context():
    db.create_all()

modern_frontend = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>EduAttend Pro – Automated Attendance for Schools</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        html,body{margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;}
        body{background:#f4f4f6;}
        .container{max-width:900px;margin:50px auto;}
        .card{background:#fff;border-radius:16px;box-shadow:0 6px 24px rgba(50,50,93,.09);padding:32px;}
        /* Hero */
        .hero{display:flex;flex-wrap:wrap;align-items:center;gap:32px;margin-bottom:32px;}
        .hero-text{flex:1}
        .hero-title{font-size:2.7rem;font-weight:700;line-height:1.15;margin-bottom:18px;}
        .hero-gradient{background:linear-gradient(94deg,#2176bf,#27c1a3,#fd7646);-webkit-background-clip:text;color:transparent;}
        .hero-desc{color:#334155;font-size:1.16rem;}
        .hero-actions{margin:32px 0 0;display:flex;gap:12px;flex-wrap:wrap;}
        .hero-image{flex:1;display:flex;align-items:center;justify-content:center;}
        .hero-image img{width:320px;max-width:100%;border-radius:12px;box-shadow:0 1px 20px rgba(33,118,191,.08);}
        /* Tabs/forms */
        .tab-navs{display:flex;gap:0;}
        .tab-btn{flex:1;padding:13px;font-weight:600;font-size:1.04rem;border:none;border-bottom:3px solid transparent;background:none;cursor:pointer;}
        .tab-btn.active{border-color:#2176bf;color:#2176bf;}
        .form-card{padding:20px 0 0}
        form{display:flex;flex-direction:column;gap:18px;}
        input[type='text'],input[type='password'],input[type='file']{
            padding:10px 12px;font-size:1rem;border:1.4px solid #d0d7de;border-radius:7px;}
        button[type='submit']{background:#2176bf;color:#fff;border:none;border-radius:8px;padding:12px 0;margin-top:8px;font-size:1.12rem;cursor:pointer;font-weight:600;}
        button[type='submit']:hover{background:#185c97;}
        .message{font-size:.98rem;}
        .message.error{color:#c62828;}
        .message.success{color:#27a466;}
        /* Dashboard */
        .dashboard{max-width:520px;margin:42px auto;}
        .dashboard label{color:#444;font-size:1.02rem;margin-bottom:2px;display:block;}
        .dash-box{background:#f4f8fb;padding:16px 20px;border-radius:10px;margin-bottom:22px;}
        .dash-links a{margin-right:16px;color:#2176bf;font-weight:500;text-decoration:none;}
    </style>
    <script>
        function switchTab(tab){
            document.getElementById('loginTabBtn').classList.remove('active');
            document.getElementById('registerTabBtn').classList.remove('active');
            document.getElementById('loginFrm').style.display='none';
            document.getElementById('registerFrm').style.display='none';
            if(tab=='login'){
                document.getElementById('loginTabBtn').classList.add('active');
                document.getElementById('loginFrm').style.display='block';
            }else{
                document.getElementById('registerTabBtn').classList.add('active');
                document.getElementById('registerFrm').style.display='block';
            }
        }
    </script>
</head>
<body>
<div class="container">
    <div class="card">
        <div class="hero">
            <div class="hero-text">
                <div class="hero-title"><span class="hero-gradient">EduAttend Pro</span></div>
                <div class="hero-desc">
                    Next-gen, offline-ready <b>automated attendance system</b> for rural schools.<br>
                    Secure, fast, simple – streamline school management and empower teachers.
                </div>
                <div class="hero-actions">
                    <button class="tab-btn active" id="loginTabBtn" onclick="switchTab('login')">Login</button>
                    <button class="tab-btn" id="registerTabBtn" onclick="switchTab('register')">Register</button>
                </div>
            </div>
            <div class="hero-image">
                <img src="https://images.unsplash.com/photo-1497486751825-1233686d5d80?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&q=80" alt="Attendance">
            </div>
        </div>
        <div class="form-card">
        {% with messages = get_flashed_messages(category_filter=['success']) %}
            {% if messages %}<div class="message success">{{ messages[0] }}</div>{% endif %}
        {% endwith %}
            {% if login_error %}<div class="message error">{{ login_error }}</div>{% endif %}
            {% if register_error %}<div class="message error">{{ register_error }}</div>{% endif %}
            <!-- Login form -->
            <form method="post" id="loginFrm" style="display:block;">
                <input type="hidden" name="form_type" value="login">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <button type="submit">Login</button>
            </form>
            <!-- Register form -->
            <form method="post" id="registerFrm" style="display:none;" enctype="multipart/form-data">
                <input type="hidden" name="form_type" value="register">
                <input type="text" name="username" placeholder="Username" required>
                <input type="password" name="password" placeholder="Password" required>
                <input type="password" name="password2" placeholder="Confirm Password" required>
                <input type="file" name="workbook" accept=".xlsx" required>
                <button type="submit">Register</button>
            </form>
        </div>
    </div>
    {% if session['user_id'] %}
    <div class="dashboard card">
        <h2>Hello, {{ session['username'] }}</h2>
        <div class="dash-box">
            <label>Workbook:</label>
            {% if session['workbook_path'] and os.path.exists(session['workbook_path']) %}
                <b>{{ session['workbook_path'].split('/')[-1] }}</b>
            {% else %}
                <span>No workbook uploaded.</span>
            {% endif %}
        </div>
        <div class="dash-links">
            <a href="{{ url_for('download_workbook') }}">Download Workbook</a>
            <a href="{{ url_for('add_student') }}">Add Student</a>
            <a href="{{ url_for('logout') }}">Logout</a>
        </div>
    </div>
    {% endif %}
</div>
<script>
    // On page load, show login tab if no errors in registration
    {% if register_error %}switchTab('register');{% endif %}
</script>
</body>
</html>
"""

add_student_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Add Student - EduAttend Pro</title>
    <style>
    body{font-family:'Segoe UI',Arial,sans-serif;background:#f9fbfc;}
    .container{max-width:470px;margin:60px auto;}
    .card{background:#fff;padding:30px;border-radius:10px;box-shadow:0 2px 18px rgba(33,118,191,.10);}
    .title{font-size:1.44rem;font-weight:600;margin-bottom:26px;text-align:center;}
    label{display:block;margin-bottom:6px;color:#222;}
    input{width:100%;padding:9px;margin-bottom:11px;border:1.2px solid #d1d5db;border-radius:6px;}
    button{background:#2176bf;color:#fff;border:none;border-radius:6px;padding:11px 0;width:100%;font-size:1.13rem;font-weight:600;}
    button:hover{background:#185c97;}
    .msg{margin:12px 0 0;font-size:1.01rem;color:green;}
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <div class="title">Add Student</div>
        {% if message %}
        <div class="msg">{{ message }}</div>
        {% endif %}
        {% if error %}
        <div class="msg" style="color:red">{{ error }}</div>
        {% endif %}
        <form method="post">
            <label>Class Name:</label>
            <input type="text" name="class_name" required>
            <label>Student Name:</label>
            <input type="text" name="name" required>
            <label>Roll Number:</label>
            <input type="number" name="roll_no" required>
            <label>Father's Name:</label>
            <input type="text" name="fathers_name">
            <label>Contact:</label>
            <input type="text" name="contact">
            <button type="submit">Add Student</button>
        </form>
        <br>
        <a href="{{ url_for('dashboard') }}">Back to Dashboard</a>
    </div>
</div>
</body>
</html>
"""

@app.route('/', methods=['GET', 'POST'])
def home():
    login_error = None
    register_error = None
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if form_type == 'login':
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['workbook_path'] = user.workbook_path
                session['role'] = user.role
                return redirect(url_for('dashboard'))
            else:
                login_error = 'Invalid username or password.'
        elif form_type == 'register':
            password2 = request.form.get('password2', '').strip()
            if password != password2:
                register_error = 'Passwords do not match.'
            elif User.query.filter_by(username=username).first():
                register_error = 'Username already exists!'
            else:
                workbook = request.files.get('workbook')
                if not workbook or not workbook.filename.endswith('.xlsx'):
                    register_error = "Please upload a valid Excel (.xlsx) workbook."
                else:
                    safe_filename = secure_filename(workbook.filename)
                    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
                    os.makedirs(user_folder, exist_ok=True)
                    workbook_path = os.path.join(user_folder, safe_filename)
                    workbook.save(workbook_path)
                    user = User(username=username, role='user', workbook_path=workbook_path)
                    user.set_password(password)
                    db.session.add(user)
                    db.session.commit()
                    flash('Registration successful! Please log in.', "success")
                    return redirect(url_for('home'))
    return render_template_string(modern_frontend, login_error=login_error, register_error=register_error, os=os, session=session)

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id'):
        return redirect(url_for('home'))
    # This just redisplays the home (with dashboard card shown)
    return redirect(url_for('home'))

@app.route('/download_workbook')
def download_workbook():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    path = session.get('workbook_path')
    if path and os.path.exists(path):
        return send_file(path, as_attachment=True)
    return abort(404)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    message = None
    error = None
    if request.method == 'POST':
        class_sheet = request.form.get('class_name')
        name = request.form.get('name')
        roll_no = request.form.get('roll_no')
        fathers_name = request.form.get('fathers_name')
        contact = request.form.get('contact')

        if not all([class_sheet, name, roll_no]):
            error = "Please fill all required fields (Class, Name, Roll No)."
        else:
            try:
                roll_no_int = int(roll_no)
            except ValueError:
                error = "Roll No must be an integer."
            if not error:
                workbook_path = session.get('workbook_path')
                if not workbook_path or not os.path.exists(workbook_path):
                    error = "Workbook file not found. Please upload again."
                else:
                    try:
                        xls = pd.ExcelFile(workbook_path)
                        if class_sheet in xls.sheet_names:
                            df = pd.read_excel(xls, sheet_name=class_sheet, engine='openpyxl')
                        else:
                            df = pd.DataFrame(columns=["S.No.", "Name", "Roll No.", "Father's Name", "Contact"])
                        if roll_no_int in df["Roll No."].values:
                            error = f"Roll No {roll_no_int} already exists in class {class_sheet}."
                        else:
                            next_s_no = int(df["S.No."].max()) + 1 if not df.empty else 1
                            new_row = {"S.No.": next_s_no, "Name": name, "Roll No.": roll_no_int,
                                       "Father's Name": fathers_name, "Contact": contact}
                            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                            all_sheets = {sheet: pd.read_excel(xls, sheet_name=sheet, engine='openpyxl') for sheet in xls.sheet_names}
                            all_sheets[class_sheet] = df
                            with pd.ExcelWriter(workbook_path, engine='openpyxl') as writer:
                                for sheet_name, sheet_df in all_sheets.items():
                                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
                            message = f"Student {name} added to class {class_sheet} successfully!"
                    except Exception as e:
                        error = f"Error updating workbook: {e}"
    return render_template_string(add_student_html, message=message, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)