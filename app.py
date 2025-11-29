import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_socketio import SocketIO, join_room, leave_room, emit
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
socketio = SocketIO(app)  # Initialize SocketIO

# تنظیمات برای Fly.io
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///mailgram.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Add file upload configuration
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['ALLOWED_VIDEO_EXTENSIONS'] = {'mp4', 'avi', 'mov', 'mkv'}
app.config['ALLOWED_AUDIO_EXTENSIONS'] = {'mp3', 'wav', 'ogg', 'm4a'}
app.config['ALLOWED_DOCUMENT_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'txt'}
app.config['ADMIN_PASSWORD'] = os.environ.get('ADMIN_PASSWORD', 'admin123')

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
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
    
    # Relationships
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', backref='receiver', lazy='dynamic')
    created_groups = db.relationship('Group', backref='creator', lazy='dynamic')
    group_memberships = db.relationship('GroupMember', backref='user', lazy='dynamic')
    sent_reports = db.relationship('Report', foreign_keys='Report.reporter_id', backref='reporter', lazy='dynamic')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
    message_type = db.Column(db.String(20), default='text')  # text, image, video, audio, document
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
    
    # Relationships
    messages = db.relationship('Message', backref='group', lazy='dynamic')
    members = db.relationship('GroupMember', backref='group', lazy='dynamic')

class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=False)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, reviewed, resolved

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions
def allowed_file(filename, file_type):
    ALLOWED_EXTENSIONS = {
        'image': app.config['ALLOWED_IMAGE_EXTENSIONS'],
        'video': app.config['ALLOWED_VIDEO_EXTENSIONS'],
        'audio': app.config['ALLOWED_AUDIO_EXTENSIONS'],
        'document': app.config['ALLOWED_DOCUMENT_EXTENSIONS']
    }
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS.get(file_type, set())

def generate_unique_username(name):
    base_username = name.lower().replace(' ', '')
    username = base_username
    counter = 1
    while User.query.filter_by(username=username).first():
        username = f"{base_username}{counter}"
        counter += 1
    return username

# Routes
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
        
        # Check if phone already exists
        if User.query.filter_by(phone=phone).first():
            flash('شماره تلفن قبلاً ثبت شده است', 'error')
            return render_template('register.html')
        
        # Generate unique username and email ID
        username = generate_unique_username(name)
        email_id = f"{username}@Mailgram.com"
        
        # Create new user
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
        
        # Regular user login
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
    
    # Get user's contacts
    contacts = User.query.filter(User.id != current_user.id, User.is_active == True).all()
    
    # Get user's groups
    user_groups = Group.query.join(GroupMember).filter(
        GroupMember.user_id == current_user.id,
        GroupMember.status == 'approved'
    ).all()
    
    return render_template('dashboard.html', 
                         user=current_user, 
                         contacts=contacts, 
                         groups=user_groups)

@app.route('/chat/<int:user_id>')
@login_required
def chat(user_id):
    other_user = User.query.get_or_404(user_id)
    
    # Get chat history
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    
    return render_template('chat.html', other_user=other_user, messages=messages)

@app.route('/group/<string:group_id>')
@login_required
def group_chat(group_id):
    group = Group.query.filter_by(group_id=group_id).first_or_404()
    
    # Check if user is member of the group
    membership = GroupMember.query.filter_by(
        group_id=group.id, 
        user_id=current_user.id,
        status='approved'
    ).first()
    
    if not membership:
        flash('شما عضو این گروه نیستید', 'error')
        return redirect(url_for('dashboard'))
    
    # Get group messages
    messages = Message.query.filter_by(group_id=group.id).order_by(Message.timestamp.asc()).all()
    
    # Get group members
    members = User.query.join(GroupMember).filter(
        GroupMember.group_id == group.id,
        GroupMember.status == 'approved'
    ).all()
    
    return render_template('group.html', group=group, messages=messages, members=members)

@app.route('/create_group', methods=['GET', 'POST'])
@login_required
def create_group():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        
        # Generate unique group ID
        group_id = f"group_{uuid.uuid4().hex[:8]}"
        
        new_group = Group(
            name=name,
            group_id=group_id,
            creator_id=current_user.id,
            description=description
        )
        
        db.session.add(new_group)
        db.session.commit()
        
        # Add creator as admin member
        creator_member = GroupMember(
            group_id=new_group.id,
            user_id=current_user.id,
            status='approved',
            is_admin=True
        )
        db.session.add(creator_member)
        db.session.commit()
        
        flash('گروه با موفقیت ایجاد شد', 'success')
        return redirect(url_for('group_chat', group_id=group_id))
    
    return render_template('create_group.html')

@app.route('/join_group_request/<string:group_id>')
@login_required
def join_group_request(group_id):
    group = Group.query.filter_by(group_id=group_id).first_or_404()
    
    # Check if already member or has pending request
    existing_member = GroupMember.query.filter_by(
        group_id=group.id,
        user_id=current_user.id
    ).first()
    
    if not existing_member:
        new_request = GroupMember(
            group_id=group.id,
            user_id=current_user.id,
            status='pending'
        )
        db.session.add(new_request)
        db.session.commit()
        flash('درخواست عضویت شما ارسال شد', 'success')
    elif existing_member.status == 'pending':
        flash('درخواست عضویت شما در حال بررسی است', 'info')
    else:
        flash('شما قبلاً عضو این گروه هستید', 'info')
    
    return redirect(url_for('dashboard'))

@app.route('/manage_group_requests/<string:group_id>')
@login_required
def manage_group_requests(group_id):
    group = Group.query.filter_by(group_id=group_id).first_or_404()
    
    # Check if user is group admin
    if group.creator_id != current_user.id:
        flash('شما دسترسی لازم برای مدیریت این گروه را ندارید', 'error')
        return redirect(url_for('dashboard'))
    
    pending_requests = GroupMember.query.filter_by(
        group_id=group.id,
        status='pending'
    ).all()
    
    return render_template('manage_requests.html', group=group, requests=pending_requests)

@app.route('/handle_group_request/<int:request_id>/<string:action>')
@login_required
def handle_group_request(request_id, action):
    group_request = GroupMember.query.get_or_404(request_id)
    group = Group.query.get(group_request.group_id)
    
    if group.creator_id != current_user.id:
        flash('شما دسترسی لازم برای مدیریت این گروه را ندارید', 'error')
        return redirect(url_for('dashboard'))
    
    if action == 'approve':
        group_request.status = 'approved'
        flash('کاربر به گروه اضافه شد', 'success')
    elif action == 'reject':
        group_request.status = 'rejected'
        flash('درخواست عضویت رد شد', 'info')
    
    db.session.commit()
    return redirect(url_for('manage_group_requests', group_id=group.group_id))

@app.route('/add_contact/<string:email_id>')
@login_required
def add_contact(email_id):
    contact_user = User.query.filter_by(email_id=email_id, is_active=True).first()
    
    if not contact_user:
        flash('کاربری با این شناسه یافت نشد', 'error')
        return redirect(url_for('dashboard'))
    
    if contact_user.id == current_user.id:
        flash('نمی‌توانید خود را به مخاطبین اضافه کنید', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if already in contacts
    existing_contact = Contact.query.filter_by(
        user_id=current_user.id,
        contact_id=contact_user.id
    ).first()
    
    if not existing_contact:
        new_contact = Contact(
            user_id=current_user.id,
            contact_id=contact_user.id
        )
        db.session.add(new_contact)
        db.session.commit()
        flash('مخاطب با موفقیت اضافه شد', 'success')
    else:
        flash('این کاربر قبلاً به مخاطبین اضافه شده است', 'info')
    
    return redirect(url_for('dashboard'))

@app.route('/report_user/<int:user_id>', methods=['POST'])
@login_required
def report_user(user_id):
    reported_user = User.query.get_or_404(user_id)
    reason = request.form['reason']
    
    new_report = Report(
        reporter_id=current_user.id,
        reported_user_id=reported_user.id,
        reason=reason
    )
    
    db.session.add(new_report)
    db.session.commit()
    
    flash('گزارش با موفقیت ثبت شد', 'success')
    return redirect(url_for('dashboard'))

# Admin Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.username != 'admin':
        flash('دسترسی غیرمجاز', 'error')
        return redirect(url_for('dashboard'))
    
    stats = {
        'total_users': User.query.count(),
        'total_groups': Group.query.count(),
        'total_messages': Message.query.count(),
        'pending_reports': Report.query.filter_by(status='pending').count(),
        'active_users': User.query.filter_by(is_active=True).count()
    }
    
    return render_template('admin/dashboard.html', stats=stats)

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.username != 'admin':
        flash('دسترسی غیرمجاز', 'error')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/chats')
@login_required
def admin_chats():
    if current_user.username != 'admin':
        flash('دسترسی غیرمجاز', 'error')
        return redirect(url_for('dashboard'))
    
    messages = Message.query.all()
    return render_template('admin/chats.html', messages=messages)

@app.route('/admin/groups')
@login_required
def admin_groups():
    if current_user.username != 'admin':
        flash('دسترسی غیرمجاز', 'error')
        return redirect(url_for('dashboard'))
    
    groups = Group.query.all()
    return render_template('admin/groups.html', groups=groups)

@app.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.username != 'admin':
        flash('دسترسی غیرمجاز', 'error')
        return redirect(url_for('dashboard'))
    
    reports = Report.query.all()
    return render_template('admin/reports.html', reports=reports)

@app.route('/admin/toggle_user/<int:user_id>')
@login_required
def admin_toggle_user(user_id):
    if current_user.username != 'admin':
        flash('دسترسی غیرمجاز', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()
    
    status = "فعال" if user.is_active else "غیرفعال"
    flash(f'کاربر {status} شد', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/delete_user/<int:user_id>')
@login_required
def admin_delete_user(user_id):
    if current_user.username != 'admin':
        flash('دسترسی غیرمجاز', 'error')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    
    flash('کاربر حذف شد', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/handle_report/<int:report_id>/<string:action>')
@login_required
def admin_handle_report(report_id, action):
    if current_user.username != 'admin':
        flash('دسترسی غیرمجاز', 'error')
        return redirect(url_for('dashboard'))
    
    report = Report.query.get_or_404(report_id)
    
    if action == 'resolve':
        report.status = 'resolved'
        flash('گزارش حل شده标记 شد', 'success')
    elif action == 'review':
        report.status = 'reviewed'
        flash('گزارش بررسی شد', 'info')
    
    db.session.commit()
    return redirect(url_for('admin_reports'))

# Socket.IO Handlers
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        join_room(current_user.id)
        emit('user_status', {'user_id': current_user.id, 'status': 'online'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        leave_room(current_user.id)
        emit('user_status', {'user_id': current_user.id, 'status': 'offline'}, broadcast=True)

@socketio.on('private_message')
def handle_private_message(data):
    sender_id = current_user.id
    receiver_id = data['receiver_id']
    message_content = data['message']
    message_type = data.get('type', 'text')
    
    # Save message to database
    new_message = Message(
        sender_id=sender_id,
        receiver_id=receiver_id,
        message_type=message_type,
        content=message_content
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    # Emit to receiver
    emit('new_message', {
        'id': new_message.id,
        'sender_id': sender_id,
        'sender_name': current_user.name,
        'content': message_content,
        'timestamp': new_message.timestamp.isoformat(),
        'type': message_type
    }, room=receiver_id)
    
    # Emit back to sender for confirmation
    emit('message_sent', {
        'id': new_message.id,
        'timestamp': new_message.timestamp.isoformat()
    })

@socketio.on('group_message')
def handle_group_message(data):
    sender_id = current_user.id
    group_id = data['group_id']
    message_content = data['message']
    message_type = data.get('type', 'text')
    
    # Save message to database
    new_message = Message(
        sender_id=sender_id,
        group_id=group_id,
        message_type=message_type,
        content=message_content
    )
    
    db.session.add(new_message)
    db.session.commit()
    
    # Get group members
    group_members = GroupMember.query.filter_by(
        group_id=group_id,
        status='approved'
    ).all()
    
    # Emit to all group members
    for member in group_members:
        emit('new_group_message', {
            'id': new_message.id,
            'group_id': group_id,
            'sender_id': sender_id,
            'sender_name': current_user.name,
            'content': message_content,
            'timestamp': new_message.timestamp.isoformat(),
            'type': message_type
        }, room=member.user_id)

@socketio.on('typing')
def handle_typing(data):
    receiver_id = data.get('receiver_id')
    group_id = data.get('group_id')
    is_typing = data['typing']
    
    if receiver_id:
        emit('user_typing', {
            'user_id': current_user.id,
            'user_name': current_user.name,
            'typing': is_typing
        }, room=receiver_id)
    elif group_id:
        group_members = GroupMember.query.filter_by(
            group_id=group_id,
            status='approved'
        ).all()
        for member in group_members:
            if member.user_id != current_user.id:
                emit('group_typing', {
                    'group_id': group_id,
                    'user_id': current_user.id,
                    'user_name': current_user.name,
                    'typing': is_typing
                }, room=member.user_id)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('با موفقیت خارج شدید', 'success')
    return redirect(url_for('login'))

# Create database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

