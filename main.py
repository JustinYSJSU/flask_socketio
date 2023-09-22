from flask import Flask, request, render_template, redirect, url_for, session
from flask_socketio import SocketIO, join_room, leave_room, send
import random
import string

app = Flask(__name__)
app.config["SECRET_KEY"] = "supersecretkey"
socketio = SocketIO(app)

# A mock database to persist data
#holds data for each created room (members and messages)
rooms = {}

#generates a random room code
def generate_room_code(length: int, existing_codes: list[str]) -> str:
    while True:
        code_chars = [random.choice(string.ascii_letters) for _ in range(length)]
        code = ''.join(code_chars)
        if code not in existing_codes:
            return code


"""POST -> get information from user submitted form. form from home.html

name -> user entered name
create -> creating a new room
code -> entered code to join a room
join -> joining an existing room
"""
@app.route('/', methods=["GET", "POST"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get('name')
        create = request.form.get('create', False)
        code = request.form.get('code')
        join = request.form.get('join', False)
        #no name entered
        if not name:
            return render_template('home.html', error="Name is required", code=code)
        #creating a room, generate a code and add to rooms
        if create != False:
            room_code = generate_room_code(6, list(rooms.keys()))
            new_room = {
                'members': 0,
                'messages': []
            }
            rooms[room_code] = new_room

        #joining a room, make sure user enters a valid code
        if join != False:
            # no code
            if not code:
                return render_template('home.html', error="Please enter a room code to enter a chat room", name=name)
            # invalid code
            if code not in rooms:
                return render_template('home.html', error="Room code invalid", name=name)
            room_code = code

        session['room'] = room_code
        session['name'] = name
        return redirect(url_for('room'))
    else:
        return render_template('home.html')

@app.route('/room')
def room():
    #session.get() will parse values from the current HTTP request 
    #here it will get the users entered name and the want they want to go to
    room = session.get('room')
    name = session.get('name')
    #no name or wrong room
    if name is None or room is None or room not in rooms:
        return redirect(url_for('home'))
    #user is in the room, start tracking the messages in the "database"
    messages = rooms[room]['messages']
    return render_template('room.html', room=room, user=name, messages=messages)

"""
handles when user connects to the chat room 
handles "connect" event from client side

"""
@socketio.on('connect')
def handle_connect():
    name = session.get('name')
    room = session.get('room')
    if name is None or room is None:
        return
    if room not in rooms:
        leave_room(room)
    join_room(room)
    send({
        "sender": "",
        "message": f"{name} has entered the chat"
    }, to=room)
    rooms[room]["members"] += 1

"""
handles "message" event from the javascript socket io (client side)
"""
@socketio.on('message')
def handle_message(payload):
    room = session.get('room')
    name = session.get('name')
    if room not in rooms:
        return
    message = {
        "sender": name,
        "message": payload["message"]
    }

    #send to the correct room, and add to "database"
    send(message, to=room)
    rooms[room]["messages"].append(message)

"""
handles disconnect event from client side (user leaves chat)
"""
@socketio.on('disconnect')
def handle_disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)
    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
        send({
        "message": f"{name} has left the chat",
        "sender": ""
    }, to=room)


if __name__ == "__main__":
    socketio.run(app, debug=True) #run with socket, not flask