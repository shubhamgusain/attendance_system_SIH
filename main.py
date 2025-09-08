import os
import base64
import datetime
import numpy as np
import pandas as pd
import cv2
from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_file, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MODEL_PATH'] = 'models/face_recognizer.yml'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.dirname(app.config['MODEL_PATH']), exist_ok=True)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Replace with your MySQL credentials
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'rishu6377',
    'database': 'attendance_db'
}

conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor()
cursor.execute("SELECT id, class_name, roll_no, image_data FROM face_images LIMIT 5")
rows = cursor.fetchall()
for id_, cls, roll, img_blob in rows:
    filename = f"{cls}_{roll}_{id_}.jpg"
    with open(filename, 'wb') as f:
        f.write(img_blob)
    print(f"Saved image: {filename}")
cursor.close()
conn.close()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    workbook_path = db.Column(db.String(256))

    def set_password(self, pw):
        self.password_hash = bcrypt.generate_password_hash(pw).decode()

    def check_password(self, pw):
        return bcrypt.check_password_hash(self.password_hash, pw)

with app.app_context():
    db.create_all()

def get_mysql_connection():
    return mysql.connector.connect(**DB_CONFIG)

def save_face_images(class_name, roll_no, images):
    conn = get_mysql_connection()
    cursor = conn.cursor()
    for img_b64 in images:
        if ',' in img_b64:
            img_b64 = img_b64.split(',')[1]
        img_bytes = base64.b64decode(img_b64)
        cursor.execute("INSERT INTO face_images (class_name, roll_no, image_data) VALUES (%s, %s, %s)", (class_name, roll_no, img_bytes))
    conn.commit()
    cursor.close()
    conn.close()

def load_face_data():
    conn = get_mysql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT class_name, roll_no, image_data FROM face_images")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    faces, labels, label_map = [], [], {}
    current_label = 0
    for c, r, img_data in rows:
        key = f"{c}-{r}"
        if key not in label_map:
            label_map[key] = current_label
            current_label += 1
        label = label_map[key]
        nparr = np.frombuffer(img_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if img is not None:
            img = cv2.resize(img, (200, 200))
            faces.append(img)
            labels.append(label)
    return faces, labels, label_map

def train_and_save_model():
    faces, labels, _ = load_face_data()
    if not faces:
        return False, "No face data available."
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.train(faces, np.array(labels))
    recognizer.write(app.config['MODEL_PATH'])
    return True, "Model trained successfully."

HOME_HTML = '''
<!doctype html>
<html>
<head>
<title>Login / Register</title>
<style>
  body { font-family: Arial, sans-serif; background: #eef2f7; }
  .container { width: 300px; margin: 50px auto; background: #fff; padding: 20px; border-radius: 10px; box-shadow: 0 0 15px #aaa; }
  h2 { text-align: center; margin-bottom: 20px; }
  input, button { width: 100%; padding: 10px; margin: 8px 0; border-radius: 5px; border: 1px solid #ccc; font-size: 14px; }
  button { background: #1764c7; color: white; border: none; font-weight: bold; cursor: pointer; }
  button:hover { background: #124f91; }
  .toggle { text-align: center; color: #1764c7; cursor: pointer; margin-top: 15px; }
  .message { text-align: center; color: red; margin-bottom: 12px; }
  .message.success { color: green; }
</style>
</head>
<body>
<div class="container">
<h2 id="title">Login</h2>
{% if error_msg %}<div class="message">{{ error_msg }}</div>{% endif %}
{% if success_msg %}<div class="message success">{{ success_msg }}</div>{% endif %}
<form id="login_form" method="POST">
<input type="hidden" name="action" value="login"/>
<input name="username" placeholder="Username" required autofocus/>
<input type="password" name="password" placeholder="Password" required/>
<button type="submit">Login</button>
</form>
<form id="register_form" method="POST" enctype="multipart/form-data" style="display:none;">
<input type="hidden" name="action" value="register"/>
<input name="username" placeholder="Username" required/>
<input type="password" name="password" placeholder="Password" required/>
<input type="password" name="password2" placeholder="Confirm Password" required/>
<input type="file" name="workbook" accept=".xlsx" required/>
<button type="submit">Register</button>
</form>
<div class="toggle" onclick="toggleForms()">Don't have an account? Register</div>
</div>
<script>
function toggleForms() {
  let loginForm = document.getElementById('login_form');
  let regForm = document.getElementById('register_form');
  let title = document.getElementById('title');
  if(loginForm.style.display === 'none') {
    loginForm.style.display = 'block';
    regForm.style.display = 'none';
    title.innerText = 'Login';
  } else {
    loginForm.style.display = 'none';
    regForm.style.display = 'block';
    title.innerText = 'Register';
  }
}
</script>
</body>
</html>
'''

DASHBOARD_HTML = '''
<!doctype html>
<html>
<head>
<title>Dashboard</title>
<style>
  body { font-family: Arial, sans-serif; background: #eef2f7; }
  .container { max-width: 600px; margin: 40px auto; background: #fff; padding: 25px; border-radius: 10px; box-shadow: 0 0 20px #aaa; text-align: center; }
  h2 { margin-bottom: 20px; }
  button, a { padding: 12px 25px; margin: 10px; font-weight: bold; border: none; border-radius: 7px; color: white; cursor: pointer; background: #1764c7; text-decoration: none; }
  button:hover, a:hover { background: #124f91; }
  #captureModal { display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.6); justify-content: center; align-items: center; z-index: 999; }
  #captureModal div { background: white; padding: 20px; border-radius: 10px; }
  input { width: 80%; padding: 8px; margin: 10px 0; border-radius: 5px; border: 1px solid #ccc; }
  video { border-radius: 10px; margin-top: 10px; }
</style>
</head>
<body>
<div class="container">
<h2>Welcome, {{ username }}</h2>
<p>Uploaded Workbook: <strong>{{ workbook }}</strong></p>
<a href="{{ url_for('download_workbook') }}">Download Workbook</a>
<a href="{{ url_for('add_student') }}">Add Student</a>
<button onclick="showCapture()">Capture Face</button>
<form action="{{ url_for('train_model') }}" method="post" style="display:inline;">
  <button type="submit">Train Model</button>
</form>
<a href="{{ url_for('mark_attendance') }}">Mark Attendance</a>
<a href="{{ url_for('logout') }}">Logout</a>
</div>

<div id="captureModal">
  <div>
    <h3>Face Capture</h3>
    <input type="text" id="className" placeholder="Class name" /><br/>
    <input type="text" id="rollNo" placeholder="Roll number" /><br/>
    <video id="video" width="320" height="240" autoplay muted></video>
    <p id="statusMsg"></p>
    <button id="startCaptureBtn">Start Capture</button>
    <button id="uploadCaptureBtn" disabled>Upload Images</button>
    <button onclick="closeCapture()">Cancel</button>
  </div>
</div>

<script>
let video = document.getElementById('video');
let stream = null;
let capturedImages = [];
let capturing = false;

function showCapture() {
  document.getElementById('captureModal').style.display = 'flex';
}

function closeCapture() {
  document.getElementById('captureModal').style.display = 'none';
  capturedImages = [];
  capturing = false;
  document.getElementById('statusMsg').innerText = '';
  document.getElementById('uploadCaptureBtn').disabled = true;
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
    stream = null;
  }
}

document.getElementById('startCaptureBtn').onclick = async () => {
  let className = document.getElementById('className').value.trim();
  let rollNo = document.getElementById('rollNo').value.trim();
  if(!className || !rollNo) { alert('Please enter Class and Roll Number'); return; }
  if(capturing) return;

  if(!stream) {
    try {
      stream = await navigator.mediaDevices.getUserMedia({video:true});
      video.srcObject = stream;
    } catch(e) {
      alert('Cannot access webcam');
      return;
    }
  }

  capturing = true;
  capturedImages = [];
  document.getElementById('statusMsg').innerText = 'Capturing 20 images...';

  let count = 0;
  let interval = setInterval(() => {
    if(count >= 20){
      clearInterval(interval);
      document.getElementById('statusMsg').innerText = 'Captured 20 images';
      capturing = false;
      document.getElementById('uploadCaptureBtn').disabled = false;
      return;
    }
    let canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 320;
    canvas.height = video.videoHeight || 240;
    canvas.getContext('2d').drawImage(video, 0, 0, canvas.width, canvas.height);
    let dataURL = canvas.toDataURL('image/jpeg');
    capturedImages.push(dataURL);
    count++;
  }, 200);
};

document.getElementById('uploadCaptureBtn').onclick = async () => {
  let className = document.getElementById('className').value.trim();
  let rollNo = document.getElementById('rollNo').value.trim();
  if(capturedImages.length === 0) {
    alert('No images captured');
    return;
  }
  let formData = new FormData();
  formData.append('class_name', className);
  formData.append('roll_no', rollNo);
  capturedImages.forEach(img => formData.append('images', img));

  try {
    let res = await fetch('/capture_face', { method: 'POST', body: formData });
    if(res.redirected) {
      window.location.href = res.url;
    } else {
      alert('Upload complete but no redirect');
    }
  } catch(e) {
    alert('Upload failed: ' + e.message);
  }
}
</script>
</body>
</html>
'''

ADD_STUDENT_HTML = '''
<!DOCTYPE html>
<html><head><title>Add Student</title>
<style>
body {font-family: Arial; background:#eef;}
.container {width:400px;margin:50px auto;background:#fff;padding:20px;border-radius:10px;box-shadow:0 0 15px #aaa;}
h2 {text-align:center; margin-bottom: 20px;}
input,button {width:100%; padding:10px; margin:10px 0; border-radius:6px; border:1px solid #ccc;}
button {background:#2874f0; color:white; font-weight:bold; border:none; cursor:pointer;}
button:hover {background:#124f91;}
.message {color:green; text-align:center;}
.error {color:red; text-align:center;}
</style>
</head><body>
<div class="container">
<h2>Add Student</h2>
{% if message %}
  <p class="message">{{ message }}</p>
{% endif %}
{% if error %}
  <p class="error">{{ error }}</p>
{% endif %}
<form method="POST">
  <input name="class_name" placeholder="Class Name" required/>
  <input name="name" placeholder="Student Name" required/>
  <input type="number" name="roll_no" placeholder="Roll Number" required/>
  <input name="fathers_name" placeholder="Father's Name"/>
  <input name="contact" placeholder="Contact"/>
  <button type="submit">Add Student</button>
</form>
<p><a href="{{ url_for('dashboard') }}">Back to Dashboard</a></p>
</div>
</body></html>
'''

# Routes

@app.route('/', methods=['GET','POST'])
def home():
    error = None
    success = None
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username','').strip()
        password = request.form.get('password')
        if action == 'login':
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['workbook_path'] = user.workbook_path
                return redirect(url_for('dashboard'))
            error = 'Invalid username or password'
        elif action == 'register':
            password2 = request.form.get('password2')
            workbook = request.files.get('workbook')
            if password != password2:
                error = 'Passwords do not match'
            elif User.query.filter_by(username=username).first():
                error = 'Username already taken'
            elif not workbook or not workbook.filename.endswith('.xlsx'):
                error = 'Upload valid Excel workbook (.xlsx)'
            else:
                userfolder = os.path.join(app.config['UPLOAD_FOLDER'], username)
                os.makedirs(userfolder, exist_ok=True)
                filepath = os.path.join(userfolder, workbook.filename)
                workbook.save(filepath)
                user = User(username=username, workbook_path=filepath)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                success = 'Registration successful. Please login.'
    return render_template_string(HOME_HTML, error_msg=error, success_msg=success)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('home'))
    username = session['username']
    workpath = session.get('workbook_path')
    wbname = os.path.basename(workpath) if workpath and os.path.exists(workpath) else "No workbook uploaded"
    return render_template_string(DASHBOARD_HTML, username=username, workbook=wbname)

@app.route('/download_workbook')
def download_workbook():
    if 'user_id' not in session: return redirect(url_for('home'))
    path = session.get('workbook_path')
    if path and os.path.exists(path):
        return send_file(path, as_attachment=True)
    return abort(404)

@app.route('/add_student', methods=['GET','POST'])
def add_student():
    if 'user_id' not in session: return redirect(url_for('home'))
    error = None
    message = None
    if request.method == 'POST':
        class_name = request.form.get('class_name')
        name = request.form.get('name')
        roll_no = request.form.get('roll_no')
        father = request.form.get('fathers_name')
        contact = request.form.get('contact')
        if not class_name or not name or not roll_no:
            error = 'Please fill required fields'
        else:
            try:
                roll_int = int(roll_no)
                workbook = session.get('workbook_path')
                if not workbook or not os.path.exists(workbook):
                    error = 'Workbook missing'
                else:
                    xl = pd.ExcelFile(workbook)
                    dfs = {sheet: xl.parse(sheet) for sheet in xl.sheet_names}
                    if class_name in dfs:
                        df = dfs[class_name]
                    else:
                        df = pd.DataFrame(columns=["S.No", "Name", "Roll Number", "Father's Name", "Contact"])
                    if str(roll_int) in df["Roll Number"].astype(str).values:
                        error = 'Roll number already exists'
                    else:
                        new_row = {"S.No": len(df)+1, "Name": name, "Roll Number": roll_int, "Father's Name": father or "", "Contact": contact or ""}
                        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        dfs[class_name] = df
                        with pd.ExcelWriter(workbook, engine='openpyxl') as writer:
                            for sheet, data in dfs.items():
                                data.to_excel(writer, sheet_name=sheet, index=False)
                        message = 'Student added successfully'
            except Exception as e:
                error = str(e)
    return render_template_string(ADD_STUDENT_HTML, error=error, message=message)

@app.route('/capture_face', methods=['POST'])
def capture_face():
    if 'user_id' not in session:
        flash('Login required', 'error')
        return redirect(url_for('home'))
    cls = request.form.get('class_name')
    roll_no = request.form.get('roll_no')
    images = request.form.getlist('images')
    if not cls or not roll_no or not images:
        flash('Incomplete capture data', 'error')
        return redirect(url_for('dashboard'))
    save_face_images(cls, roll_no, images)
    flash('Face images uploaded successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/train_model', methods=['POST'])
def train_model():
    if 'user_id' not in session:
        flash('Login required', 'error')
        return redirect(url_for('home'))
    success, msg = train_and_save_model()
    flash(msg, 'success' if success else 'error')
    return redirect(url_for('dashboard'))

@app.route('/mark_attendance')
def mark_attendance():
    if 'user_id' not in session:
        flash('Please login to access attendance', 'error')
        return redirect(url_for('home'))

    if not os.path.exists(app.config['MODEL_PATH']):
        flash('No trained model found. Please train the model first.', 'error')
        return redirect(url_for('dashboard'))

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(app.config['MODEL_PATH'])
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    workbook = session.get('workbook_path')
    if not workbook or not os.path.exists(workbook):
        flash('Attendance workbook not found', 'error')
        return redirect(url_for('dashboard'))

    xl = pd.ExcelFile(workbook)
    sheets = xl.sheet_names

    today_str = datetime.datetime.now().strftime('%d-%m-%Y')

    faces, labels, label_map = load_face_data()
    if not faces:
        flash('No face data available. Please capture face images and train the model.', 'error')
        return redirect(url_for('dashboard'))

    inv_label_map = {v: k for k, v in label_map.items()}

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        flash('Could not open webcam', 'error')
        return redirect(url_for('dashboard'))

    attendance_marked = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces_detected = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

        for (x, y, w, h) in faces_detected:
            face_roi = gray[y:y+h, x:x+w]
            face_roi = cv2.resize(face_roi, (200, 200))

            label, confidence = recognizer.predict(face_roi)
            print(f"DEBUG: Predicted label {label}, confidence {confidence}")

            # Increase threshold to accept less confident matches (adjust experimentally)
            threshold = 150

            if confidence < threshold and label in inv_label_map:
                student_key = inv_label_map[label]
                print(f"DEBUG: Recognized student key: {student_key}")

                if student_key is None:
                    text = "Recognition mismatch"
                    color = (0, 0, 255)
                    print("DEBUG: Student key not found in mapping")
                else:
                    try:
                        class_name, roll_no = student_key.split('-')
                    except Exception as e:
                        text = "Label format error"
                        color = (0, 0, 255)
                        print(f"DEBUG: Label split error: {e}")
                        break

                    if class_name in sheets:
                        df = xl.parse(class_name)
                        df.columns = df.columns.str.strip()

                        if today_str not in df.columns:
                            df[today_str] = ""

                        matched_rows = df.index[df['Roll Number'].astype(str) == roll_no].tolist()

                        if matched_rows:
                            idx = matched_rows[0]
                            df.at[idx, today_str] = 'P'

                            # Save updated sheet replacing old content
                            with pd.ExcelWriter(workbook, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                                df.to_excel(writer, sheet_name=class_name, index=False)

                            attendance_marked = True
                            text = f'Present: {roll_no}'
                            color = (0, 255, 0)
                            print(f"DEBUG: Successfully marked attendance for roll {roll_no} in class {class_name}")
                        else:
                            text = 'Roll number not found'
                            color = (0, 165, 255)
                            print(f"DEBUG: Roll number {roll_no} not found in sheet {class_name}")
                    else:
                        text = 'Class sheet missing'
                        color = (0, 0, 255)
                        print(f"DEBUG: Class sheet {class_name} missing in workbook")
            else:
                text = 'Unknown'
                color = (0, 0, 255)
                print(f"DEBUG: Face not recognized or confidence {confidence} too high")

            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            cv2.putText(frame, text, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            break  # Only process first face per frame to avoid multi-detection confusion

        cv2.imshow('Mark Attendance - Press q to exit', frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

        if attendance_marked:
            cv2.waitKey(2000)  # Pause 2 seconds to show marked attendance
            break

    cap.release()
    cv2.destroyAllWindows()

    if attendance_marked:
        flash('Attendance marked successfully!', 'success')
    else:
        flash('No attendance marked.', 'warning')

    return redirect(url_for('dashboard'))



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)