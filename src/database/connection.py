# This file establishes and manages the connection pool to the NeonDB PostgreSQL database using SQLAlchemy.

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load all the environment variables from the .env file
load_dotenv()

# Load the NEON_DATABASE_URL environment variable from the .env file
DATABASE_URL = os.getenv("NEON_DATABASE_URL")


# Check if the NEON_DATABASE_URL is set or not in the .env file
if not DATABASE_URL:
    raise ValueError("NEON_DATABASE_URL environmet variable is not set.")

# Create the SQLAlchemy engine
# pool_pre_ping checks if the connection is alive before using it
engine = create_engine(DATABASE_URL, pool_pre_ping = True)

# Creates the configured Session class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind = engine)

# Create a base class for the declarative model
Base = declarative_base()

def get_db():
    """Dependency to get the database session for our FastAPI routes later"""
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()