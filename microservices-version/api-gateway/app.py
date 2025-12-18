"""
API Gateway
Routes requests and handles authentication
Backward compatible with original API
"""
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import jwt
import bcrypt
import uuid
import requests
import time
from functools import wraps

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI', 'sqlite:///../shared/database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_ALGORITHM'] = 'HS256'

db = SQLAlchemy(app)
CORS(app)

# Service URLs
SEARCH_SERVICE_URL = os.getenv('SEARCH_SERVICE_URL', 'http://localhost:5001')

api_requests_log = []

# MODELS 

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    videos = db.relationship('Video', backref='user', lazy=True)
    api_keys = db.relationship('APIKey', backref='user', lazy=True)

class Video(db.Model):
    __tablename__ = 'videos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class APIKey(db.Model):
    __tablename__ = 'api_keys'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    key_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)

class SearchJob(db.Model):
    __tablename__ = 'search_jobs'
    
    id = db.Column(db.String(36), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    query = db.Column(db.String(500), nullable=False)
    status = db.Column(db.String(20), default='queued')
    results = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)