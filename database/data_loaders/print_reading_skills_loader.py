import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import sys
import os

# ---- Update these imports for your actual project structure ----
from models.configuration.config import DATABASE_URL, DATABASE_DIR

# Import your ORM models from db_main.py
from models.db_main import (
    AcademicTask, MechanicalTask, ElectricalTask
)

# Path to Excel load sheet
LOAD_SHEET_PATH = os.path.join(DATABASE_DIR, 'loadsheets', 'skills_matrix', 'print_reading_skills_matrix.xlsx')

# Supported ORM classes for this loader
ORM_MAP = {
    "AcademicTask": AcademicTask,
    "MechanicalTask": MechanicalTask,
    "ElectricalTask": ElectricalTask,
}

def load_print_reading_skills(filename=None, db_url=None):
    filename = filename or LOAD_SHEET_PATH
    db_url = db_url or DATABASE_URL

    # Connect to DB
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print(f"Loading Print Reading skills from: {filename}")

        # Read Excel file
        df = pd.read_excel(filename)

        count = 0
        skipped = 0

        for idx, row in df.iterrows():
            try:
                orm_type = str(row["ORM Class"]).strip()
                cls = ORM_MAP.get(orm_type)
                if not cls:
                    print(f"Skipping row {idx}: Unsupported ORM class '{orm_type}'")
                    skipped += 1
                    continue

                kwargs = {}

                # AcademicTask (for blueprint reading/academic tasks)
                if orm_type == "AcademicTask":
                    kwargs['competency_name'] = row.get("Task Object", "")
                    kwargs['description'] = f"{row.get('Task Action', '')} - {row.get('Task Object', '')}"
                    kwargs['skill_operation'] = row.get("Task Action", "")
                    kwargs['skill_concept'] = row.get("Task Object", "")
                    kwargs['verification_method'] = row.get("Verification Method", "")
                    kwargs['required_for_level_1'] = False
                    kwargs['required_for_level_2'] = True
                    kwargs['level'] = "2"
                    kwargs['proficiency_level'] = "Level_2_B"
                    kwargs['sub_category'] = row.get("Subcategory", "")

                # MechanicalTask (for hydraulics/pneumatics)
                elif orm_type == "MechanicalTask":
                    kwargs['competency_name'] = row.get("Task Object", "")
                    kwargs['description'] = f"{row.get('Task Action', '')} - {row.get('Task Object', '')}"
                    kwargs['task_action'] = row.get("Task Action", "")
                    kwargs['task_object'] = row.get("Task Object", "")
                    kwargs['verification_method'] = row.get("Verification Method", "")
                    kwargs['required_for_level_1'] = False
                    kwargs['required_for_level_2'] = True
                    kwargs['level'] = "2"
                    kwargs['proficiency_level'] = "Level_2_B"
                    kwargs['sub_category'] = row.get("Subcategory", "")

                # ElectricalTask (for electrical schematics)
                elif orm_type == "ElectricalTask":
                    kwargs['competency_name'] = row.get("Task Object", "")
                    kwargs['description'] = f"{row.get('Task Action', '')} - {row.get('Task Object', '')}"
                    kwargs['task_action'] = row.get("Task Action", "")
                    kwargs['task_object'] = row.get("Task Object", "")
                    kwargs['verification_method'] = row.get("Verification Method", "")
                    kwargs['required_for_level_1'] = False
                    kwargs['required_for_level_2'] = True
                    kwargs['level'] = "2"
                    kwargs['proficiency_level'] = "Level_2_B"
                    kwargs['sub_category'] = row.get("Subcategory", "")

                # Clean up
                kwargs = {k: v for k, v in kwargs.items() if v is not None and str(v).strip()}

                skill = cls(**kwargs)
                session.add(skill)
                count += 1

                if count % 10 == 0:
                    print(f"Processed {count} records so far...")

            except Exception as e:
                print(f"Error processing row {idx}: {e}")
                skipped += 1

        session.commit()
        print(f"Successfully loaded {count} Print Reading skills/tasks to database (skipped: {skipped})")

    except Exception as e:
        print(f"Error loading skills: {e}")
        session.rollback()
    finally:
        session.close()
        print("Database session closed.")

if __name__ == "__main__":
    load_print_reading_skills()
