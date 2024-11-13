from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from models import get_user_by_username, add_user, get_user_by_id, get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if add_user(username, password):
            flash('Signup successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Username already exists', 'danger')
    return render_template('signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login successful!', 'success')
            if user.is_admin:
                return redirect(url_for('auth.admin'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        return redirect(url_for('dashboard'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        for user_id in request.form.getlist('user_id'):
            can_upload_multiple = 1 if request.form.get(f'can_upload_multiple_{user_id}') else 0
            cursor.execute('UPDATE Users SET CanUploadMultiple = ? WHERE ID = ?', (can_upload_multiple, user_id))
        conn.commit()

    cursor.execute('SELECT * FROM Users WHERE isAdmin = 0')
    users = cursor.fetchall()
    conn.close()

    return render_template('admin.html', users=users)
