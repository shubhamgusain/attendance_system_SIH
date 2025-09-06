import os
import io
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import pandas as pd


# Flask app setup
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'   # Change for production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload size
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


db = SQLAlchemy(app)
bcrypt = Bcrypt(app)


# User model extended with workbook path
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='user')
    workbook_path = db.Column(db.String(255), nullable=True)  # path to uploaded excel


    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')


    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


with app.app_context():
    db.create_all()


# Complete front-end template with login/register and styling
home_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8" />
    <title>Student Attendance System - Login/Register</title>
    <style>
        body { margin:0; padding:0; font-family: 'Segoe UI', Arial, sans-serif; background:#f4f4f4; height: 100vh;
               display: flex; align-items: center; justify-content:center; }
        .container { display: flex; width: 900px; height: 520px; box-shadow: 0 0 20px rgba(0,0,0,0.1);
                     border-radius: 10px; overflow: hidden; background: white; }
        .left { background: #2176bf; color: #fff; flex: 1; display: flex; flex-direction: column;
                justify-content: center; align-items: center; }
        .left svg { margin-bottom: 30px; }
        .left h2 { font-size: 32px; font-weight: 500; text-align: center; padding: 0 10px;}
        .right { flex: 1; padding: 30px 40px; display: flex; flex-direction: column; }
        .tabs { display: flex; margin-bottom: 30px; }
        .tab { flex: 1; padding: 15px; text-align: center; cursor: pointer; border-bottom: 3px solid transparent;
               font-weight: 600; font-size: 18px; color: #2176bf; transition: border-color 0.3s; }
        .tab.active { border-bottom: 3px solid #2176bf; font-weight: 700; }
        form { flex: 1; overflow-y: auto; }
        .form-group { position: relative; margin-bottom: 20px; }
        input[type="text"], input[type="password"], input[type="file"] {
            width: 100%; padding: 12px 40px 12px 10px; box-sizing: border-box; font-size: 16px;
            border: 1px solid #ccc; border-radius: 6px;
        }
        .eye { position: absolute; right: 12px; top: 13px; font-size: 20px; color: #888; cursor: pointer; }
        button {
            width: 100%; background: #2176bf; color: white; border: none; border-radius: 6px;
            padding: 14px; font-size: 20px; cursor: pointer; transition: background 0.3s ease;
        }
        button:hover { background: #185c97; }
        .message { margin-top: 10px; font-size: 14px; color: red; }
        .success { color: green; }
    </style>
</head>
<body>
    <div class="container">
        <div class="left">
            <!-- Graduation Cap SVG Icon -->
            <svg width="90" height="90" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M2 7l10-5 10 5-10 5-10-5z" fill="white"/>
                <path d="M2 7v6.236c0 2.484 3.258 4.5 9 4.5s9-2.016 9-4.5V7l-9 4.5L2 7z" fill="white"/>
            </svg>
            <h2>Student Attendance System</h2>
        </div>
        <div class="right">
            <div class="tabs">
                <div class="tab active" id="login_tab" onclick="showForm('login')">Login</div>
                <div class="tab" id="register_tab" onclick="showForm('register')">Register</div>
            </div>
            <form id="login_form" method="post" style="display:block;" action="/">
                <input type="hidden" name="form_type" value="login">
                <div class="form-group">
                    <input type="text" name="username" placeholder="Username" required>
                </div>
                <div class="form-group">
                    <input type="password" id="login_password" name="password" placeholder="Password" required>
                    <span class="eye" onclick="togglePassword('login_password')">👁</span>
                </div>
                <button type="submit">Login</button>
                {% if login_error %}
                <div class="message">{{ login_error }}</div>
                {% endif %}
            </form>
            <form id="register_form" method="post" style="display:none;" action="/" enctype="multipart/form-data">
                <input type="hidden" name="form_type" value="register">
                <div class="form-group">
                    <input type="text" name="username" placeholder="Username" required>
                </div>
                <div class="form-group">
                    <input type="password" id="register_password" name="password" placeholder="Password" required>
                    <span class="eye" onclick="togglePassword('register_password')">👁</span>
                </div>
                <div class="form-group">
                    <input type="text" name="role" placeholder="Role (optional)">
                </div>
                <div class="form-group">
                    <label>Upload Your Excel Workbook (.xlsx):</label><br>
                    <input type="file" name="workbook" accept=".xlsx" required>
                </div>
                <button type="submit">Register</button>
                {% if register_error %}
                <div class="message">{{ register_error }}</div>
                {% endif %}
                {% with messages = get_flashed_messages(category_filter=["success"]) %}
                    {% if messages %}
                        <div class="message success">{{ messages[0] }}</div>
                    {% endif %}
                {% endwith %}
            </form>
        </div>
    </div>
    <script>
        function togglePassword(id) {
            var pwd = document.getElementById(id);
            pwd.type = pwd.type === 'password' ? 'text' : 'password';
        }
        function showForm(form) {
            if(form === 'login') {
                document.getElementById('login_form').style.display = 'block';
                document.getElementById('register_form').style.display = 'none';
                document.getElementById('login_tab').classList.add('active');
                document.getElementById('register_tab').classList.remove('active');
            } else {
                document.getElementById('login_form').style.display = 'none';
                document.getElementById('register_form').style.display = 'block';
                document.getElementById('login_tab').classList.remove('active');
                document.getElementById('register_tab').classList.add('active');
            }
        }
    </script>
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
        role = request.form.get('role') or 'user'
        if form_type == 'login':
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['workbook_path'] = user.workbook_path
                return redirect(url_for('dashboard'))
            else:
                login_error = 'Invalid username or password.'
        elif form_type == 'register':
            if User.query.filter_by(username=username).first():
                register_error = 'Username already exists!'
            else:
                workbook_file = request.files.get('workbook')
                if not workbook_file or not workbook_file.filename.endswith('.xlsx'):
                    register_error = "Please upload a valid Excel (.xlsx) workbook."
                else:
                    safe_filename = secure_filename(workbook_file.filename)
                    user_folder = os.path.join(app.config['UPLOAD_FOLDER'], username)
                    os.makedirs(user_folder, exist_ok=True)
                    workbook_path = os.path.join(user_folder, safe_filename)
                    workbook_file.save(workbook_path)
                    user = User(username=username, role=role, workbook_path=workbook_path)
                    user.set_password(password)
                    db.session.add(user)
                    db.session.commit()
                    flash('Registration successful! Please log in.', "success")
                    return redirect(url_for('home'))
    return render_template_string(home_html,
                                  login_error=login_error,
                                  register_error=register_error)



@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    workbook_path = session.get('workbook_path')
    file_info = workbook_path if workbook_path and os.path.exists(workbook_path) else "No workbook uploaded."
    return f"""
    <h1>Welcome, {session.get('username')}!</h1>
    <p>Your workbook file: {file_info}</p>
    <p><a href='/download_workbook'>Download Workbook</a></p>
    <p><a href='/add_student'>Add New Student Detail</a></p>
    <p><a href='/logout'>Logout</a></p>
    """



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
                            
                            # Load all sheets into dict of DataFrames
                            all_sheets = {sheet: pd.read_excel(xls, sheet_name=sheet, engine='openpyxl') for sheet in xls.sheet_names}
                            # Update the target sheet with new data
                            all_sheets[class_sheet] = df
                            
                            # Write all sheets freshly to the workbook file (overwrite)
                            with pd.ExcelWriter(workbook_path, engine='openpyxl') as writer:
                                for sheet_name, sheet_df in all_sheets.items():
                                    sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)

                            message = f"Student {name} added to class {class_sheet} successfully!"
                    except Exception as e:
                        error = f"Error updating workbook: {e}"





    form_html = """
    <h2>Add New Student Detail</h2>
    {% if message %}
        <p style="color: green;">{{ message }}</p>
    {% endif %}
    {% if error %}
        <p style="color: red;">{{ error }}</p>
    {% endif %}
    <form method="post" action="">
        <label>Class (Sheet Name):</label><br>
        <input type="text" name="class_name" required><br><br>
        <label>Name:</label><br>
        <input type="text" name="name" required><br><br>
        <label>Roll No.:</label><br>
        <input type="number" name="roll_no" required><br><br>
        <label>Father's Name:</label><br>
        <input type="text" name="fathers_name"><br><br>
        <label>Contact:</label><br>
        <input type="text" name="contact"><br><br>
        <button type="submit">Add Student</button>
    </form>
    <p><a href="{{ url_for('dashboard') }}">Back to Dashboard</a></p>
    """
    return render_template_string(form_html, message=message, error=error)



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))



if __name__ == '__main__':
    app.run(debug=True)
