import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the path so we can import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from models.configuration.config import DATABASE_DIR, DATABASE_URL
from models.configuration import info_id, debug_id, error_id, warning_id, with_request_id, set_request_id

from models.db_main import Base


@with_request_id
def create_database():
    """
    Create the SQLite database with all tables from your schema
    """
    request_id = set_request_id("DB_CREATE")
    info_id("Starting database creation process", request_id)

    # Ensure database directory exists
    os.makedirs(DATABASE_DIR, exist_ok=True)
    debug_id(f"Ensured database directory exists: {DATABASE_DIR}", request_id)

    # Get the database path from config
    db_path = os.path.join(DATABASE_DIR, 'maintenance_skills.db')

    # Remove existing database if it exists (optional - for fresh start)
    if os.path.exists(db_path):
        warning_id(f"Database {db_path} already exists", request_id)
        user_input = input(f"Database {db_path} already exists. Delete and recreate? (y/n): ")
        if user_input.lower() == 'y':
            os.remove(db_path)
            info_id(f"Removed existing database: {db_path}", request_id)
            print(f"Removed existing database: {db_path}")
        else:
            info_id("Keeping existing database", request_id)

    # Create engine using the DATABASE_URL from config
    debug_id(f"Creating SQLAlchemy engine with URL: {DATABASE_URL}", request_id)
    engine = create_engine(DATABASE_URL, echo=True)

    info_id(f"Creating database: {db_path}", request_id)
    print(f"Creating database: {db_path}")
    print("Creating all tables...")

    # Create all tables
    try:
        Base.metadata.create_all(engine)
        info_id("All database tables created successfully", request_id)
        print("Database created successfully!")
    except Exception as e:
        error_id(f"Failed to create database tables: {str(e)}", request_id)
        raise

    info_id("Database creation process completed", request_id)

    return engine


def verify_tables(engine, request_id):
    """
    Verify that all tables were created
    """
    info_id("Starting table verification", request_id)
    print("\nVerifying tables...")

    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = [
        # Core employee tables
        'employees', 'maintenance_persons', 'supervisors',

        # Competency tables
        'core_competencies', 'employee_competencies', 'employee_task_progress',

        # Academic competencies
        'academic_competencies', 'academic_tasks',

        # Safety competencies
        'safety_competencies', 'safety_tasks',

        # Leadership competencies
        'leadership_competencies', 'leadership_tasks',

        # Communication competencies
        'communication_competencies', 'communication_tasks',

        # Training competencies
        'training_competencies', 'training_tasks',

        # Technical skills
        'technical_skills',
        'electrical_skills', 'electrical_tasks',
        'mechanical_skills', 'mechanical_tasks',
        'tool_skills', 'tool_tasks',
        'operational_skills', 'operational_tasks',

        # Checklist system
        'area_checklists', 'checklist_sections', 'checklist_tasks',
        'checklist_task_competencies',
        'task_skill_assignment',

        # Scheduling system
        'shifts', 'shift_days', 'employee_schedules',

        # Attendance system
        'attendance_records', 'attendance_issues'
    ]

    info_id(f"Expected {len(expected_tables)} tables, found {len(tables)} tables", request_id)
    print(f"Expected tables: {len(expected_tables)}")
    print(f"Created tables: {len(tables)}")

    missing_tables = set(expected_tables) - set(tables)
    extra_tables = set(tables) - set(expected_tables)

    if missing_tables:
        error_id(f"Missing tables: {missing_tables}", request_id)
        print(f"Missing tables: {missing_tables}")

    if extra_tables:
        warning_id(f"Extra tables found: {extra_tables}", request_id)
        print(f"Extra tables: {extra_tables}")

    if not missing_tables:
        info_id("All expected tables created successfully!", request_id)
        print("✅ All expected tables created successfully!")

    debug_id(f"Created tables: {sorted(tables)}", request_id)
    print(f"\nCreated tables:")
    for table in sorted(tables):
        print(f"  - {table}")


def main():
    request_id = set_request_id("MAIN_DB_CREATE")
    info_id("=== MAINTENANCE SKILLS DATABASE CREATOR ===", request_id)
    print("=== MAINTENANCE SKILLS DATABASE CREATOR ===")

    try:
        # Create the database
        engine = create_database()

        # Verify tables
        verify_tables(engine, request_id)

        info_id("Database creation process completed successfully", request_id)
        print("\n=== DATABASE CREATION COMPLETE ===")
        print("You can now use this database with your ChecklistDataLoader script!")
        print(f"Database file: {os.path.join(DATABASE_DIR, 'maintenance_skills.db')}")

    except Exception as e:
        error_id(f"Database creation failed: {str(e)}", request_id)
        print(f"\n❌ DATABASE CREATION FAILED: {e}")
        raise


if __name__ == "__main__":
    main()