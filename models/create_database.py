import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_main import (
    Base, Employee, MaintenancePerson, Supervisor, CoreCompetency,
    AcademicCompetency, AcademicTask, SafetyCompetency, SafetyTask,
    LeadershipCompetency, LeadershipTask, CommunicationCompetency, CommunicationTask,
    TrainingCompetency, TrainingTask, TechnicalSkill,
    ElectricalSkill, ElectricalTask, MechanicalSkill, MechanicalTask, ToolSkill, ToolTask,
    OperationalSkill, OperationalTask,       # <-- NEW!
    AreaChecklist, ChecklistSection, ChecklistTask, ChecklistTaskCompetency,
    TaskSkillAssignment
)


def create_database(db_path="maintenance_skills.db"):
    """
    Create the SQLite database with all tables from your schema
    """

    # Remove existing database if it exists (optional - for fresh start)
    if os.path.exists(db_path):
        user_input = input(f"Database {db_path} already exists. Delete and recreate? (y/n): ")
        if user_input.lower() == 'y':
            os.remove(db_path)
            print(f"Removed existing database: {db_path}")

    # Create engine
    engine = create_engine(f'sqlite:///{db_path}', echo=True)

    print(f"Creating database: {db_path}")
    print("Creating all tables...")

    # Create all tables
    Base.metadata.create_all(engine)

    print("Database created successfully!")

    # Create session for testing
    Session = sessionmaker(bind=engine)
    session = Session()

    # Test the database by adding sample data
    create_sample_data(session)

    session.close()

    return engine


def create_sample_data(session):
    """
    Create some sample data to test the database
    """
    print("\nAdding sample data...")

    try:
        # Supervisor
        supervisor = Supervisor(
            employee_id="SUP001",
            name_first="John",
            name_last="Smith",
            hire_date="2020-01-15",
            status="Active",
            management_level=2
        )
        session.add(supervisor)
        session.flush()  # Get the ID

        # Maintenance Person
        maintenance_person = MaintenancePerson(
            employee_id="MNT001",
            name_first="Jane",
            name_last="Doe",
            hire_date="2022-03-10",
            status="Active",
            maintenance_level="Level 2",
            qualified_area="MMABF",
            reports_to_id=supervisor.id
        )
        session.add(maintenance_person)

        # Safety Competency
        safety_competency = CoreCompetency(
            competency_name="Basic Safety Training",
            description="Fundamental safety procedures and protocols",
            competency_type="safety",
            required_for_level_1=True,
            proficiency_level="Basic"
        )
        session.add(safety_competency)

        # ---- Operational Skill/Task Sample ----
        op_skill = OperationalSkill(
            competency_name="Operate Bag Sealer",
            description="Safely operate the bag sealer in manual mode",
            competency_type="operational",
            operation_type="Manual",
            machine_type="Bag Sealer",
            required_for_level_1=True
        )
        session.add(op_skill)
        session.flush()
        op_task = OperationalTask(
            id=op_skill.id,  # Ensures correct inheritance PK
            task_action="Operate",
            task_object="Bag Sealer",
            verification_method="Demonstrate manual operation"
        )
        session.add(op_task)

        session.commit()
        print("Sample data added successfully!")

        print(f"Created Supervisor: {supervisor.name_first} {supervisor.name_last} (ID: {supervisor.employee_id})")
        print(f"Created Maintenance Person: {maintenance_person.name_first} {maintenance_person.name_last} (ID: {maintenance_person.employee_id})")
        print(f"Created Competency: {safety_competency.competency_name}")
        print(f"Created Operational Skill: {op_skill.competency_name}")

    except Exception as e:
        print(f"Error adding sample data: {e}")
        session.rollback()


def verify_tables(engine):
    """
    Verify that all tables were created
    """
    print("\nVerifying tables...")

    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    expected_tables = [
        'employees', 'maintenance_persons', 'supervisors',
        'core_competencies', 'employee_competencies',
        'academic_competencies', 'academic_tasks',
        'safety_competencies', 'safety_tasks',
        'leadership_competencies', 'leadership_tasks',
        'communication_competencies', 'communication_tasks',
        'training_competencies', 'training_tasks',
        'technical_skills',
        'electrical_skills', 'electrical_tasks',
        'mechanical_skills', 'mechanical_tasks',
        'tool_skills', 'tool_tasks',
        'operational_skills', 'operational_tasks',    # <-- NEW!
        'area_checklists', 'checklist_sections', 'checklist_tasks',
        'checklist_task_competencies',
        'task_skill_assignment'
    ]

    print(f"Expected tables: {len(expected_tables)}")
    print(f"Created tables: {len(tables)}")

    missing_tables = set(expected_tables) - set(tables)
    extra_tables = set(tables) - set(expected_tables)

    if missing_tables:
        print(f"Missing tables: {missing_tables}")

    if extra_tables:
        print(f"Extra tables: {extra_tables}")

    if not missing_tables:
        print("✅ All expected tables created successfully!")

    print(f"\nCreated tables:")
    for table in sorted(tables):
        print(f"  - {table}")


def main():
    print("=== MAINTENANCE SKILLS DATABASE CREATOR ===")

    # Create the database
    engine = create_database()

    # Verify tables
    verify_tables(engine)

    print("\n=== DATABASE CREATION COMPLETE ===")
    print("You can now use this database with your ChecklistDataLoader script!")
    print(f"Database file: {os.path.abspath('maintenance_skills.db')}")


if __name__ == "__main__":
    main()
