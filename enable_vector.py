from app.core.database import engine
from sqlalchemy import text

def enable_vector():
    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("✓ PgVector extension is enabled")
    except Exception as e:
        print(f"⚠ Could not enable PgVector: {e}")

if __name__ == "__main__":
    enable_vector()
