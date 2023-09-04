from flask import Flask, render_template, flash, redirect, url_for, jsonify, request, session
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, flash, redirect, url_for, send_file
from flask_mail import Mail, Message
import os
import secrets
import hashlib
from flask_uploads import UploadSet, configure_uploads, TEXT, DOCUMENTS, DATA

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a strong secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db' 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.example.com'  # Replace with your email server's SMTP details
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@example.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'
app.config['UPLOADS_DEFAULT_DEST'] = 'uploads' 
app.config['UPLOADED_TEXT_DEST'] = 'uploads'
app.config['UPLOADED_DOCUMENTS_DEST'] = 'uploads'
app.config['UPLOADED_DATA_DEST'] = 'uploads'

db = SQLAlchemy(app)
mail = Mail(app)
text_files = UploadSet('text', TEXT)
document_files = UploadSet('document', DOCUMENTS)
data_files = UploadSet('data', DATA)

configure_uploads(app, (text_files, document_files, data_files))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(120), unique=True, nullable=False)


def generate_verification_token():
    return secrets.token_hex(16)

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/ops_user', methods = ['GET','POST'])
def oprational_user():
    return render_template('ops_user.html')

@app.route('/client_user')
def client_user():
    return render_template('client_user.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        # Check if the email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists. Please use a different email or log in.', 'danger')
        else:
            # Generate a verification token and create a new user
            verification_token = generate_verification_token()
            new_user = User(username=username, email=email, password=password, verification_token=verification_token)
            db.session.add(new_user)
            db.session.commit()
            
            # Send a verification email
            send_verification_email(email, verification_token)
            
            flash('A verification email has been sent to your email address. Please verify your account.', 'success')
            return redirect(url_for('login'))

    return render_template('signup.html')

# Function to send a verification email
def send_verification_email(email, token):
    msg = Message('Email Verification', sender='your_email@example.com', recipients=[email])
    msg.body = f"Click the following link to verify your email: {url_for('verify_email', token=token, _external=True)}"
    mail.send(msg)

@app.route('/verify_email/<token>')
def verify_email(token):
    user = User.query.filter_by(verification_token=token).first()
    if user:
        user.verified = True
        user.verification_token = None
        db.session.commit()
        flash('Email verified successfully. You can now log in.', 'success')
    else:
        flash('Invalid verification token. Please check your email or sign up again.', 'danger')
    
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.password == password and user.verified:
            session['user_id'] = user.id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Please check your email and password or verify your email if you haven\'t already.', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)
        if user:
            return f'Welcome, {user.username}! This is your dashboard.'
    
    flash('Please log in to access your dashboard.', 'danger')
    return redirect(url_for('login'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST' and 'file' in request.files:
        file = request.files['file']

        if file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOADS_DEFAULT_DEST'], filename))
            flash('File uploaded successfully!', 'success')
        else:
            flash('No file selected.', 'danger')

    return render_template('upload.html')

@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_file(os.path.join(app.config['UPLOADS_DEFAULT_DEST'], filename), as_attachment=True)
    except FileNotFoundError:
        flash('File not found.', 'danger')
        return redirect(url_for('upload_file'))

@app.route('/list_files')
def list_files():
    uploaded_files = os.listdir(app.config['UPLOADS_DEFAULT_DEST'])
    return render_template('list_files.html', files=uploaded_files)



if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)