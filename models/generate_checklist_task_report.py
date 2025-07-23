import pandas as pd
from tabulate import tabulate
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.db_main import (
    AreaChecklist, ChecklistSection, ChecklistTask, TaskSkillAssignment,
    MechanicalTask, ElectricalTask, ToolTask, OperationalTask
)  # <-- Change as needed

DATABASE_URL = "sqlite:///maintenance_skills.db"  # or your actual connection string

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def select_checklist(session):
    checklists = session.query(AreaChecklist).all()
    print("\nAvailable Checklists:")
    print("0) [ALL CHECKLISTS]")
    for idx, checklist in enumerate(checklists, 1):
        area = checklist.area or ""
        desc = checklist.description or ""
        print(f"{idx}) {checklist.document_number} | {area} | {desc}")
    while True:
        choice = input("Enter a number to select a checklist (or 0 for all): ").strip()
        if not choice.isdigit():
            print("Please enter a number.")
            continue
        idx = int(choice)
        if 0 <= idx <= len(checklists):
            if idx == 0:
                return None  # All
            else:
                return checklists[idx-1]
        print("Invalid selection. Try again.")

def generate_checklist_task_skills_report(session, selected_checklist=None, excel_filename="checklist_task_report.xlsx"):
    rows = []
    checklists = [selected_checklist] if selected_checklist else session.query(AreaChecklist).all()
    for checklist in checklists:
        for section in checklist.sections:
            for task in section.tasks:
                base_row = {
                    "Checklist": f"{checklist.document_number} ({checklist.area})",
                    "Section": section.section_name,
                    "Task": task.task_description,
                    "Skill Type": "",
                    "Action": "",
                    "Object": "",
                    "Operation Type": "",
                    "Machine Type": "",
                    "Verification Method": ""
                }
                if not task.skill_assignments:
                    row = base_row.copy()
                    row["Skill Type"] = "None"
                    rows.append(row)
                    continue
                for skill in task.skill_assignments:
                    if skill.mechanical_task:
                        row = base_row.copy()
                        row.update({
                            "Skill Type": "Mechanical",
                            "Action": skill.mechanical_task.task_action,
                            "Object": skill.mechanical_task.task_object,
                            "Verification Method": skill.mechanical_task.verification_method
                        })
                        rows.append(row)
                    if skill.electrical_task:
                        row = base_row.copy()
                        row.update({
                            "Skill Type": "Electrical",
                            "Action": skill.electrical_task.task_action,
                            "Object": skill.electrical_task.task_object,
                            "Verification Method": skill.electrical_task.verification_method
                        })
                        rows.append(row)
                    if skill.tool_task:
                        row = base_row.copy()
                        row.update({
                            "Skill Type": "Tool",
                            "Action": skill.tool_task.task_action,
                            "Object": skill.tool_task.task_object,
                            "Verification Method": skill.tool_task.verification_method
                        })
                        rows.append(row)
                    if skill.operational_task:
                        row = base_row.copy()
                        row.update({
                            "Skill Type": "Operational",
                            "Action": skill.operational_task.task_action,
                            "Object": skill.operational_task.task_object,
                            "Operation Type": skill.operational_task.operation_type,
                            "Machine Type": skill.operational_task.machine_type,
                            "Verification Method": skill.operational_task.verification_method
                        })
                        rows.append(row)
    if rows:
        print(tabulate(rows, headers="keys", tablefmt="github"))
        df = pd.DataFrame(rows)
        # Dynamic filename if filtering by checklist
        if selected_checklist:
            excel_filename = f"checklist_task_report_{selected_checklist.document_number}.xlsx"
        df.to_excel(excel_filename, index=False)
        print(f"\nExcel report written to: {excel_filename}")
    else:
        print("No tasks found.")

if __name__ == "__main__":
    selected = select_checklist(session)
    generate_checklist_task_skills_report(session, selected_checklist=selected)
