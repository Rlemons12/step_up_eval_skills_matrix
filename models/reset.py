"""
Database reset and repair utility
"""

import os
import sys

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)


def reset_database():
    """Remove and recreate the database"""
    db_files = ['task_evaluations.db', 'test_evaluations.db', 'integration_test.db', 'test_from_parent.db']

    print("Resetting database...")

    # Remove existing database files
    for db_file in db_files:
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
                print(f"✓ Removed {db_file}")
            except Exception as e:
                print(f"✗ Could not remove {db_file}: {e}")

    # Create fresh database
    try:
        from db_evaul_task import SimpleTaskEvaluationDB

        print("Creating fresh database...")
        db = SimpleTaskEvaluationDB()
        db.create_tables()
        db.setup_reference_data()
        print("✓ Database reset successfully!")

        return True

    except Exception as e:
        print(f"✗ Error creating database: {e}")
        return False


def check_database():
    """Check database status"""
    try:
        from db_evaul_task import SimpleTaskEvaluationDB

        print("Checking database...")
        db = SimpleTaskEvaluationDB()

        # Try to get statistics
        stats = db.get_summary_statistics()
        print(f"✓ Database is working - {stats['total_evaluations']} evaluations found")

        return True

    except Exception as e:
        print(f"✗ Database check failed: {e}")
        return False


def repair_database():
    """Try to repair database without losing data"""
    try:
        from db_evaul_task import SimpleTaskEvaluationDB

        print("Attempting database repair...")
        db = SimpleTaskEvaluationDB()

        # Just try to create tables (won't affect existing data)
        db.create_tables()

        # Try to setup reference data (should skip existing entries)
        db.setup_reference_data()

        print("✓ Database repair completed")
        return True

    except Exception as e:
        print(f"✗ Database repair failed: {e}")
        return False


def main():
    """Main function"""
    print("=" * 50)
    print("DATABASE REPAIR UTILITY")
    print("=" * 50)

    # First try to check if database is working
    if check_database():
        print("\n✓ Database is working fine!")
        print("You can start the API server with: python form_evaul.py api")
        return

    print("\n❌ Database has issues. Attempting repair...")

    # Try repair first (preserves data)
    if repair_database():
        if check_database():
            print("\n✓ Database repaired successfully!")
            print("You can start the API server with: python form_evaul.py api")
            return

    # If repair doesn't work, offer reset
    print("\n⚠️  Repair failed. You may need to reset the database.")
    print("WARNING: This will delete all existing evaluations!")

    response = input("Reset database? (y/N): ").lower().strip()

    if response == 'y':
        if reset_database():
            print("\n✓ Database reset successfully!")
            print("You can start the API server with: python form_evaul.py api")
        else:
            print("\n❌ Database reset failed!")
    else:
        print("\nDatabase reset cancelled.")
        print("Manual steps:")
        print("1. Delete task_evaluations.db file")
        print("2. Run: python form_evaul.py test")


if __name__ == "__main__":
    main()