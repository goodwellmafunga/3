from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
import base64
import requests
from PIL import Image
import pytesseract
from io import BytesIO
from flask_sqlalchemy import SQLAlchemy
import re
from fuzzywuzzy import fuzz
from arduino_control import open_boom_gate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = "f5d66bddd230224ac9daeab7f87fed45a8ee114508a4879ba4b94b7c5151ecc1"
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///number_plates.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# If Tesseract is not in your PATH, include the Tesseract executable path
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
API_URL = "https://detect.roboflow.com"
API_KEY = "eBZoRrORo1oEJBm2hMNR"
MODEL_ID = "object-detection-bounding-box-js5eg/3"

db = SQLAlchemy(app)
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'admin' or 'security'

class BoomGateRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_text = db.Column(db.String(80), nullable=False)
    user_name = db.Column(db.String(80))
    user_id = db.Column(db.String(80))
    first_name = db.Column(db.String(80))
    surname = db.Column(db.String(80))
    company_name = db.Column(db.String(80))
    phone_number = db.Column(db.String(20))
    car_model = db.Column(db.String(80))
    timestamp = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f"<BoomGateRecord {self.plate_text} at {self.timestamp}>"

class LogEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_text = db.Column(db.String(80), nullable=False)
    user_name = db.Column(db.String(80), nullable=True)
    user_id = db.Column(db.String(80), nullable=True)
    first_name = db.Column(db.String(80), nullable=True)
    surname = db.Column(db.String(80), nullable=True)
    company_name = db.Column(db.String(80), nullable=True)
    timestamp = db.Column(db.DateTime, nullable=False)

class NumberPlate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate_text = db.Column(db.String(80), nullable=False, unique=True)
    user_name = db.Column(db.String(80), nullable=False)
    user_id = db.Column(db.String(80), nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    surname = db.Column(db.String(80), nullable=False)
    company_name = db.Column(db.String(80), nullable=False, default="Midlands State University")
    phone_number = db.Column(db.String(20), nullable=False)
    car_model = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f"<NumberPlate {self.plate_text}>"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def normalize_text(text):
    return re.sub(r'\W+', '', text).upper()

def perform_ocr(image_path, predictions):
    image = Image.open(image_path).convert('L')  # Convert to grayscale
    text_results = []
    for pred in predictions:
        x_min = max(pred['x'] - pred['width'] / 2, 0)
        y_min = max(pred['y'] - pred['height'] / 2, 0)
        x_max = min(pred['x'] + pred['width'] / 2, image.width)
        y_max = min(pred['y'] + pred['height'] / 2, image.height)
        
        box = (x_min, y_min, x_max, y_max)
        cropped_image = image.crop(box)
        
        text = pytesseract.image_to_string(cropped_image, config='--psm 6')
        normalized_text = normalize_text(text)
        text_results.append({
            "detection_id": pred['detection_id'],
            "text": normalized_text
        })
    return text_results

def check_plate_in_db(plate_text):
    normalized_plate_text = normalize_text(plate_text)
    plate = NumberPlate.query.filter_by(plate_text=normalized_plate_text).first()
    return plate

@app.route('/infer_auto', methods=['POST'])
def infer_auto():
    if 'image' in request.json:
        image_data = request.json['image']
        image_data = image_data.replace('data:image/jpeg;base64,', '')
        image_data = base64.b64decode(image_data)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'webcam_image_auto.jpg')
        with open(filepath, 'wb') as f:
            f.write(image_data)
        try:
            with open(filepath, 'rb') as image_file:
                image_data = image_file.read()
            response = requests.post(
                f"{API_URL}/{MODEL_ID}?api_key={API_KEY}",
                files={"file": image_data}
            )
            result = response.json()
            if 'predictions' in result:
                text_results = perform_ocr(filepath, result['predictions'])
                for text_result in text_results:
                    plate_text = text_result['text'].strip()
                    match = check_plate_in_db(plate_text)
                    timestamp = datetime.now()
                    log_entry = LogEntry(plate_text=plate_text, timestamp=timestamp)
                    if match:
                        log_entry.user_name = match.user_name
                        log_entry.user_id = match.user_id
                        log_entry.first_name = match.first_name
                        log_entry.surname = match.surname
                        log_entry.company_name = match.company_name
                        db.session.add(log_entry)
                        db.session.commit()
                        open_boom_gate()
                        return jsonify({
                            "match_found": True,
                            "plate_text": plate_text,
                            "user_name": match.user_name,
                            "user_id": match.user_id,
                            "first_name": match.first_name,
                            "surname": match.surname,
                            "company_name": match.company_name
                        }), 200
                    else:
                        db.session.add(log_entry)
                        db.session.commit()
                        return jsonify({"match_found": False}), 200
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "No valid input provided"}), 400


@app.route('/infer', methods=['POST'])
def infer():
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            try:
                with open(filepath, 'rb') as image_file:
                    image_data = image_file.read()
                response = requests.post(
                    f"{API_URL}/{MODEL_ID}?api_key={API_KEY}",
                    files={"file": image_data}
                )
                result = response.json()
                if 'predictions' in result:
                    text_results = perform_ocr(filepath, result['predictions'])
                    for text_result in text_results:
                        plate_text = text_result['text'].strip()
                        match = check_plate_in_db(plate_text)
                        if match:
                            print(f"Match found in database: {match}")
                            open_boom_gate()  # Open the boom gate
                            # Log the record
                            new_record = BoomGateRecord(
                                plate_text=match.plate_text,
                                user_name=match.user_name,
                                user_id=match.user_id,
                                first_name=match.first_name,
                                surname=match.surname,
                                company_name=match.company_name,
                                phone_number=match.phone_number,
                                car_model=match.car_model,
                                timestamp=datetime.utcnow()
                            )
                            db.session.add(new_record)
                            db.session.commit()
                            return render_template(
                                'result.html', 
                                plate_text=match.plate_text,  # Use plate text from the database
                                user_name=match.user_name,
                                user_id=match.user_id,
                                first_name=match.first_name,
                                surname=match.surname,
                                company_name=match.company_name,
                                phone_number=match.phone_number,
                                car_model=match.car_model,
                                match=True
                            )
                        else:
                            # Log number plate not found
                            new_record = BoomGateRecord(
                                plate_text=plate_text,
                                timestamp=datetime.utcnow()
                            )
                            db.session.add(new_record)
                            db.session.commit()
                            return render_template('result.html', plate_text=plate_text, match=False)
                return jsonify(result), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        else:
            return jsonify({"error": "File type not allowed"}), 400
    elif 'image' in request.form:
        image_data = request.form['image']
        image_data = image_data.replace('data:image/png;base64,', '')
        image_data = base64.b64decode(image_data)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'webcam_image.png')
        with open(filepath, 'wb') as f:
            f.write(image_data)
        try:
            with open(filepath, 'rb') as image_file:
                image_data = image_file.read()
            response = requests.post(
                f"{API_URL}/{MODEL_ID}?api_key={API_KEY}",
                files={"file": image_data}
            )
            result = response.json()
            if 'predictions' in result:
                text_results = perform_ocr(filepath, result['predictions'])
                for text_result in text_results:
                    plate_text = text_result['text'].strip()
                    match = check_plate_in_db(plate_text)
                    if match:
                        print(f"Match found in database: {match}")
                        open_boom_gate()  # Open the boom gate
                        # Log the record
                        new_record = BoomGateRecord(
                            plate_text=match.plate_text,
                            user_name=match.user_name,
                            user_id=match.user_id,
                            first_name=match.first_name,
                            surname=match.surname,
                            company_name=match.company_name,
                            phone_number=match.phone_number,
                            car_model=match.car_model,
                            timestamp=datetime.now()
                        )
                        db.session.add(new_record)
                        db.session.commit()
                        return render_template(
                            'result.html', 
                            plate_text=match.plate_text,  # Use plate text from the database
                            user_name=match.user_name,
                            user_id=match.user_id,
                            first_name=match.first_name,
                            surname=match.surname,
                            company_name=match.company_name,
                            phone_number=match.phone_number,
                            car_model=match.car_model,
                            match=True
                        )
                    else:
                        # Log number plate not found
                        new_record = BoomGateRecord(
                            plate_text=plate_text,
                            timestamp=datetime.now()
                        )
                        db.session.add(new_record)
                        db.session.commit()
                        return render_template('result.html', plate_text=plate_text, match=False)
            return jsonify(result), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "No valid input provided"}), 400

@app.route('/add_plate', methods=['POST'])
def add_plate():
    plate_text = request.json.get('plate_text', '').strip()
    user_name = request.json.get('user_name', '').strip()
    user_id = request.json.get('user_id', '').strip()
    first_name = request.json.get('first_name', '').strip()
    surname = request.json.get('surname', '').strip()
    phone_number = request.json.get('phone_number', '').strip()
    car_model = request.json.get('car_model', '').strip()
    company_name = "Midlands State University"  # Fixed value

    if not all([plate_text, user_name, user_id, first_name, surname, company_name, phone_number, car_model]):
        return jsonify({"error": "All fields are required"}), 400

    if check_plate_in_db(plate_text):
        return jsonify({"error": "Number plate already exists"}), 400

    new_plate = NumberPlate(
        plate_text=normalize_text(plate_text),
        user_name=user_name,
        user_id=user_id,
        first_name=first_name,
        surname=surname,
        company_name=company_name,
        phone_number=phone_number,
        car_model=car_model
    )
    db.session.add(new_plate)
    db.session.commit()
    return jsonify({"message": f"Number plate '{plate_text}' added to the database."}), 200

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    if request.method == 'POST':
        date_str = request.form.get('date')
        if date_str:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            records = BoomGateRecord.query.filter(
                db.func.date(BoomGateRecord.timestamp) == date_obj.date()
            ).all()
        else:
            records = BoomGateRecord.query.all()
    else:
        records = BoomGateRecord.query.all()
    return render_template('reports.html', records=records)

@app.route('/user_details')
def user_details():
    return render_template('user_details.html')


@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        new_user = User(username=username, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_user.html')

# Function to create default users
def create_default_users():
    if not User.query.filter_by(username='admin').first():
        hashed_password = generate_password_hash('admin123', method='pbkdf2:sha256', salt_length=8)
        new_user = User(username='admin', password=hashed_password, role='admin')
        db.session.add(new_user)
        db.session.commit()
    if not User.query.filter_by(username='guard').first():
        hashed_password = generate_password_hash('guard123', method='pbkdf2:sha256', salt_length=8)
        new_user = User(username='guard', password=hashed_password, role='security')
        db.session.add(new_user)
        db.session.commit()

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    with app.app_context():
        db.create_all()
        create_default_users()  # Create default users
    app.run(debug=True)