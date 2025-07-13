#!/usr/bin/env python3
"""
Database Migration Script

Adds api_football_id column to teams table for API-Football integration
"""

import os
import sys
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app
from db import db


def migrate_database():
    """Create database tables and add api_football_id column if needed"""
    
    with app.app_context():
        try:
            # First, create all tables if they don't exist
            print("🔄 Creating database tables...")
            db.create_all()
            print("✅ Database tables created/verified")
            
            # Check if teams table exists
            table_exists = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'teams'
                )
            """)).fetchone()[0]
            
            if not table_exists:
                print("❌ Teams table still doesn't exist after create_all()")
                return False
            
            # Check if api_football_id column already exists
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'teams' 
                AND column_name = 'api_football_id'
            """)).fetchone()
            
            if result:
                print("✅ api_football_id column already exists in teams table")
                return True
            
            # Add the column if it doesn't exist
            print("🔄 Adding api_football_id column to teams table...")
            db.session.execute(text("""
                ALTER TABLE teams 
                ADD COLUMN api_football_id INTEGER UNIQUE
            """))
            
            db.session.commit()
            print("✅ Successfully added api_football_id column")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            db.session.rollback()
            return False


if __name__ == "__main__":
    print("🚀 Starting database migration...")
    
    if migrate_database():
        print("🎉 Migration completed successfully!")
    else:
        print("❌ Migration failed!")
        sys.exit(1) 