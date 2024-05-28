from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = '12345678'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat_app.db'
db = SQLAlchemy(app)
socketio = SocketIO(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(500), nullable=False)

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    messages = Message.query.all()
    logged_in = 'username' in session
    return render_template('index.html', messages=messages, logged_in=logged_in, username=session.get('username'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.get_json()
        existing_user = User.query.filter_by(username=data['username']).first()
        if existing_user:
            return jsonify({'success': False, 'message': '用户已存在！'})
        
        hashed_password = generate_password_hash(data['password'])
        new_user = User(username=data['username'], password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        session['username'] = new_user.username
        return jsonify({'success': True, 'message': '注册成功！'})
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()
        if user and check_password_hash(user.password, data['password']):
            session['username'] = user.username
            return jsonify({'success': True, 'message': '登录成功！'})
        return jsonify({'success': False, 'message': '用户名或密码错误！'})
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/chat', methods=['POST'])
def chat():
    if 'username' not in session:
        return jsonify({'success': False, 'message': '请先登录！'})

    data = request.get_json()
    new_message = Message(username=session['username'], message=data['message'])
    db.session.add(new_message)
    db.session.commit()
    socketio.emit('new_message', {'username': session['username'], 'message': data['message']})
    return jsonify({'success': True, 'username': session['username'], 'message': data['message']})

@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        emit('status', {'msg': f"{session['username']} 加入了聊天"}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if 'username' in session:
        emit('status', {'msg': f"{session['username']} 退出了聊天"}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
