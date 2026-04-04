import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///dev.db")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Neon database shuts itself off if no traffic is recieved for a particular amount of time to save resources.This helps in keeping it connected.
    SQLALCHEMY_ENGINE_OPTIONS = { 
        "pool_pre_ping": True, 
        "pool_recycle": 300,
    }