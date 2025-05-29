from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
import os
import json
from myflaskapp.session import Session

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Configure CORS with allowed origins
ALLOWED_ORIGINS = [
    'https://icy-beach-0c1ee010f.6.azurestaticapps.net', 
    'http://localhost:3000'  
]
# Enable CORS for specific origins
CORS(app, origins=ALLOWED_ORIGINS)  

# local development
# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///sessions.db"


# Use environment variable for database URL
# url has to be in the format: postgresql+psycopg2://username:password@host/database_name
print(">> DATABASE_URL from env:", os.getenv("DATABASE_URL"))
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
db = SQLAlchemy(app)


class UserModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    sessions = db.relationship(
        "SessionModel", secondary="user_sessions", backref="users"
    )

class SessionModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey("user_model.id"), nullable=False)
    name = db.Column(db.String(100), default="Untitled")
    summary = db.Column(db.Text, default="")
    transcript = db.Column(db.Text, default="")
    chats = db.relationship("ChatModel", backref="session", cascade="all, delete-orphan")
    
    @property
    def messages(self):
        # For backward compatibility, return messages from the default chat
        default_chat = ChatModel.query.filter_by(session_id=self.id, name="default").first()
        if default_chat:
            return default_chat.messages
        return []
    
    @messages.setter
    def messages(self, value):
        # For backward compatibility, set messages on the default chat
        default_chat = ChatModel.query.filter_by(session_id=self.id, name="default").first()
        if not default_chat:
            default_chat = ChatModel(session_id=self.id, name="default")
            db.session.add(default_chat)
        default_chat.messages = value


class ChatModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("session_model.id"), nullable=False)
    name = db.Column(db.String(100), default="default")
    messages = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


user_sessions = db.Table(
    "user_sessions",
    db.Column("user_id", db.Integer, db.ForeignKey("user_model.id"), primary_key=True),
    db.Column(
        "session_id", db.Integer, db.ForeignKey("session_model.id"), primary_key=True
    ),
)


# requires username, returns user_id
@app.route("/login", methods=["POST"])
def login():
    try:
        print(">> /login hit")
        user_data = request.get_json(force=True, silent=True)
        print(">> Received payload:", user_data)

        if not user_data:
            return jsonify({"error": "Missing request body"}), 400

        username = user_data.get("username")
        if not username:
            return jsonify({"error": "Missing username"}), 400

        existing_user = UserModel.query.filter_by(username=username).first()
        if existing_user:
            print(">> Existing user found:", existing_user.id)
            return jsonify({
                "message": "User already exists",
                "user_id": existing_user.id
            }), 200

        new_user = UserModel(username=username)
        db.session.add(new_user)
        db.session.commit()

        print(">> New user created:", new_user.id)

        return jsonify({
            "message": "User created",
            "user_id": new_user.id
        }), 201

    except Exception as e:
        print("!!! Error in /login route:", str(e))
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


# requires user_id
@app.route("/delete_user/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    user = db.session.get(UserModel, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "User deleted"}), 200


# requires user_id and session_id
@app.route("/unsubscribe/<int:user_id>/<int:session_id>", methods=["DELETE"])
def unsubscribe(user_id, session_id):
    user = db.session.get(UserModel, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    session = db.session.get(SessionModel, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    user.sessions.remove(session)
    db.session.commit()

    return jsonify({"message": "Unsubscribed from session"}), 200


# requires user_id and session_id
@app.route("/subscribe/<int:user_id>/<int:session_id>", methods=["POST"])
def subscribe(user_id, session_id):
    user = db.session.get(UserModel, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    session = db.session.get(SessionModel, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    if session not in user.sessions:
        user.sessions.append(session)
    
    db.session.commit()

    return jsonify({"message": "Subscribed to session"}), 200


# requires user_id, creates session_id, returns summary and metadata
@app.route("/summarize/<int:user_id>", methods=["POST"])
def summarize(user_id):
    if "transcript" not in request.files or "recording" not in request.files:
        return jsonify({"error": "Missing transcript or recording file"}), 400

    session = Session()
    
    # get case number and interviewee name, set session name
    case_number = request.form.get("case_number")
    interviewee_name = request.form.get("interviewee_name")
    if not case_number or not interviewee_name:
        return jsonify({"error": "Missing case number or interviewee name"}), 400
    
    session.name = f"{case_number}: {interviewee_name}"
    
    # get transcript and recording files
    transcript_file = request.files["transcript"]
    recording_file = request.files["recording"]

    transcript_path = secure_filename(transcript_file.filename)
    recording_path = secure_filename(recording_file.filename)

    transcript_file.save(transcript_path)
    recording_file.save(recording_path)
    
    # Handle additional context files
    additional_context_paths = []
    if 'additional_context' in request.files:
        additional_context_files = request.files.getlist('additional_context')
        for context_file in additional_context_files:
            context_path = secure_filename(context_file.filename)
            context_file.save(context_path)
            additional_context_paths.append(context_path)

    def generate():
        try:
            for chunk in session.summarize(transcript_path, recording_path, additional_context_paths):
                yield chunk
        finally:
            os.remove(transcript_path)
            os.remove(recording_path)
            # Clean up additional context files
            for context_path in additional_context_paths:
                if os.path.exists(context_path):
                    os.remove(context_path)
            new_session = SessionModel(
                creator_id=user_id,
                name=session.name,
                summary=session.summary,
                transcript=session.transcript,
            )
            db.session.add(new_session)
            db.session.flush()  # Get the session ID before committing
            
            # Create a default chat for the session
            default_chat = ChatModel(
                session_id=new_session.id,
                name="default",
                messages=session.messages
            )
            db.session.add(default_chat)

            # Associate the session with the user who created it
            user = db.session.get(UserModel, user_id)
            if user and new_session not in user.sessions:
                user.sessions.append(new_session)

            db.session.commit()
            yield "SESSION_META::" + json.dumps({
                "id": new_session.id,
                "messages": session.messages,
                "chat_id": default_chat.id
            })

    return Response(stream_with_context(generate()), content_type="text/markdown")

@app.route("/revise/<int:session_id>", methods=["POST"])
def revise(session_id):
    data = request.json
    revision = data.get("revision")
    if not revision:
        return jsonify({"error": "Missing revision request"}), 400
    
    record = db.session.get(SessionModel, session_id)
    if not record:
        return jsonify({"error": "Session not found"}), 404
    
    session = Session(
        name=record.name,
        summary=record.summary,
        transcript=record.transcript,
        messages=list(record.messages),
    )
    
    def generate():
        try:
            yield " "
            for chunk in session.revise(revision):
                yield chunk
        finally:
            record.summary = session.summary
            db.session.commit()
            
    return Response(stream_with_context(generate()), content_type="text/markdown")


# requires session_id, does not require user_id, returns chat response
@app.route("/chat/<int:session_id>", methods=["POST"])
def chat(session_id):
    data = request.json
    prompt = data.get("message")
    chat_id = data.get("chat_id")
    
    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400

    record = db.session.get(SessionModel, session_id)
    if not record:
        return jsonify({"error": "Session not found"}), 404
        
    # Get the specified chat or use the default chat
    if chat_id:
        chat_record = db.session.get(ChatModel, chat_id)
        if not chat_record or chat_record.session_id != session_id:
            return jsonify({"error": "Chat not found or doesn't belong to this session"}), 404
    else:
        # Use default chat or create it if it doesn't exist
        chat_record = ChatModel.query.filter_by(session_id=session_id, name="default").first()
        if not chat_record:
            chat_record = ChatModel(session_id=session_id, name="default")
            db.session.add(chat_record)
            db.session.commit()

    session = Session(
        name=record.name,
        summary=record.summary,
        transcript=record.transcript,
        messages=list(chat_record.messages),
    )

    def generate():
        try:
            for chunk in session.prompt_chat(prompt):
                yield chunk
        finally:
            chat_record.messages = session.messages
            db.session.commit()

    return Response(stream_with_context(generate()), content_type="text/markdown")


# requires session_id, does not require user_id, returns session metadata
@app.route("/load_session/<int:session_id>", methods=["GET"])
def load_session(session_id):
    record = db.session.get(SessionModel, session_id)
    if not record:
        return jsonify({"error": "Session not found"}), 404

    chats = ChatModel.query.filter_by(session_id=session_id).all()
    chat_list = [{"id": chat.id, "name": chat.name} for chat in chats]
    
    # Get default chat messages for backward compatibility
    default_chat = ChatModel.query.filter_by(session_id=session_id, name="default").first()
    messages = default_chat.messages if default_chat else []

    return jsonify(
        {
            "message": "Session loaded",
            "session_id": session_id,
            "name": record.name,
            "summary": record.summary,
            "transcript": record.transcript,
            "messages": messages,
            "chats": chat_list
        }
    )


# requires user_id, does not require session_id, returns session names and ids for user
@app.route("/get_sessions/<int:user_id>", methods=["GET"])
def get_sessions(user_id):
    user = db.session.get(UserModel, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    session_list = [
        {"id": session.id, "name": session.name, "creator_id": session.creator_id} for session in user.sessions
    ]
    return jsonify(session_list)


@app.route("/get_all_sessions", methods=["GET"])
def get_all_sessions():
    sessions = SessionModel.query.all()
    session_list = [{"id": session.id, "name": session.name} for session in sessions]
    return jsonify(session_list)


# requires session_id, does not require user_id
@app.route("/delete_session/<int:session_id>", methods=["DELETE"])
def delete_session(session_id):
    session = db.session.get(SessionModel, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    db.session.delete(session)
    db.session.commit()
    return jsonify({"message": "Session deleted"}), 200


@app.route("/rename_session/<int:session_id>", methods=["PATCH"])
def rename_session(session_id):
    data = request.json
    new_name = data.get("name")
    if not new_name:
        return jsonify({"error": "Missing new name"}), 400
    
    session = db.session.get(SessionModel, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    session.name = new_name
    db.session.commit()
    return jsonify({"message": "Session renamed"}), 200


# Add new endpoints for managing chats
@app.route("/create_chat/<int:session_id>", methods=["POST"])
def create_chat(session_id):
    data = request.json
    chat_name = data.get("name", "New Chat")
    
    session = db.session.get(SessionModel, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    
    default_chat = ChatModel.query.filter_by(session_id=session_id, name="default").first()
    first_five_messages = default_chat.messages[:5] if default_chat else []
        
    new_chat = ChatModel(session_id=session_id, name=chat_name, messages=first_five_messages)
    db.session.add(new_chat)
    db.session.commit()
    
    return jsonify({
        "message": "Chat created",
        "chat_id": new_chat.id,
        "name": new_chat.name
    }), 201

@app.route("/get_chats/<int:session_id>", methods=["GET"])
def get_chats(session_id):
    session = db.session.get(SessionModel, session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
        
    chats = ChatModel.query.filter_by(session_id=session_id).all()
    chat_list = [{"id": chat.id, "name": chat.name} for chat in chats]
    
    return jsonify(chat_list)

@app.route("/rename_chat/<int:chat_id>", methods=["PATCH"])
def rename_chat(chat_id):
    data = request.json
    new_name = data.get("name")
    
    if not new_name:
        return jsonify({"error": "Missing new name"}), 400
    
    chat = db.session.get(ChatModel, chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    
    chat.name = new_name
    db.session.commit()
    
    return jsonify({"message": "Chat renamed"}), 200

@app.route("/delete_chat/<int:chat_id>", methods=["DELETE"])
def delete_chat(chat_id):
    chat = db.session.get(ChatModel, chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    
    db.session.delete(chat)
    db.session.commit()
    
    return jsonify({"message": "Chat deleted"}), 200

@app.route("/load_chat/<int:chat_id>", methods=["GET"])
def load_chat(chat_id):
    chat = db.session.get(ChatModel, chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    
    session = db.session.get(SessionModel, chat.session_id)
    
    return jsonify({
        "chat_id": chat.id,
        "name": chat.name,
        "session_id": chat.session_id,
        "session_name": session.name,
        "messages": chat.messages
    })

if __name__ == "__main__":
    with app.app_context():
        print("Creating tables...")
        db.create_all()
        print("Done")
    app.run(debug=True, host="0.0.0.0", port=8080)
