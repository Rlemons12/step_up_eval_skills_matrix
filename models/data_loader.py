import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_main import (
    ElectricalSkill, ElectricalTask,
    MechanicalSkill, MechanicalTask,
    TaskSkillAssignment
)

# --- Setup DB ---
DATABASE_URL = "sqlite:///maintenance_skills.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def load_skills(file_path: str):
    print(f"\n📂 Reading: {file_path}")
    # Determine if it's CSV or Excel
    if file_path.lower().endswith(".csv"):
        df = pd.read_csv(file_path, encoding='latin1')  # or encoding='cp1252'
    else:
        df = pd.read_excel(file_path)

    df.columns = [col.strip() for col in df.columns]

    for _, row in df.iterrows():
        orm_class = row.get("ORM Class", "").strip()
        task_action = row.get("Task Action", "").strip()
        task_object = row.get("Task Object", "").strip()
        verification_method = row.get("Verification Method", "").strip()
        category = row.get("Category", "").strip()

        if orm_class == "ElectricalTask":
            # --- Electrical ---
            skill = session.query(ElectricalSkill).filter_by(sub_category=category).first()
            if not skill:
                skill = ElectricalSkill(
                    sub_category=category,
                    voltage_level="Low",  # Placeholder or logic can be added
                    skill_category="Electrical"
                )
                session.add(skill)
                session.flush()

            task = ElectricalTask(
                task_action=task_action,
                task_object=task_object,
                verification_method=verification_method,
                sub_category=category,
                voltage_level=skill.voltage_level,
                skill_category=skill.skill_category
            )
            session.add(task)
            session.flush()
            session.add(TaskSkillAssignment(electrical_task_id=task.id))

        elif orm_class == "MechanicalTask":
            # --- Mechanical ---
            skill = session.query(MechanicalSkill).filter_by(sub_category=category).first()
            if not skill:
                skill = MechanicalSkill(
                    sub_category=category,
                    equipment_category="General",  # Placeholder or refine later
                    skill_category="Mechanical"
                )
                session.add(skill)
                session.flush()

            task = MechanicalTask(
                task_action=task_action,
                task_object=task_object,
                verification_method=verification_method,
                sub_category=category,
                equipment_category=skill.equipment_category,
                skill_category=skill.skill_category
            )
            session.add(task)
            session.flush()
            session.add(TaskSkillAssignment(mechanical_task_id=task.id))

        else:
            print(f"⚠️ Skipping unrecognized ORM Class: {orm_class}")

if __name__ == "__main__":
    try:
        file_path = input("Enter the path to the skills matrix file (CSV or Excel): ").strip()
        if not os.path.isfile(file_path):
            print(f"❌ File not found: {file_path}")
        else:
            load_skills(file_path)
            session.commit()
            print("\n✅ Import complete.")
    except Exception as e:
        print(f"\n❌ An error occurred: {e}")
