"""
Database initialization using SQLAlchemy 
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import bcrypt

DATABASE_PATH = 'sqlite:///database.db'
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    videos = relationship('Video', back_populates='user')
    api_keys = relationship('APIKey', back_populates='user')

class Video(Base):
    __tablename__ = 'videos'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    duration = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship('User', back_populates='videos')

class APIKey(Base):
    __tablename__ = 'api_keys'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    
    user = relationship('User', back_populates='api_keys')

class SearchJob(Base):
    __tablename__ = 'search_jobs'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    query = Column(String(500), nullable=False)
    status = Column(String(20), default='queued')
    results = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

def init_database():
    """Initialize database with demo data"""
    engine = create_engine(DATABASE_PATH)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Check if demo user exists
    existing_user = session.query(User).filter_by(email='demo@example.com').first()
    if existing_user:
        print("Demo user already exists!")
        session.close()
        return
    
    # Create demo user
    password = 'demo123'
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    demo_user = User(
        email='demo@example.com',
        name='Demo User',
        password_hash=password_hash
    )
    session.add(demo_user)
    session.flush()
    
    # Add sample videos
    videos = [
        Video(user_id=demo_user.id, title='Python Basics', description='Learn Python', duration=600),
        Video(user_id=demo_user.id, title='React Tutorial', description='Build web apps', duration=1200),
        Video(user_id=demo_user.id, title='Docker Guide', description='Containers 101', duration=900),
    ]
    
    for video in videos:
        session.add(video)
    
    session.commit()
    print("✅ Database initialized!")
    print("\nDemo credentials:")
    print("Email: demo@example.com")
    print("Password: demo123")
    session.close()

if __name__ == '__main__':
    init_database()