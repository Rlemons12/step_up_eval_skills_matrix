from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import pandas as pd
from datetime import datetime
import os


def export_employee_skills_to_excel(employee_id=None, employee_name=None):
    """
    Export all skills and competencies for a specific employee to Excel
    Can search by employee_id or employee_name
    """
    # Create database connection
    engine = create_engine(r'sqlite:///C:\Users\10169062\PycharmProjects\pythonProject2\database\maintenance_skills.db')

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Find the employee
        employee = find_employee(session, employee_id, employee_name)
        if not employee:
            print("❌ Employee not found!")
            return None

        print(f"📋 Generating skills report for: {employee['name']} (ID: {employee['employee_id']})")

        # Create filename with employee info and timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = employee['name'].replace(' ', '_').replace(',', '')
        filename = f"Employee_Skills_{safe_name}_{employee['employee_id']}_{timestamp}.xlsx"
        filepath = os.path.join(os.getcwd(), filename)

        # Ensure output directory exists (cwd should exist, but keep this safe)
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        # Create Excel writer object
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:

            # 1. Employee Information Sheet
            print("  - Creating employee information sheet...")
            employee_info_df = create_employee_info_sheet(session, employee)
            employee_info_df.to_excel(writer, sheet_name='Employee_Info', index=False)

            # 2. Current Competencies (Skills they have achieved)
            print("  - Creating current competencies sheet...")
            current_comp_df = create_current_competencies_sheet(session, employee['id'])
            current_comp_df.to_excel(writer, sheet_name='Current_Competencies', index=False)

            # 3. Task Progress (What they're working on)
            print("  - Creating task progress sheet...")
            task_progress_df = create_task_progress_sheet(session, employee['id'])
            task_progress_df.to_excel(writer, sheet_name='Task_Progress', index=False)

            # 4. Required Competencies (Based on their level/position)
            print("  - Creating required competencies sheet...")
            required_comp_df = create_required_competencies_sheet(session, employee)
            required_comp_df.to_excel(writer, sheet_name='Required_Competencies', index=False)

            # 5. Skills Gap Analysis
            print("  - Creating skills gap analysis...")
            gap_analysis_df = create_skills_gap_analysis(session, employee['id'])
            gap_analysis_df.to_excel(writer, sheet_name='Skills_Gap_Analysis', index=False)

            # 6. All Available Competencies (Complete catalog)
            print("  - Creating all available competencies...")
            all_available_df = create_all_available_competencies_sheet(session)
            all_available_df.to_excel(writer, sheet_name='All_Available_Skills', index=False)

            # 7. Assigned Tasks and Competencies
            print("  - Creating assigned tasks sheet...")
            assigned_tasks_df = create_assigned_tasks_sheet(session, employee['id'])
            assigned_tasks_df.to_excel(writer, sheet_name='Assigned_Tasks', index=False)

            # 8. Competency Assignments by Checklist
            print("  - Creating competency assignments...")
            competency_assignments_df = create_competency_assignments_sheet(session, employee['id'])
            competency_assignments_df.to_excel(writer, sheet_name='Competency_Assignments', index=False)

            # 9. Competency Summary by Category
            print("  - Creating competency summary...")
            summary_df = create_employee_competency_summary(session, employee['id'])
            summary_df.to_excel(writer, sheet_name='Competency_Summary', index=False)

        print(f"✅ Employee skills report created: {filepath}")

        # Print assignment summary to console
        print_assignment_summary(session, employee)

        return filepath

    except Exception as e:
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()


def find_employee(session, employee_id=None, employee_name=None):
    """Find employee by ID or name"""
    if employee_id:
        query = text("""
                     SELECT id, employee_id, name_first, name_last, hire_date, status, employee_type
                     FROM employees
                     WHERE id = :emp_id
                        OR employee_id = :emp_id
                     """)
        result = session.execute(query, {'emp_id': employee_id}).fetchone()
    elif employee_name:
        # Search by name (first, last, or full name)
        query = text("""
                     SELECT id, employee_id, name_first, name_last, hire_date, status, employee_type
                     FROM employees
                     WHERE name_first LIKE :name
                        OR name_last LIKE :name
                        OR (name_first || ' ' || name_last) LIKE :name
                     """)
        result = session.execute(query, {'name': f'%{employee_name}%'}).fetchone()
    else:
        return None

    if result:
        return {
            'id': result[0],
            'employee_id': result[1],
            'name_first': result[2],
            'name_last': result[3],
            'name': f"{result[2]} {result[3]}",
            'hire_date': result[4],
            'status': result[5],
            'employee_type': result[6]
        }
    return None


def create_employee_info_sheet(session, employee):
    """Create employee information sheet"""
    data = [
        {'Field': 'Employee ID', 'Value': employee['employee_id']},
        {'Field': 'First Name', 'Value': employee['name_first']},
        {'Field': 'Last Name', 'Value': employee['name_last']},
        {'Field': 'Full Name', 'Value': employee['name']},
        {'Field': 'Hire Date', 'Value': employee['hire_date']},
        {'Field': 'Status', 'Value': employee['status']},
        {'Field': 'Employee Type', 'Value': employee['employee_type']},
        {'Field': 'Report Generated', 'Value': datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    ]

    return pd.DataFrame(data)


def create_current_competencies_sheet(session, employee_id):
    """Create sheet showing employee's current competencies"""
    query = text("""
                 SELECT cc.competency_name,
                        cc.description,
                        cc.competency_type,
                        ec.proficiency_achieved,
                        ec.level_achieved,
                        ec.date_achieved,
                        ec.status,
                        ec.notes,
                        assessor.name_first || ' ' || assessor.name_last as assessed_by
                 FROM employee_competencies ec
                          JOIN core_competencies cc ON ec.competency_id = cc.id
                          LEFT JOIN employees assessor ON ec.assessed_by = assessor.id
                 WHERE ec.employee_id = :emp_id
                 ORDER BY cc.competency_type, cc.competency_name
                 """)

    result = session.execute(query, {'emp_id': employee_id})
    data = []

    for row in result.fetchall():
        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Competency_Type': (row[2] or 'core').replace('_', ' ').title(),
            'Proficiency_Achieved': row[3],
            'Level_Achieved': row[4],
            'Date_Achieved': row[5],
            'Status': row[6],
            'Notes': row[7],
            'Assessed_By': row[8]
        })

    return pd.DataFrame(data)


def create_task_progress_sheet(session, employee_id):
    """Create sheet showing employee's task progress"""
    query = text("""
                 SELECT cc.competency_name,
                        ct.task_description,
                        etp.completion_status,
                        etp.completion_date,
                        etp.notes,
                        cs.section_name,
                        ac.description as checklist_description
                 FROM employee_task_progress etp
                          JOIN checklist_tasks ct ON etp.checklist_task_id = ct.id
                          LEFT JOIN core_competencies cc ON etp.competency_id = cc.id
                          LEFT JOIN checklist_sections cs ON ct.section_id = cs.id
                          LEFT JOIN area_checklists ac ON cs.checklist_id = ac.id
                 WHERE etp.employee_id = :emp_id
                 ORDER BY etp.completion_status DESC, cc.competency_name
                 """)

    result = session.execute(query, {'emp_id': employee_id})
    data = []

    for row in result.fetchall():
        data.append({
            'Related_Competency': row[0],
            'Task_Description': row[1],
            'Completion_Status': row[2],
            'Completion_Date': row[3],
            'Notes': row[4],
            'Section': row[5],
            'Checklist': row[6]
        })

    return pd.DataFrame(data)


def create_required_competencies_sheet(session, employee):
    """Create sheet showing competencies required for employee's level/type"""
    query = text("""
                 SELECT competency_name,
                        description,
                        competency_type,
                        level,
                        proficiency_level,
                        CASE
                            WHEN required_for_level_1 = 1 THEN 'Level 1'
                            WHEN required_for_level_2 = 1 THEN 'Level 2'
                            WHEN required_for_level_3 = 1 THEN 'Level 3'
                            WHEN required_for_maintenance_tech = 1 THEN 'Maintenance Tech'
                            ELSE 'General'
                            END as required_for,
                        CASE
                            WHEN cc.id IN (SELECT competency_id
                                           FROM employee_competencies
                                           WHERE employee_id = :emp_id) THEN 'Achieved'
                            ELSE 'Not Achieved'
                            END as achievement_status
                 FROM core_competencies cc
                 WHERE required_for_level_1 = 1
                    OR required_for_level_2 = 1
                    OR required_for_level_3 = 1
                    OR required_for_maintenance_tech = 1
                 ORDER BY required_for, competency_type, competency_name
                 """)

    result = session.execute(query, {'emp_id': employee['id']})
    data = []

    for row in result.fetchall():
        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Competency_Type': (row[2] or 'core').replace('_', ' ').title(),
            'Level': row[3],
            'Proficiency_Level': row[4],
            'Required_For': row[5],
            'Achievement_Status': row[6]
        })

    return pd.DataFrame(data)


def create_skills_gap_analysis(session, employee_id):
    """Create skills gap analysis showing what employee needs"""
    query = text("""
                 SELECT cc.competency_name,
                        cc.description,
                        cc.competency_type,
                        cc.level,
                        cc.proficiency_level,
                        CASE
                            WHEN required_for_level_1 = 1 THEN 'Level 1'
                            WHEN required_for_level_2 = 1 THEN 'Level 2'
                            WHEN required_for_level_3 = 1 THEN 'Level 3'
                            WHEN required_for_maintenance_tech = 1 THEN 'Maintenance Tech'
                            ELSE 'Optional'
                            END   as required_for,
                        'Missing' as gap_status,
                        'High'    as priority
                 FROM core_competencies cc
                 WHERE (required_for_level_1 = 1 OR required_for_level_2 = 1
                     OR required_for_level_3 = 1 OR required_for_maintenance_tech = 1)
                   AND cc.id NOT IN (SELECT competency_id
                                     FROM employee_competencies
                                     WHERE employee_id = :emp_id
                                       AND status = 'Active')

                 UNION ALL

                 SELECT cc.competency_name,
                        cc.description,
                        cc.competency_type,
                        cc.level,
                        cc.proficiency_level,
                        'Optional'  as required_for,
                        'Available' as gap_status,
                        'Medium'    as priority
                 FROM core_competencies cc
                 WHERE NOT (required_for_level_1 = 1 OR required_for_level_2 = 1
                     OR required_for_level_3 = 1 OR required_for_maintenance_tech = 1)
                   AND cc.id NOT IN (SELECT competency_id
                                     FROM employee_competencies
                                     WHERE employee_id = :emp_id)

                 ORDER BY gap_status, required_for, competency_type
                 """)

    result = session.execute(query, {'emp_id': employee_id})
    data = []

    for row in result.fetchall():
        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Competency_Type': (row[2] or 'core').replace('_', ' ').title(),
            'Level': row[3],
            'Proficiency_Level': row[4],
            'Required_For': row[5],
            'Gap_Status': row[6],
            'Priority': row[7]
        })

    return pd.DataFrame(data)


def create_all_available_competencies_sheet(session):
    """Create sheet with all available competencies"""
    query = text("""
                 SELECT competency_name,
                        description,
                        competency_type,
                        level,
                        proficiency_level,
                        CASE
                            WHEN required_for_level_1 = 1 THEN 'Level 1, '
                            ELSE ''
                            END ||
                        CASE
                            WHEN required_for_level_2 = 1 THEN 'Level 2, '
                            ELSE ''
                            END ||
                        CASE
                            WHEN required_for_level_3 = 1 THEN 'Level 3, '
                            ELSE ''
                            END ||
                        CASE
                            WHEN required_for_maintenance_tech = 1 THEN 'Maintenance Tech, '
                            ELSE ''
                            END as required_for_positions
                 FROM core_competencies
                 ORDER BY competency_type, competency_name
                 """)

    result = session.execute(query)
    data = []

    for row in result.fetchall():
        required_for = row[5].rstrip(', ') if row[5] else 'None'
        data.append({
            'Competency_Name': row[0],
            'Description': row[1],
            'Competency_Type': (row[2] or 'core').replace('_', ' ').title(),
            'Level': row[3],
            'Proficiency_Level': row[4],
            'Required_For_Positions': required_for
        })

    return pd.DataFrame(data)


def create_assigned_tasks_sheet(session, employee_id):
    """Create sheet showing tasks assigned to employee through skill assignments"""
    query = text("""
                 SELECT DISTINCT ct.task_description,
                                 cs.section_name,
                                 ac.description          as checklist_description,
                                 ac.area,
                                 cc_elec.competency_name as electrical_competency,
                                 cc_mech.competency_name as mechanical_competency,
                                 cc_tool.competency_name as tool_competency,
                                 cc_op.competency_name   as operational_competency,
                                 CASE
                                     WHEN etp.id IS NOT NULL THEN etp.completion_status
                                     ELSE 'Not Started'
                                     END                 as progress_status,
                                 etp.completion_date,
                                 etp.notes               as progress_notes
                 FROM checklist_tasks ct
                          JOIN checklist_sections cs ON ct.section_id = cs.id
                          JOIN area_checklists ac ON cs.checklist_id = ac.id
                          LEFT JOIN task_skill_assignment tsa ON ct.id = tsa.checklist_task_id
                          LEFT JOIN electrical_tasks et ON tsa.electrical_task_id = et.id
                          LEFT JOIN core_competencies cc_elec ON et.id = cc_elec.id
                          LEFT JOIN mechanical_tasks mt ON tsa.mechanical_task_id = mt.id
                          LEFT JOIN core_competencies cc_mech ON mt.id = cc_mech.id
                          LEFT JOIN tool_tasks tt ON tsa.tool_task_id = tt.id
                          LEFT JOIN core_competencies cc_tool ON tt.id = cc_tool.id
                          LEFT JOIN operational_tasks ot ON tsa.operational_task_id = ot.id
                          LEFT JOIN core_competencies cc_op ON ot.id = cc_op.id
                          LEFT JOIN employee_task_progress etp ON ct.id = etp.checklist_task_id AND etp.employee_id = :emp_id
                 WHERE tsa.checklist_task_id IS NOT NULL
                    OR ct.id IN (SELECT ctc.checklist_task_id
                                 FROM checklist_task_competencies ctc
                                          JOIN employee_competencies ec ON ctc.competency_id = ec.competency_id
                                 WHERE ec.employee_id = :emp_id)
                 ORDER BY ac.description, cs.section_name, ct.task_order
                 """)

    result = session.execute(query, {'emp_id': employee_id})
    data = []

    for row in result.fetchall():
        # Combine competency names
        competencies = []
        if row[4]:  # electrical_competency
            competencies.append(f"Electrical: {row[4]}")
        if row[5]:  # mechanical_competency
            competencies.append(f"Mechanical: {row[5]}")
        if row[6]:  # tool_competency
            competencies.append(f"Tool: {row[6]}")
        if row[7]:  # operational_competency
            competencies.append(f"Operational: {row[7]}")

        data.append({
            'Task_Description': row[0],
            'Section': row[1],
            'Checklist': row[2],
            'Area': row[3],
            'Related_Competencies': '; '.join(competencies) if competencies else 'None',
            'Progress_Status': row[8],
            'Completion_Date': row[9],
            'Progress_Notes': row[10]
        })

    return pd.DataFrame(data)


def create_competency_assignments_sheet(session, employee_id):
    """Create sheet showing competency assignments through checklist tasks"""
    # Use a simpler approach to avoid SQLite DISTINCT aggregation issues
    query = text("""
                 SELECT DISTINCT cc.competency_name,
                                 cc.description,
                                 cc.competency_type,
                                 ac.description as checklist_description,
                                 CASE
                                     WHEN ec.id IS NOT NULL THEN 'Achieved'
                                     ELSE 'Not Achieved'
                                     END        as competency_status,
                                 ec.proficiency_achieved,
                                 ec.date_achieved
                 FROM core_competencies cc
                          JOIN checklist_task_competencies ctc ON cc.id = ctc.competency_id
                          JOIN checklist_tasks ct ON ctc.checklist_task_id = ct.id
                          JOIN checklist_sections cs ON ct.section_id = cs.id
                          JOIN area_checklists ac ON cs.checklist_id = ac.id
                          LEFT JOIN employee_competencies ec ON cc.id = ec.competency_id AND ec.employee_id = :emp_id
                 ORDER BY cc.competency_type, cc.competency_name
                 """)

    result = session.execute(query, {'emp_id': employee_id})

    # Process results and group by competency
    competency_data = {}

    for row in result.fetchall():
        comp_name = row[0]
        if comp_name not in competency_data:
            competency_data[comp_name] = {
                'competency_name': row[0],
                'description': row[1],
                'competency_type': row[2],
                'checklists': set(),
                'competency_status': row[4],
                'proficiency_achieved': row[5],
                'date_achieved': row[6]
            }

        if row[3]:  # checklist_description
            competency_data[comp_name]['checklists'].add(row[3])

    # Now get task counts for each competency
    task_count_query = text("""
                            SELECT cc.competency_name,
                                   COUNT(ctc.checklist_task_id)                                   as total_tasks,
                                   COUNT(CASE WHEN etp.completion_status = 'Complete' THEN 1 END) as completed_tasks
                            FROM core_competencies cc
                                     JOIN checklist_task_competencies ctc ON cc.id = ctc.competency_id
                                     LEFT JOIN employee_task_progress etp
                                               ON ctc.checklist_task_id = etp.checklist_task_id
                                                   AND etp.employee_id = :emp_id
                            GROUP BY cc.id, cc.competency_name
                            ORDER BY cc.competency_name
                            """)

    task_counts = {}
    task_result = session.execute(task_count_query, {'emp_id': employee_id})

    for row in task_result.fetchall():
        task_counts[row[0]] = {
            'total_tasks': row[1],
            'completed_tasks': row[2]
        }

    # Build final data
    data = []
    for comp_name, comp_info in competency_data.items():
        task_info = task_counts.get(comp_name, {'total_tasks': 0, 'completed_tasks': 0})

        completion_percentage = 0
        if task_info['total_tasks'] > 0:
            completion_percentage = round((task_info['completed_tasks'] / task_info['total_tasks']) * 100, 1)

        # Format checklists
        checklists_str = '; '.join(sorted(comp_info['checklists'])) if comp_info['checklists'] else 'None'

        data.append({
            'Competency_Name': comp_info['competency_name'],
            'Description': comp_info['description'],
            'Competency_Type': (comp_info['competency_type'] or 'core').replace('_', ' ').title(),
            'Assigned_Tasks_Count': task_info['total_tasks'],
            'Completed_Tasks': task_info['completed_tasks'],
            'Completion_Percentage': f"{completion_percentage}%",
            'Assigned_Checklists': checklists_str,
            'Competency_Status': comp_info['competency_status'],
            'Proficiency_Achieved': comp_info['proficiency_achieved'],
            'Date_Achieved': comp_info['date_achieved']
        })

    return pd.DataFrame(data)


def create_employee_competency_summary(session, employee_id):
    """Create summary of employee competencies by category"""
    query = text("""
                 SELECT COALESCE(cc.competency_type, 'core') as category,
                        COUNT(*)                             as achieved_count,
                        AVG(CASE
                                WHEN ec.proficiency_achieved = 'Basic' THEN 1
                                WHEN ec.proficiency_achieved = 'Intermediate' THEN 2
                                WHEN ec.proficiency_achieved = 'Advanced' THEN 3
                                ELSE 0
                            END)                             as avg_proficiency_score
                 FROM employee_competencies ec
                          JOIN core_competencies cc ON ec.competency_id = cc.id
                 WHERE ec.employee_id = :emp_id
                   AND ec.status = 'Active'
                 GROUP BY cc.competency_type

                 UNION ALL

                 SELECT 'TOTAL'  as category,
                        COUNT(*) as achieved_count,
                        AVG(CASE
                                WHEN ec.proficiency_achieved = 'Basic' THEN 1
                                WHEN ec.proficiency_achieved = 'Intermediate' THEN 2
                                WHEN ec.proficiency_achieved = 'Advanced' THEN 3
                                ELSE 0
                            END) as avg_proficiency_score
                 FROM employee_competencies ec
                 WHERE ec.employee_id = :emp_id
                   AND ec.status = 'Active'

                 ORDER BY category
                 """)

    result = session.execute(query, {'emp_id': employee_id})
    data = []

    for row in result.fetchall():
        category = row[0].replace('_', ' ').title() if row[0] != 'TOTAL' else 'TOTAL'
        avg_score = round(row[2], 2) if row[2] else 0

        data.append({
            'Category': category,
            'Competencies_Achieved': row[1],
            'Average_Proficiency_Score': avg_score,
            'Proficiency_Level': get_proficiency_level(avg_score)
        })

    return pd.DataFrame(data)


def get_proficiency_level(score):
    """Convert numeric score to proficiency level"""
    if score >= 2.5:
        return 'Advanced'
    elif score >= 1.5:
        return 'Intermediate'
    elif score >= 0.5:
        return 'Basic'
    else:
        return 'None'


def print_assignment_summary(session, employee):
    """Print employee assignment summary to console"""
    print(f"\n{'=' * 60}")
    print(f"EMPLOYEE SKILLS & ASSIGNMENTS SUMMARY")
    print(f"{'=' * 60}")
    print(f"Employee: {employee['name']}")
    print(f"ID: {employee['employee_id']}")
    print(f"Type: {employee['employee_type']}")
    print(f"Status: {employee['status']}")

    # Get competency counts
    comp_query = text("""
                      SELECT COUNT(*)                                                         as total_competencies,
                             COUNT(CASE WHEN ec.status = 'Active' THEN 1 END)                 as active_competencies,
                             COUNT(CASE WHEN ec.proficiency_achieved = 'Advanced' THEN 1 END) as advanced_count
                      FROM employee_competencies ec
                      WHERE ec.employee_id = :emp_id
                      """)

    comp_result = session.execute(comp_query, {'emp_id': employee['id']}).fetchone()

    # Get task assignment counts
    task_query = text("""
                      SELECT COUNT(DISTINCT ct.id)                                                          as total_assigned_tasks,
                             COUNT(DISTINCT CASE
                                                WHEN etp.completion_status = 'Complete'
                                                    THEN ct.id END)                                         as completed_tasks,
                             COUNT(DISTINCT CASE
                                                WHEN etp.completion_status = 'In Progress'
                                                    THEN ct.id END)                                         as in_progress_tasks
                      FROM checklist_tasks ct
                               LEFT JOIN task_skill_assignment tsa ON ct.id = tsa.checklist_task_id
                               LEFT JOIN employee_task_progress etp
                                         ON ct.id = etp.checklist_task_id AND etp.employee_id = :emp_id
                      WHERE tsa.checklist_task_id IS NOT NULL
                         OR ct.id IN (SELECT ctc.checklist_task_id
                                      FROM checklist_task_competencies ctc
                                               JOIN employee_competencies ec ON ctc.competency_id = ec.competency_id
                                      WHERE ec.employee_id = :emp_id)
                      """)

    task_result = session.execute(task_query, {'emp_id': employee['id']}).fetchone()

    print(f"\n📊 COMPETENCY SUMMARY:")
    print(f"Total Competencies: {comp_result[0]}")
    print(f"Active Competencies: {comp_result[1]}")
    print(f"Advanced Level: {comp_result[2]}")

    print(f"\n📋 TASK ASSIGNMENT SUMMARY:")
    print(f"Total Assigned Tasks: {task_result[0] or 0}")
    print(f"Completed Tasks: {task_result[1] or 0}")
    print(f"In Progress Tasks: {task_result[2] or 0}")

    if task_result[0] and task_result[0] > 0:
        completion_rate = round((task_result[1] / task_result[0]) * 100, 1)
        print(f"Task Completion Rate: {completion_rate}%")

    print(f"{'=' * 60}")


def list_all_employees(session):
    """List all employees for selection"""
    query = text("""
                 SELECT id, employee_id, name_first, name_last, employee_type, status
                 FROM employees
                 ORDER BY name_last, name_first
                 """)

    result = session.execute(query)
    employees = []

    print("\nAvailable Employees:")
    print("-" * 50)

    for row in result.fetchall():
        employee_info = f"{row[2]} {row[3]} (ID: {row[1]}) - {row[4]} - {row[5]}"
        print(f"  {employee_info}")
        employees.append({
            'id': row[0],
            'employee_id': row[1],
            'name': f"{row[2]} {row[3]}",
            'type': row[4],
            'status': row[5]
        })

    return employees


def generate_all_employee_reports(session):
    """Generate individual reports for all employees plus a master summary"""
    print("🚀 Generating reports for ALL employees...")

    # Get all employees
    query = text("""
                 SELECT id, employee_id, name_first, name_last, employee_type, status
                 FROM employees
                 WHERE status = 'Active'
                 ORDER BY name_last, name_first
                 """)

    result = session.execute(query)
    employees = []

    for row in result.fetchall():
        employees.append({
            'id': row[0],
            'employee_id': row[1],
            'name_first': row[2],
            'name_last': row[3],
            'name': f"{row[2]} {row[3]}",
            'employee_type': row[4],
            'status': row[5]
        })

    if not employees:
        print("❌ No active employees found!")
        return

    print(f"📊 Found {len(employees)} active employees")

    # Create a directory for all reports
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = f"All_Employee_Reports_{timestamp}"
    print(f"📁 Creating reports directory: {reports_dir}")

    # ✅ Actually create it
    try:
        os.makedirs(reports_dir, exist_ok=True)
    except Exception as e:
        print(f"❌ Failed to create reports directory '{reports_dir}': {e}")
        return

    # Track summary data
    all_employee_data = []
    successful_reports = 0
    failed_reports = 0

    # Generate individual reports
    print("\n🔄 Generating individual employee reports...")
    for i, employee in enumerate(employees, 1):
        try:
            print(f"  [{i}/{len(employees)}] Processing: {employee['name']} (ID: {employee['employee_id']})")

            # Ensure parent directory exists (defensive)
            os.makedirs(reports_dir, exist_ok=True)

            # Generate individual report
            report_path = generate_individual_employee_report(session, employee, reports_dir)

            if report_path:
                # Collect summary data
                summary_data = get_employee_summary_data(session, employee)
                all_employee_data.append(summary_data)
                successful_reports += 1
                print(f"    ✅ Success")
            else:
                failed_reports += 1
                print(f"    ❌ Failed")

        except Exception as e:
            failed_reports += 1
            print(f"    ❌ Error: {str(e)}")

    # Generate master summary report
    print("\n📋 Creating master summary report...")
    master_summary_path = create_master_summary_report(all_employee_data, reports_dir, timestamp)

    # Print final summary
    print(f"\n{'=' * 60}")
    print(f"ALL EMPLOYEE REPORTS GENERATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"📁 Reports Directory: {reports_dir}")
    print(f"✅ Successful Reports: {successful_reports}")
    print(f"❌ Failed Reports: {failed_reports}")
    print(f"📊 Master Summary: {master_summary_path}")
    print(f"{'=' * 60}")


def generate_individual_employee_report(session, employee, reports_dir):
    """Generate individual employee report in specified directory"""
    try:
        # Create filename
        safe_name = employee['name'].replace(' ', '_').replace(',', '')
        filename = f"Employee_Skills_{safe_name}_{employee['employee_id']}.xlsx"
        filepath = os.path.join(reports_dir, filename)

        # ✅ Ensure directory exists
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        # Create Excel writer object
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:

            # 1. Employee Information Sheet
            employee_info_df = create_employee_info_sheet(session, employee)
            employee_info_df.to_excel(writer, sheet_name='Employee_Info', index=False)

            # 2. Current Competencies
            current_comp_df = create_current_competencies_sheet(session, employee['id'])
            current_comp_df.to_excel(writer, sheet_name='Current_Competencies', index=False)

            # 3. Task Progress
            task_progress_df = create_task_progress_sheet(session, employee['id'])
            task_progress_df.to_excel(writer, sheet_name='Task_Progress', index=False)

            # 4. Required Competencies
            required_comp_df = create_required_competencies_sheet(session, employee)
            required_comp_df.to_excel(writer, sheet_name='Required_Competencies', index=False)

            # 5. Skills Gap Analysis
            gap_analysis_df = create_skills_gap_analysis(session, employee['id'])
            gap_analysis_df.to_excel(writer, sheet_name='Skills_Gap_Analysis', index=False)

            # 6. Assigned Tasks
            assigned_tasks_df = create_assigned_tasks_sheet(session, employee['id'])
            assigned_tasks_df.to_excel(writer, sheet_name='Assigned_Tasks', index=False)

            # 7. Competency Assignments
            competency_assignments_df = create_competency_assignments_sheet(session, employee['id'])
            competency_assignments_df.to_excel(writer, sheet_name='Competency_Assignments', index=False)

            # 8. Competency Summary
            summary_df = create_employee_competency_summary(session, employee['id'])
            summary_df.to_excel(writer, sheet_name='Competency_Summary', index=False)

        return filepath

    except Exception as e:
        print(f"      Error creating report: {e}")
        return None


def get_employee_summary_data(session, employee):
    """Get summary data for an employee for the master report"""
    try:
        # Get competency counts
        comp_query = text("""
                          SELECT COUNT(*)                                                             as total_competencies,
                                 COUNT(CASE WHEN ec.status = 'Active' THEN 1 END)                     as active_competencies,
                                 COUNT(CASE WHEN ec.proficiency_achieved = 'Basic' THEN 1 END)        as basic_count,
                                 COUNT(CASE WHEN ec.proficiency_achieved = 'Intermediate' THEN 1 END) as intermediate_count,
                                 COUNT(CASE WHEN ec.proficiency_achieved = 'Advanced' THEN 1 END)     as advanced_count
                          FROM employee_competencies ec
                          WHERE ec.employee_id = :emp_id
                          """)

        comp_result = session.execute(comp_query, {'emp_id': employee['id']}).fetchone()

        # Get task assignment counts
        task_query = text("""
                          SELECT COUNT(DISTINCT ct.id)                                                          as total_assigned_tasks,
                                 COUNT(DISTINCT CASE
                                                    WHEN etp.completion_status = 'Complete'
                                                        THEN ct.id END)                                         as completed_tasks,
                                 COUNT(DISTINCT CASE
                                                    WHEN etp.completion_status = 'In Progress'
                                                        THEN ct.id END)                                         as in_progress_tasks
                          FROM checklist_tasks ct
                                   LEFT JOIN task_skill_assignment tsa ON ct.id = tsa.checklist_task_id
                                   LEFT JOIN employee_task_progress etp
                                             ON ct.id = etp.checklist_task_id AND etp.employee_id = :emp_id
                          WHERE tsa.checklist_task_id IS NOT NULL
                             OR ct.id IN (SELECT ctc.checklist_task_id
                                          FROM checklist_task_competencies ctc
                                                   JOIN employee_competencies ec ON ctc.competency_id = ec.competency_id
                                          WHERE ec.employee_id = :emp_id)
                          """)

        task_result = session.execute(task_query, {'emp_id': employee['id']}).fetchone()

        # Calculate completion rate
        completion_rate = 0
        if task_result[0] and task_result[0] > 0:
            completion_rate = round((task_result[1] / task_result[0]) * 100, 1)

        return {
            'Employee_ID': employee['employee_id'],
            'Employee_Name': employee['name'],
            'First_Name': employee['name_first'],
            'Last_Name': employee['name_last'],
            'Employee_Type': employee['employee_type'],
            'Status': employee['status'],
            'Total_Competencies': comp_result[0] or 0,
            'Active_Competencies': comp_result[1] or 0,
            'Basic_Level': comp_result[2] or 0,
            'Intermediate_Level': comp_result[3] or 0,
            'Advanced_Level': comp_result[4] or 0,
            'Total_Assigned_Tasks': task_result[0] or 0,
            'Completed_Tasks': task_result[1] or 0,
            'In_Progress_Tasks': task_result[2] or 0,
            'Task_Completion_Rate': f"{completion_rate}%"
        }

    except Exception as e:
        print(f"      Error getting summary data: {e}")
        return {
            'Employee_ID': employee['employee_id'],
            'Employee_Name': employee['name'],
            'First_Name': employee['name_first'],
            'Last_Name': employee['name_last'],
            'Employee_Type': employee['employee_type'],
            'Status': employee['status'],
            'Total_Competencies': 0,
            'Active_Competencies': 0,
            'Basic_Level': 0,
            'Intermediate_Level': 0,
            'Advanced_Level': 0,
            'Total_Assigned_Tasks': 0,
            'Completed_Tasks': 0,
            'In_Progress_Tasks': 0,
            'Task_Completion_Rate': '0%'
        }


def create_master_summary_report(all_employee_data, reports_dir, timestamp):
    """Create master summary report with all employee data"""
    try:
        filename = f"MASTER_Employee_Skills_Summary_{timestamp}.xlsx"
        filepath = os.path.join(reports_dir, filename)

        # ✅ Ensure directory exists
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)

        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:

            # 1. All Employees Summary
            if all_employee_data:
                employees_df = pd.DataFrame(all_employee_data)
                employees_df.to_excel(writer, sheet_name='All_Employees_Summary', index=False)

            # 2. Department/Type Summary
            if all_employee_data:
                dept_summary = create_department_summary(all_employee_data)
                dept_summary.to_excel(writer, sheet_name='Department_Summary', index=False)

            # 3. Skills Coverage Analysis
            if all_employee_data:
                skills_coverage = create_skills_coverage_analysis(all_employee_data)
                skills_coverage.to_excel(writer, sheet_name='Skills_Coverage', index=False)

            # 4. Top Performers
            if all_employee_data:
                top_performers = create_top_performers_analysis(all_employee_data)
                top_performers.to_excel(writer, sheet_name='Top_Performers', index=False)

        return filepath

    except Exception as e:
        print(f"Error creating master summary: {e}")
        return None


def create_department_summary(all_employee_data):
    """Create summary by employee type/department"""
    df = pd.DataFrame(all_employee_data)

    summary = df.groupby('Employee_Type').agg({
        'Employee_ID': 'count',
        'Total_Competencies': 'mean',
        'Active_Competencies': 'mean',
        'Basic_Level': 'sum',
        'Intermediate_Level': 'sum',
        'Advanced_Level': 'sum',
        'Total_Assigned_Tasks': 'sum',
        'Completed_Tasks': 'sum'
    }).round(1)

    summary.columns = [
        'Employee_Count',
        'Avg_Total_Competencies',
        'Avg_Active_Competencies',
        'Total_Basic_Skills',
        'Total_Intermediate_Skills',
        'Total_Advanced_Skills',
        'Total_Assigned_Tasks',
        'Total_Completed_Tasks'
    ]

    # Calculate completion rate by department
    summary['Dept_Task_Completion_Rate'] = (
        summary['Total_Completed_Tasks'] / summary['Total_Assigned_Tasks'] * 100
    ).round(1).fillna(0).astype(str) + '%'

    summary = summary.reset_index()
    return summary


def create_skills_coverage_analysis(all_employee_data):
    """Create skills coverage analysis"""
    df = pd.DataFrame(all_employee_data)

    total_employees = len(df)

    analysis = []
    analysis.append({
        'Metric': 'Total Active Employees',
        'Value': total_employees,
        'Percentage': '100%'
    })

    analysis.append({
        'Metric': 'Employees with Competencies',
        'Value': len(df[df['Total_Competencies'] > 0]),
        'Percentage': f"{len(df[df['Total_Competencies'] > 0]) / total_employees * 100:.1f}%"
    })

    analysis.append({
        'Metric': 'Employees with Advanced Skills',
        'Value': len(df[df['Advanced_Level'] > 0]),
        'Percentage': f"{len(df[df['Advanced_Level'] > 0]) / total_employees * 100:.1f}%"
    })

    analysis.append({
        'Metric': 'Employees with Assigned Tasks',
        'Value': len(df[df['Total_Assigned_Tasks'] > 0]),
        'Percentage': f"{len(df[df['Total_Assigned_Tasks'] > 0]) / total_employees * 100:.1f}%"
    })

    analysis.append({
        'Metric': 'Employees with 100% Task Completion',
        'Value': len(df[df['Task_Completion_Rate'] == '100.0%']),
        'Percentage': f"{len(df[df['Task_Completion_Rate'] == '100.0%']) / total_employees * 100:.1f}%"
    })

    return pd.DataFrame(analysis)


def create_top_performers_analysis(all_employee_data):
    """Create top performers analysis"""
    df = pd.DataFrame(all_employee_data)

    # Convert completion rate back to numeric for sorting
    df['Completion_Rate_Numeric'] = df['Task_Completion_Rate'].str.rstrip('%').astype(float)

    # Top performers by different metrics
    top_performers = []

    # Top 10 by total competencies
    top_competencies = df.nlargest(10, 'Total_Competencies')[
        ['Employee_Name', 'Employee_Type', 'Total_Competencies']
    ].copy()
    top_competencies['Ranking_Category'] = 'Top Total Competencies'
    top_competencies['Rank'] = range(1, len(top_competencies) + 1)
    top_performers.append(top_competencies)

    # Top 10 by advanced skills
    top_advanced = df.nlargest(10, 'Advanced_Level')[
        ['Employee_Name', 'Employee_Type', 'Advanced_Level']
    ].copy()
    top_advanced['Ranking_Category'] = 'Top Advanced Skills'
    top_advanced['Rank'] = range(1, len(top_advanced) + 1)
    top_performers.append(top_advanced)

    # Top 10 by task completion rate
    top_completion = df.nlargest(10, 'Completion_Rate_Numeric')[
        ['Employee_Name', 'Employee_Type', 'Task_Completion_Rate']
    ].copy()
    top_completion['Ranking_Category'] = 'Top Task Completion'
    top_completion['Rank'] = range(1, len(top_completion) + 1)
    top_performers.append(top_completion)

    # Combine all rankings
    combined_df = pd.concat(top_performers, ignore_index=True)

    return combined_df


def main():
    """Main function to run the employee skills export"""
    engine = create_engine(r'sqlite:///C:\Users\10169062\PycharmProjects\pythonProject2\database\maintenance_skills.db')
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("🔍 Employee Skills Report Generator")
        print("=" * 40)

        # Option 1: List all employees
        print("\n1. List all employees")
        print("2. Search by employee ID")
        print("3. Search by employee name")
        print("4. Generate reports for ALL employees")

        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == '1':
            employees = list_all_employees(session)
            if employees:
                emp_input = input("\nEnter employee ID to generate report: ").strip()
                export_employee_skills_to_excel(employee_id=emp_input)

        elif choice == '2':
            emp_id = input("Enter employee ID: ").strip()
            export_employee_skills_to_excel(employee_id=emp_id)

        elif choice == '3':
            emp_name = input("Enter employee name (first, last, or full): ").strip()
            export_employee_skills_to_excel(employee_name=emp_name)

        elif choice == '4':
            generate_all_employee_reports(session)

        else:
            print("Invalid choice!")

    finally:
        session.close()


if __name__ == "__main__":
    try:
        main()
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
