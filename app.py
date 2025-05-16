from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
from database import db, Room, Message, init_db

# Initialize Flask app
app = Flask(__name__)

# Configure app
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database
init_db(app)

# REST API Routes
@app.route('/rooms', methods=['GET'])
def get_rooms():
    """Get all chat rooms"""
    rooms = Room.query.all()
    return jsonify([{'id': room.id, 'name': room.name} for room in rooms])

@app.route('/rooms', methods=['POST'])
def create_room():
    """Create a new chat room"""
    data = request.get_json()
    
    if not data or 'name' not in data:
        return jsonify({'error': 'Room name is required'}), 400
    
    # Check if room name already exists
    if Room.query.filter_by(name=data['name']).first():
        return jsonify({'error': 'Room name already exists'}), 409
    
    room = Room(name=data['name'])
    db.session.add(room)
    db.session.commit()
    
    return jsonify({'id': room.id, 'name': room.name}), 201

@app.route('/rooms/<int:room_id>/messages', methods=['GET'])
def get_messages(room_id):
    """Get messages for a specific room"""
    room = Room.query.get_or_404(room_id)
    messages = Message.query.filter_by(room_id=room_id).order_by(Message.timestamp.asc()).all()
    
    return jsonify([
        {
            'id': msg.id,
            'username': msg.username,
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat()
        } for msg in messages
    ])

# SocketIO Event Handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('connected', {'status': 'connected'})

@socketio.on('join')
def handle_join(data):
    """Handle room join event"""
    if not data or 'room' not in data or 'username' not in data:
        return
    
    room_id = data['room']
    username = data['username']
    
    # Join the room
    join_room(room_id)
    emit('user_joined', {'username': username}, room=room_id)

@socketio.on('message')
def handle_message(data):
    """Handle new message event"""
    if not data or 'room' not in data or 'username' not in data or 'content' not in data:
        return
    
    room_id = data['room']
    username = data['username']
    content = data['content']
    
    # Save message to database
    message = Message(room_id=room_id, username=username, content=content)
    db.session.add(message)
    db.session.commit()
    
    # Broadcast message to room
    emit('message', {
        'id': message.id,
        'username': username,
        'content': content,
        'timestamp': message.timestamp.isoformat()
    }, room=room_id)

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicator event"""
    if not data or 'room' not in data or 'username' not in data:
        return
    
    room_id = data['room']
    username = data['username']
    
    # Broadcast typing indicator to room
    emit('typing', {'username': username}, room=room_id)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)