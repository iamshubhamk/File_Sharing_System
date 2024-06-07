from flask import Flask, request, redirect, url_for, render_template, session, send_file, flash
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import os
from bson import ObjectId

app = Flask(__name__)
app.secret_key = os.urandom(24)

app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_PATH'] = 16 * 1024 * 1024  # 16 MB limit

client = MongoClient('mongodb://localhost:27017/')
db = client['file_sharing']
users_collection = db['users']
files_collection = db['files']

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']  # 'server_side_user' or 'client_user'
        
        if users_collection.find_one({'username': username}):
            flash('Username already exists')
            return redirect(url_for('signup'))
        
        hashed_password = generate_password_hash(password)
        users_collection.insert_one({'username': username, 'password': hashed_password, 'role': role})
        flash('Signup successful, please login')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = users_collection.find_one({'username': username})
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    files = files_collection.find()
    return render_template('dashboard.html', username=session['username'], role=session['role'], files=files)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_id = files_collection.insert_one({
                'username': session['username'],
                'filename': filename,
                'file_size': len(file.read()),  # Store file size if needed
                'content_type': file.content_type  # Store content type if needed
            }).inserted_id
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))  # Save file to upload folder
            flash('File uploaded successfully')
        else:
            flash('Invalid file format')
    return redirect(url_for('dashboard'))

@app.route('/download/<file_id>')
def download_file(file_id):
    try:
        file_object = files_collection.find_one({'_id': ObjectId(file_id)})
        if file_object:
            file_path = file_object['file_path']
            return send_file(file_path, as_attachment=True)
        else:
            flash('File not found')
            return redirect(url_for('dashboard'))
    except Exception as e:
        flash(f'Error: {str(e)}')
        return redirect(url_for('dashboard'))

@app.route('/delete/<file_id>', methods=['POST'])
def delete_file(file_id):
    if 'username' not in session:
        return redirect(url_for('login'))
    
    file = files_collection.find_one({'_id': ObjectId(file_id)})
    if file:
        if file['username'] == session['username']:
            # Delete file from MongoDB and optionally from file system
            files_collection.delete_one({'_id': ObjectId(file_id)})
            flash('File deleted successfully')
            # Optionally delete from file system
            # os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file['filename']))
        else:
            flash('Unauthorized to delete this file')
    else:
        flash('File not found')
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))


if __name__=='__main__':
    app.run(debug=True)