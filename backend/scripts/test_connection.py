import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import engine

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        version = result.scalar()
        print("✅ Connected to Neon successfully!")
        print(f"Postgres version: {version}")
except Exception as e:
    print("❌ Connection failed.")
    print(e)