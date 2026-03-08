from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import time
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bus-tracking-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active buses and their locations
active_buses = {}
bus_routes = {
    'BUS001': 'Bhavani - Surya Engineering College',
    'BUS002': 'Erode - Surya Engineering College',
    'BUS003': 'Thiruppur - Surya Engineering College'
}

@app.route('/')
def index():
    return render_template('student.html')

@app.route('/driver')
def driver():
    return render_template('driver.html')

@app.route('/student')
def student():
    return render_template('student.html')

@socketio.on('driver_connect')
def handle_driver_connect(data):
    """Handle driver connection with bus ID"""
    bus_id = data['bus_id']
    bus_name = data.get('bus_name', '')
    route = bus_routes.get(bus_id, 'Unknown Route')
    
    # Store driver info
    active_buses[bus_id] = {
        'bus_id': bus_id,
        'bus_name': bus_name,
        'route': route,
        'connected': True,
        'last_update': datetime.now().strftime('%H:%M:%S'),
        'location': None
    }
    
    # Join a room specific to this bus
    join_room(bus_id)
    
    print(f'Driver connected: {bus_id}')
    emit('driver_connected', {'status': 'connected', 'bus_id': bus_id})

@socketio.on('driver_location')
def handle_driver_location(data):
    """Receive GPS location from driver"""
    bus_id = data['bus_id']
    latitude = data['latitude']
    longitude = data['longitude']
    speed = data.get('speed', 0)
    accuracy = data.get('accuracy', 0)
    
    # Update bus location
    if bus_id in active_buses:
        active_buses[bus_id].update({
            'location': {
                'lat': latitude,
                'lng': longitude,
                'speed': speed,
                'accuracy': accuracy,
                'timestamp': datetime.now().strftime('%H:%M:%S')
            },
            'last_update': datetime.now().strftime('%H:%M:%S')
        })
        
        # Broadcast location to all students tracking this bus
        emit('bus_location_update', {
            'bus_id': bus_id,
            'latitude': latitude,
            'longitude': longitude,
            'speed': speed,
            'accuracy': accuracy,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'route': active_buses[bus_id]['route']
        }, broadcast=True)
        
        print(f'Location update for {bus_id}: {latitude}, {longitude}')

@socketio.on('get_active_buses')
def handle_get_active_buses():
    """Send list of active buses to students"""
    active_list = []
    for bus_id, info in active_buses.items():
        if info['location']:
            active_list.append({
                'bus_id': bus_id,
                'bus_name': info.get('bus_name', ''),
                'route': info['route'],
                'last_update': info['last_update'],
                'location': info['location']
            })
    
    emit('active_buses_list', {'buses': active_list})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle driver disconnection"""
    # Find which bus disconnected
    for bus_id in list(active_buses.keys()):
        # Check if this socket was in the bus room
        # For simplicity, we'll implement a heartbeat later
        pass

# Add heartbeat to detect stale connections
@socketio.on('driver_heartbeat')
def handle_heartbeat(data):
    """Receive heartbeat from driver to keep connection alive"""
    bus_id = data['bus_id']
    if bus_id in active_buses:
        active_buses[bus_id]['last_heartbeat'] = time.time()
        emit('heartbeat_ack', {'status': 'ok'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)