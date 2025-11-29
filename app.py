import os
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from config import Config
import json

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database Models (بدون تغییر)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email_id = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    message_type = db.Column(db.String(20), default='text')
    content = db.Column(db.Text, nullable=False)
    file_path = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    group_id = db.Column(db.String(50), unique=True, nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions (بدون تغییر)
def generate_unique_username(name):
    base_username = name.lower().replace(' ', '')
    username = base_username
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1
    return username

# Routes (همان routes اما بدون SocketIO)
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.username == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        password = request.form['password']
        
        if User.query.filter_by(phone=phone).first():
            flash('شماره تلفن قبلاً ثبت شده است', 'error')
            return render_template('register.html')
        
        username = generate_unique_username(name)
        email_id = f"{username}@Mailgram.com"
        
        new_user = User(
            name=name,
            phone=phone,
            password=generate_password_hash(password),
            username=username,
            email_id=email_id
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('ثبت‌نام با موفقیت انجام شد. اکنون می‌توانید وارد شوید.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']
        
        # Check for admin login
        if phone == 'admin' and password == app.config['ADMIN_PASSWORD']:
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    name='Administrator',
                    phone='admin',
                    password=generate_password_hash(app.config['ADMIN_PASSWORD']),
                    username='admin',
                    email_id='admin@Mailgram.com'
                )
                db.session.add(admin_user)
                db.session.commit()
            login_user(admin_user)
            return redirect(url_for('admin_dashboard'))
        
        user = User.query.filter_by(phone=phone, is_active=True).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            user.last_seen = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('dashboard'))
        else:
            flash('شماره تلفن یا رمز عبور اشتباه است', 'error')
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.username == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    contacts = User.query.filter(User.id != current_user.id, User.is_active == True).all()
    user_groups = Group.query.join(GroupMember).filter(
        GroupMember.user_id == current_user.id,
        GroupMember.status == 'approved'
    ).all()
    
    return render_template('dashboard.html', 
                         user=current_user, 
                         contacts=contacts, 
                         groups=user_groups)

# سایر routes بدون تغییر باقی می‌مانند...
# [بقیه routes را از فایل اصلی کپی کنید]

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
