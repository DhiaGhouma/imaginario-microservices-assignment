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