from sqlalchemy import text
from app.core.database import SessionLocal

def run_migration():
    print("--- Starting Database Migration ---")
    db = SessionLocal()
    try:
        # 1. Add missing columns to transactions
        print("Migrating 'transactions' table...")
        
        # Check if column exists first to avoid errors
        res = db.execute(text("DESC transactions")).fetchall()
        cols = [r[0] for r in res]
        
        if 'quantity' not in cols:
            db.execute(text("ALTER TABLE transactions ADD COLUMN quantity DECIMAL(15,3)"))
            print("Added 'quantity'")
            
        if 'gst_amount' not in cols:
            db.execute(text("ALTER TABLE transactions ADD COLUMN gst_amount DECIMAL(15,2)"))
            print("Added 'gst_amount'")
            
        if 'description' not in cols:
            db.execute(text("ALTER TABLE transactions ADD COLUMN description TEXT"))
            print("Added 'description'")

        # 2. Sync data if useful (Move old 'gst' to 'gst_amount')
        if 'gst' in cols and 'gst_amount' in cols:
            db.execute(text("UPDATE transactions SET gst_amount = gst WHERE gst_amount IS NULL"))
            print("Synced 'gst' to 'gst_amount'")

        db.commit()
        print("✅ Migration successful.")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
