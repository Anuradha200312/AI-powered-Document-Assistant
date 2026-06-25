import bcrypt
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from core.models import User

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a plain password matches the hashed password."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

def register_user(db: Session, username: str, email: str, password: str):
    """Register a new user in the database."""
    hashed_password = hash_password(password)
    new_user = User(
        username=username,
        email=email,
        password_hash=hashed_password
    )
    db.add(new_user)
    try:
        db.commit()
        db.refresh(new_user)
        return {"success": True, "user": new_user}
    except IntegrityError:
        db.rollback()
        return {"success": False, "error": "Username or email already exists."}

def authenticate_user(db: Session, username: str, password: str):
    """Authenticate a user by checking the username and password."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return {"success": False, "error": "Invalid username or password."}
    if not verify_password(password, user.password_hash):
        return {"success": False, "error": "Invalid username or password."}
    return {"success": True, "user": user}
