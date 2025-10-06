from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
from datetime import datetime
import os
from models.db_main import (
    Base, CoreCompetency, TechnicalSkill, ElectricalSkill, MechanicalSkill,
    ToolSkill, OperationalSkill, AcademicCompetency, SafetyCompetency,
    LeadershipCompetency, CommunicationCompetency, TrainingCompetency,
    ElectricalTask, MechanicalTask, ToolTask, OperationalTask,
    AcademicTask, SafetyTask, LeadershipTask, CommunicationTask, TrainingTask
)


def export_all_skills_to_excel():
    """
    Export all skills and competencies to an Excel file with multiple sheets
    """
    # Create database connection
    engine = create_engine(r'sqlite:///C:\Users\10169062\PycharmProjects\pythonProject2\database\maintenance_skills.db')

    Session = sessionmaker(bind=engine)
    session = Session()

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"All_Skills_Report_{timestamp}.xlsx"
    filepath = os.path.join(os.getcwd(), filename)

    try:
        print(f"Exporting skills data to Excel: {filename}")

        # Create Excel writer object
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:

            # 1. Export All Competencies Summary
            print("  - Creating All Competencies sheet...")
            all_competencies_df = create_all_competencies_sheet(session)
            all_competencies_df.to_excel(writer, sheet_name='All_Competencies', index=False)

            # 2. Export by Category
            print("  - Creating category-specific sheets...")

            # Core Competencies
            core_df = create_core_competencies_sheet(session)
            if not core_df.empty:
                core_df.to_excel(writer, sheet_name='Core_Competencies', index=False)

            # Electrical Skills & Tasks
            electrical_df = create_electrical_sheet(session)
            if not electrical_df.empty:
                electrical_df.to_excel(writer, sheet_name='Electrical_Skills', index=False)

            # Mechanical Skills & Tasks
            mechanical_df = create_mechanical_sheet(session)
            if not mechanical_df.empty:
                mechanical_df.to_excel(writer, sheet_name='Mechanical_Skills', index=False)

            # Tool Skills & Tasks
            tool_df = create_tool_sheet(session)
            if not tool_df.empty:
                tool_df.to_excel(writer, sheet_name='Tool_Skills', index=False)

            # Operational Skills & Tasks
            operational_df = create_operational_sheet(session)
            if not operational_df.empty:
                operational_df.to_excel(writer, sheet_name='Operational_Skills', index=False)

            # Academic Competencies & Tasks
            academic_df = create_academic_sheet(session)
            if not academic_df.empty:
                academic_df.to_excel(writer, sheet_name='Academic_Competencies', index=False)

            # Safety Competencies & Tasks
            safety_df = create_safety_sheet(session)
            if not safety_df.empty:
                safety_df.to_excel(writer, sheet_name='Safety_Competencies', index=False)

            # Leadership Competencies & Tasks
            leadership_df = create_leadership_sheet(session)
            if not leadership_df.empty:
                leadership_df.to_excel(writer, sheet_name='Leadership_Skills', index=False)

            # Communication Competencies & Tasks
            communication_df = create_communication_sheet(session)
            if not communication_df.empty:
                communication_df.to_excel(writer, sheet_name='Communication_Skills', index=False)

            # Training Competencies & Tasks
            training_df = create_training_sheet(session)
            if not training_df.empty:
                training_df.to_excel(writer, sheet_name='Training_Skills', index=False)

            # 3. Create Summary Statistics Sheet
            print("  - Creating summary statistics...")
            summary_df = create_summary_sheet(session)
            summary_df.to_excel(writer, sheet_name='Summary_Statistics', index=False)

            # 4. Create Database Structure Analysis
            print("  - Creating database structure analysis...")
            structure_df = create_structure_analysis_sheet(session)
            structure_df.to_excel(writer, sheet_name='Database_Structure', index=False)

        print(f"✅ Excel file created successfully: {filepath}")
        print(f"📊 File contains multiple sheets with all skills and competencies data")

        # Print summary to console
        print_console_summary(session)

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()

    return filepath


def create_all_competencies_sheet(session):
    """Create a comprehensive sheet with all competencies"""
    query = text("""
                 SELECT id,
                        competency_name,
                        description,
                        competency_type,
                        level,
                        proficiency_level,
                        required_for_level_1,
                        required_for_level_2,
                        required_for_level_3,
                        required_for_maintenance_tech
                 FROM core_competencies
                 ORDER BY competency_type, competency_name
                 """)

    result = session.execute(query)
    data = []

    for row in result.fetchall():
        requirements = []
        if row[6]:  # required_for_level_1
            requirements.append("Level 1")
        if row[7]:  # required_for_level_2
            requirements.append("Level 2")
        if row[8]:  # required_for_level_3
            requirements.append("Level 3")
        if row[9]:  # required_for_maintenance_tech
            requirements.append("Maintenance Tech")

        data.append({
            'ID': row[0],
            'Competency_Name': row[1],
            'Description': row[2],
            'Competency_Type': row[3] or 'core',
            'Level': row[4],
            'Proficiency_Level': row[5],
            'Required_For': ', '.join(requirements) if requirements else 'None'
        })

    return pd.DataFrame(data)


def create_core_competencies_sheet(session):
    """Create sheet for core competencies only"""
    query = text("""
                 SELECT competency_name,
                        description,
                        level,
                        proficiency_level,
                        required_for_level_1,
                        required_for_level_2,
                        required_for_level_3,
                        required_for_maintenance_tech
                 FROM core_competencies
                 WHERE competency_type = 'core'
                    OR competency_type IS NULL
                 ORDER BY competency_name
                 """)

    result = session.execute(query)
    data = []

    for row in result.fetchall():
        requirements = []
        if row[4]:  # required_for_level_1
            requirements.append("Level 1")
        if row[5]:  # required_for_level_2
            requirements.append("Level 2")
        if row[6]:  # required_for_level_3
            requirements.append("Level 3")
        if row[7]:  # required_for_maintenance_tech
            requirements.append("Maintenance Tech")

        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Level': row[2],
            'Proficiency_Level': row[3],
            'Required_For': ', '.join(requirements) if requirements else 'None'
        })

    return pd.DataFrame(data)


def create_electrical_sheet(session):
    """Create comprehensive electrical skills sheet"""
    # Get electrical skills
    skills_query = text("""
                        SELECT cc.competency_name,
                               cc.description,
                               es.sub_category,
                               es.voltage_level,
                               cc.level,
                               cc.proficiency_level,
                               'Electrical Skill' as type
                        FROM core_competencies cc
                                 JOIN electrical_skills es ON cc.id = es.id
                        WHERE cc.competency_type = 'electrical'

                        UNION ALL

                        SELECT cc.competency_name,
                               cc.description,
                               es.sub_category,
                               es.voltage_level,
                               cc.level,
                               cc.proficiency_level,
                               'Electrical Task' as type
                        FROM core_competencies cc
                                 JOIN electrical_skills es ON cc.id = es.id
                                 JOIN electrical_tasks et ON es.id = et.id
                        WHERE cc.competency_type = 'electrical_task'

                        ORDER BY type, competency_name
                        """)

    # Get task details
    task_query = text("""
                      SELECT cc.competency_name,
                             et.task_action,
                             et.task_object,
                             et.verification_method
                      FROM core_competencies cc
                               JOIN electrical_tasks et ON cc.id = et.id
                      WHERE cc.competency_type = 'electrical_task'
                      """)

    # Execute queries
    skills_result = session.execute(skills_query)
    task_result = session.execute(task_query)

    # Create task lookup
    task_details = {}
    for row in task_result.fetchall():
        task_details[row[0]] = {
            'action': row[1],
            'object': row[2],
            'verification': row[3]
        }

    # Build data
    data = []
    for row in skills_result.fetchall():
        name = row[0]
        record = {
            'Competency_Name': name,
            'Description': row[1],
            'Sub_Category': row[2],
            'Voltage_Level': row[3],
            'Level': row[4],
            'Proficiency_Level': row[5],
            'Type': row[6],
            'Task_Action': task_details.get(name, {}).get('action', ''),
            'Task_Object': task_details.get(name, {}).get('object', ''),
            'Verification_Method': task_details.get(name, {}).get('verification', '')
        }
        data.append(record)

    return pd.DataFrame(data)


def create_mechanical_sheet(session):
    """Create comprehensive mechanical skills sheet"""
    skills_query = text("""
                        SELECT cc.competency_name,
                               cc.description,
                               ms.sub_category,
                               ms.equipment_category,
                               cc.level,
                               cc.proficiency_level,
                               'Mechanical Skill' as type
                        FROM core_competencies cc
                                 JOIN mechanical_skills ms ON cc.id = ms.id
                        WHERE cc.competency_type = 'mechanical'

                        UNION ALL

                        SELECT cc.competency_name,
                               cc.description,
                               ms.sub_category,
                               ms.equipment_category,
                               cc.level,
                               cc.proficiency_level,
                               'Mechanical Task' as type
                        FROM core_competencies cc
                                 JOIN mechanical_skills ms ON cc.id = ms.id
                                 JOIN mechanical_tasks mt ON ms.id = mt.id
                        WHERE cc.competency_type = 'mechanical_task'

                        ORDER BY type, competency_name
                        """)

    task_query = text("""
                      SELECT cc.competency_name,
                             mt.task_action,
                             mt.task_object,
                             mt.verification_method
                      FROM core_competencies cc
                               JOIN mechanical_tasks mt ON cc.id = mt.id
                      WHERE cc.competency_type = 'mechanical_task'
                      """)

    skills_result = session.execute(skills_query)
    task_result = session.execute(task_query)

    task_details = {}
    for row in task_result.fetchall():
        task_details[row[0]] = {
            'action': row[1],
            'object': row[2],
            'verification': row[3]
        }

    data = []
    for row in skills_result.fetchall():
        name = row[0]
        record = {
            'Competency_Name': name,
            'Description': row[1],
            'Sub_Category': row[2],
            'Equipment_Category': row[3],
            'Level': row[4],
            'Proficiency_Level': row[5],
            'Type': row[6],
            'Task_Action': task_details.get(name, {}).get('action', ''),
            'Task_Object': task_details.get(name, {}).get('object', ''),
            'Verification_Method': task_details.get(name, {}).get('verification', '')
        }
        data.append(record)

    return pd.DataFrame(data)


def create_tool_sheet(session):
    """Create tool skills sheet"""
    query = text("""
                 SELECT cc.competency_name,
                        cc.description,
                        ts.tool_type,
                        ts.primary_application,
                        cc.level,
                        cc.proficiency_level
                 FROM core_competencies cc
                          JOIN tool_skills ts ON cc.id = ts.id
                 WHERE cc.competency_type = 'tools'
                 ORDER BY competency_name
                 """)

    result = session.execute(query)
    data = []

    for row in result.fetchall():
        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Tool_Type': row[2],
            'Primary_Application': row[3],
            'Level': row[4],
            'Proficiency_Level': row[5]
        })

    return pd.DataFrame(data)


def create_operational_sheet(session):
    """Create operational skills sheet"""
    query = text("""
                 SELECT cc.competency_name,
                        cc.description,
                        os.operation_type,
                        os.machine_type,
                        cc.level,
                        cc.proficiency_level
                 FROM core_competencies cc
                          JOIN operational_skills os ON cc.id = os.id
                 WHERE cc.competency_type = 'operational'
                 ORDER BY competency_name
                 """)

    result = session.execute(query)
    data = []

    for row in result.fetchall():
        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Operation_Type': row[2],
            'Machine_Type': row[3],
            'Level': row[4],
            'Proficiency_Level': row[5]
        })

    return pd.DataFrame(data)


def create_academic_sheet(session):
    """Create academic competencies sheet"""
    query = text("""
                 SELECT cc.competency_name,
                        cc.description,
                        ac.subject_area,
                        ac.academic_level,
                        ac.external_source,
                        ac.credential_type,
                        cc.level,
                        cc.proficiency_level
                 FROM core_competencies cc
                          JOIN academic_competencies ac ON cc.id = ac.id
                 WHERE cc.competency_type = 'academic'
                 ORDER BY competency_name
                 """)

    result = session.execute(query)
    data = []

    for row in result.fetchall():
        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Subject_Area': row[2],
            'Academic_Level': row[3],
            'External_Source': row[4],
            'Credential_Type': row[5],
            'Level': row[6],
            'Proficiency_Level': row[7]
        })

    return pd.DataFrame(data)


def create_safety_sheet(session):
    """Create safety competencies sheet"""
    query = text("""
                 SELECT cc.competency_name,
                        cc.description,
                        sc.safety_category,
                        sc.safety_domain,
                        sc.regulatory_source,
                        cc.level,
                        cc.proficiency_level
                 FROM core_competencies cc
                          JOIN safety_competencies sc ON cc.id = sc.id
                 WHERE cc.competency_type = 'safety'
                 ORDER BY competency_name
                 """)

    result = session.execute(query)
    data = []

    for row in result.fetchall():
        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Safety_Category': row[2],
            'Safety_Domain': row[3],
            'Regulatory_Source': row[4],
            'Level': row[5],
            'Proficiency_Level': row[6]
        })

    return pd.DataFrame(data)


def create_leadership_sheet(session):
    """Create leadership competencies sheet"""
    query = text("""
                 SELECT cc.competency_name,
                        cc.description,
                        lc.leadership_type,
                        lc.leadership_scope,
                        cc.level,
                        cc.proficiency_level
                 FROM core_competencies cc
                          JOIN leadership_competencies lc ON cc.id = lc.id
                 WHERE cc.competency_type = 'leadership'
                 ORDER BY competency_name
                 """)

    result = session.execute(query)
    data = []

    for row in result.fetchall():
        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Leadership_Type': row[2],
            'Leadership_Scope': row[3],
            'Level': row[4],
            'Proficiency_Level': row[5]
        })

    return pd.DataFrame(data)


def create_communication_sheet(session):
    """Create communication competencies sheet"""
    query = text("""
                 SELECT cc.competency_name,
                        cc.description,
                        cc2.communication_method,
                        cc2.communication_audience,
                        cc.level,
                        cc.proficiency_level
                 FROM core_competencies cc
                          JOIN communication_competencies cc2 ON cc.id = cc2.id
                 WHERE cc.competency_type = 'communication'
                 ORDER BY competency_name
                 """)

    result = session.execute(query)
    data = []

    for row in result.fetchall():
        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Communication_Method': row[2],
            'Communication_Audience': row[3],
            'Level': row[4],
            'Proficiency_Level': row[5]
        })

    return pd.DataFrame(data)


def create_training_sheet(session):
    """Create training competencies sheet"""
    query = text("""
                 SELECT cc.competency_name,
                        cc.description,
                        tc.training_type,
                        tc.training_method,
                        cc.level,
                        cc.proficiency_level
                 FROM core_competencies cc
                          JOIN training_competencies tc ON cc.id = tc.id
                 WHERE cc.competency_type = 'training'
                 ORDER BY competency_name
                 """)

    result = session.execute(query)
    data = []

    for row in result.fetchall():
        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Training_Type': row[2],
            'Training_Method': row[3],
            'Level': row[4],
            'Proficiency_Level': row[5]
        })

    return pd.DataFrame(data)


def create_summary_sheet(session):
    """Create summary statistics sheet"""
    query = text("""
                 SELECT competency_type, COUNT(*) as count
                 FROM core_competencies
                 GROUP BY competency_type
                 ORDER BY competency_type
                 """)

    result = session.execute(query)
    data = []

    total_count = 0
    for row in result.fetchall():
        comp_type = row[0] or 'core'
        count = row[1]
        total_count += count

        data.append({
            'Competency_Type': comp_type.replace('_', ' ').title(),
            'Count': count
        })

    # Add total row
    data.append({
        'Competency_Type': 'TOTAL',
        'Count': total_count
    })

    return pd.DataFrame(data)


def create_structure_analysis_sheet(session):
    """Create database structure analysis"""
    data = []

    # Check each table
    tables = [
        'core_competencies',
        'electrical_skills',
        'mechanical_skills',
        'tool_skills',
        'operational_skills',
        'academic_competencies',
        'safety_competencies',
        'leadership_competencies',
        'communication_competencies',
        'training_competencies'
    ]

    for table in tables:
        try:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = result.scalar()
            data.append({
                'Table_Name': table,
                'Record_Count': count,
                'Status': 'OK'
            })
        except Exception as e:
            data.append({
                'Table_Name': table,
                'Record_Count': 0,
                'Status': f'Error: {str(e)}'
            })

    return pd.DataFrame(data)


def print_console_summary(session):
    """Print a quick summary to console"""
    query = text("""
                 SELECT competency_type, COUNT(*) as count
                 FROM core_competencies
                 GROUP BY competency_type
                 ORDER BY competency_type
                 """)

    result = session.execute(query)

    print("\n" + "=" * 50)
    print("SKILLS EXPORT SUMMARY")
    print("=" * 50)

    total = 0
    for row in result.fetchall():
        comp_type = row[0] or 'core'
        count = row[1]
        total += count
        print(f"  {comp_type.replace('_', ' ').title()}: {count}")

    print(f"\nTotal Skills/Competencies: {total}")
    print("=" * 50)


if __name__ == "__main__":
    try:
        export_all_skills_to_excel()
    except ImportError as e:
        if 'pandas' in str(e):
            print("❌ Error: pandas library is required for Excel export")
            print("Install with: pip install pandas openpyxl")
        elif 'openpyxl' in str(e):
            print("❌ Error: openpyxl library is required for Excel export")
            print("Install with: pip install openpyxl")
        else:
            print(f"❌ Import error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()