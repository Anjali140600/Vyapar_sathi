import sys
from python_services.database_humanizer.db_processor import DBHumanizerModule

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"DB MODULE OUTPUT:\n{DBHumanizerModule().process(query)}")
    else:
        print("Usage: python run_db.py <field, value>")
        print("Example: python run_db.py total amount, 21000")
