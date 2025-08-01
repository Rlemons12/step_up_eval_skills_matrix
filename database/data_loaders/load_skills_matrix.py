import pandas as pd
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from models.configuration.config import DATABASE_URL, DATABASE_DIR
from models.configuration.log_config import info_id, warning_id, error_id, debug_id, set_request_id

from models.db_main import AcademicTask, MechanicalTask, ElectricalTask

request_id = set_request_id("SKILLS_MATRIX_LOADER")

EXCEL_FILE = os.path.join(DATABASE_DIR, 'loadsheets', 'skills_matrix', 'comprehensive.xlsx')
LEVEL = "Level 2"
PROFICIENCY_LEVEL = "B"

ORM_MAP = {
    "AcademicTask": AcademicTask,
    "MechanicalTask": MechanicalTask,
    "ElectricalTask": ElectricalTask,
}

def to_bool(val):
    if isinstance(val, str):
        return val.strip().lower() == "yes"
    return bool(val)

def insert_skill(row, session):
    orm_type = str(row["ORM Class"]).strip()
    cls = ORM_MAP.get(orm_type)
    if not cls:
        warning_id(f"Unsupported ORM Class: {orm_type}", request_id)
        return

    skill_id = str(row["Skill ID"]).strip()
    if session.query(cls).filter_by(competency_name=skill_id).first():
        info_id(f"Skill ID {skill_id} already exists. Skipping.", request_id)
        return

    try:
        # Shared fields for all classes
        kwargs = {
            "competency_name": skill_id,
            "description": f"{row.get('Task Action', '')} - {row.get('Task Object', '')}",
            "level": LEVEL,
            "proficiency_level": PROFICIENCY_LEVEL,
            "required_for_level_1": to_bool(row.get("Required for Level 1", "No")),
            "required_for_level_2": True,
        }

        if orm_type == "MechanicalTask":
            kwargs.update({
                "sub_category": row.get("Subcategory", ""),
                "task_action": row.get("Task Action", ""),
                "task_object": row.get("Task Object", ""),
                "verification_method": row.get("Verification Method", ""),
                "equipment_category": row.get("Tool/Voltage/Note", ""),
            })
        elif orm_type == "ElectricalTask":
            kwargs.update({
                "sub_category": row.get("Subcategory", ""),
                "task_action": row.get("Task Action", ""),
                "task_object": row.get("Task Object", ""),
                "verification_method": row.get("Verification Method", ""),
                "voltage_level": row.get("Tool/Voltage/Note", ""),
            })
        elif orm_type == "AcademicTask":
            kwargs.update({
                "skill_operation": row.get("Task Action", ""),
                "skill_concept": row.get("Task Object", ""),
                "verification_method": row.get("Verification Method", ""),
                # DO NOT ADD sub_category!
            })

        # Remove empty/None/NaN fields
        kwargs = {k: v for k, v in kwargs.items()
                  if v is not None and str(v).strip() and str(v).strip().lower() != "nan"}

        skill = cls(**kwargs)
        session.add(skill)
        session.commit()
        info_id(f"Inserted: {skill_id} ({orm_type})", request_id)
    except IntegrityError:
        session.rollback()
        warning_id(f"Duplicate Skill ID: {skill_id} (rolled back)", request_id)
    except Exception as e:
        session.rollback()
        error_id(f"Failed to insert {skill_id}: {e}", request_id)

def main():
    try:
        df = pd.read_excel(EXCEL_FILE)
        info_id(f"Loaded Excel file: {EXCEL_FILE} with {len(df)} rows.", request_id)
    except Exception as e:
        error_id(f"Failed to load Excel file: {e}", request_id)
        raise

    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    for idx, row in df.iterrows():
        insert_skill(row, session)

    session.close()
    info_id("Skill loading complete.", request_id)

if __name__ == "__main__":
    main()
