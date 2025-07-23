from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

# Create the base class
Base = declarative_base()


class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True)
    employee_id = Column(String, unique=True, nullable=False)
    name_first = Column(String)
    name_last = Column(String)
    hire_date = Column(String)
    birthdate = Column(String)
    status = Column(String)
    employee_type = Column(String)  # For polymorphic identity
    reports_to_id = Column(Integer, ForeignKey('employees.id'))

    reports_to = relationship("Employee", remote_side=[id], backref="direct_reports")
    # FIXED: Specify foreign_keys to resolve ambiguity
    competencies = relationship("EmployeeCompetency", back_populates="employee", foreign_keys="EmployeeCompetency.employee_id")


class MaintenancePerson(Employee):
    __tablename__ = "maintenance_persons"
    id = Column(Integer, ForeignKey('employees.id'), primary_key=True)
    maintenance_level = Column(String)
    qualified_area = Column(String)

    __mapper_args__ = {'polymorphic_identity': 'maintenance'}


class Supervisor(Employee):
    __tablename__ = "supervisors"
    id = Column(Integer, ForeignKey('employees.id'), primary_key=True)
    management_level = Column(Integer)

    __mapper_args__ = {'polymorphic_identity': 'supervisor'}


class CoreCompetency(Base):
    __tablename__ = "core_competencies"
    id = Column(Integer, primary_key=True)
    competency_name = Column(String, nullable=True)
    description = Column(String)
    competency_type = Column(String)  # For polymorphic identity
    level = Column(String, nullable=True)

    # Level requirements - inherited by all subclasses
    required_for_level_1 = Column(Boolean, default=False)
    required_for_level_2 = Column(Boolean, default=False)
    required_for_level_3 = Column(Boolean, default=False)
    required_for_maintenance_tech = Column(Boolean, default=False)
    proficiency_level = Column(String)  # Basic, Intermediate, Advanced

    # CRITICAL: Add polymorphic configuration
    __mapper_args__ = {
        'polymorphic_identity': 'core',
        'polymorphic_on': competency_type
    }

    # Relationship to track which employees have this competency
    employee_records = relationship("EmployeeCompetency", back_populates="competency")


# Junction table to track employee competencies
class EmployeeCompetency(Base):
    __tablename__ = "employee_competencies"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'))
    competency_id = Column(Integer, ForeignKey('core_competencies.id'))
    proficiency_achieved = Column(String)  # Basic, Intermediate, Advanced
    level_achieved = Column(String)
    date_achieved = Column(String)
    assessed_by = Column(Integer, ForeignKey('employees.id'))  # Who assessed them
    status = Column(String)  # Active, Expired, Needs Renewal
    notes = Column(String)  # Additional assessment notes

    # FIXED: Specify foreign_keys for each relationship
    employee = relationship("Employee", back_populates="competencies", foreign_keys=[employee_id])
    competency = relationship("CoreCompetency", back_populates="employee_records")
    assessor = relationship("Employee", foreign_keys=[assessed_by])


class EmployeeTaskProgress(Base):
    __tablename__ = "employee_task_progress"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'))
    checklist_task_id = Column(Integer, ForeignKey('checklist_tasks.id'))
    competency_id = Column(Integer, ForeignKey('core_competencies.id'))  # Optional, for reference
    completion_status = Column(String)  # e.g., "Not Started", "In Progress", "Complete"
    completion_date = Column(String)    # Date when marked complete
    notes = Column(String)

    employee = relationship("Employee")
    task = relationship("ChecklistTask")
    competency = relationship("CoreCompetency")

    # Optional: composite unique constraint
    # __table_args__ = (UniqueConstraint('employee_id', 'checklist_task_id', name='_employee_task_uc'),)


class AcademicCompetency(CoreCompetency):
    __tablename__ = "academic_competencies"
    id = Column(Integer, ForeignKey('core_competencies.id'), primary_key=True)
    subject_area = Column(String)  # Math, Reading, Writing, Physics, Chemistry
    academic_level = Column(String)  # High School, College, Advanced
    external_source = Column(String)  # LMS name, Institution, Certification Body
    credential_type = Column(String)  # Course Completion, Certification, Degree

    __mapper_args__ = {'polymorphic_identity': 'academic'}


class AcademicTask(AcademicCompetency):
    __tablename__ = "academic_tasks"
    id = Column(Integer, ForeignKey('academic_competencies.id'), primary_key=True)
    skill_operation = Column(String)  # "Add", "Subtract", "Multiply", "Divide", "Solve", "Graph"
    skill_concept = Column(String)  # "Whole Numbers", "Fractions", "Equations", "Functions"
    verification_method = Column(String)  # "Problem solving test", "Demonstration", "Quiz score"
    prerequisite_skills = Column(String)  # "Addition, Subtraction" (comma-separated)

    __mapper_args__ = {'polymorphic_identity': 'academic_task'}


class SafetyCompetency(CoreCompetency):
    __tablename__ = "safety_competencies"
    id = Column(Integer, ForeignKey('core_competencies.id'), primary_key=True)
    safety_category = Column(String)  # PPE, LOTO, Hazard Recognition, Emergency Response
    safety_domain = Column(String)  # Electrical, Mechanical, Chemical, General
    regulatory_source = Column(String)  # OSHA, NFPA, Company Policy

    __mapper_args__ = {'polymorphic_identity': 'safety'}


class SafetyTask(SafetyCompetency):
    __tablename__ = "safety_tasks"
    id = Column(Integer, ForeignKey('safety_competencies.id'), primary_key=True)
    safety_action = Column(String)  # "Inspect", "Don", "Remove", "Test", "Isolate", "Verify"
    safety_object = Column(String)  # "Hard Hat", "Energy Source", "Hazard", "Equipment"
    verification_method = Column(String)  # "Visual check", "Functional test", "Demonstration"
    compliance_standard = Column(String)  # "29 CFR 1910.147", "Company SOP-123"

    __mapper_args__ = {'polymorphic_identity': 'safety_task'}


class LeadershipCompetency(CoreCompetency):
    __tablename__ = "leadership_competencies"
    id = Column(Integer, ForeignKey('core_competencies.id'), primary_key=True)
    leadership_type = Column(String)  # Team Direction, Conflict Resolution, Decision Making
    leadership_scope = Column(String)  # Individual, Team, Department, Organization

    __mapper_args__ = {'polymorphic_identity': 'leadership'}


class LeadershipTask(LeadershipCompetency):
    __tablename__ = "leadership_tasks"
    id = Column(Integer, ForeignKey('leadership_competencies.id'), primary_key=True)
    leadership_action = Column(String)  # "Facilitate", "Resolve", "Delegate", "Coach", "Decide"
    leadership_object = Column(String)  # "Meeting", "Conflict", "Task", "Team Member", "Problem"
    verification_method = Column(String)  # "Peer feedback", "Outcome assessment", "360 review"

    __mapper_args__ = {'polymorphic_identity': 'leadership_task'}


class CommunicationCompetency(CoreCompetency):
    __tablename__ = "communication_competencies"
    id = Column(Integer, ForeignKey('core_competencies.id'), primary_key=True)
    communication_method = Column(String)  # Verbal, Written, Technical, Presentation
    communication_audience = Column(String)  # Peer, Supervisor, Team, Customer, Executive

    __mapper_args__ = {'polymorphic_identity': 'communication'}


class CommunicationTask(CommunicationCompetency):
    __tablename__ = "communication_tasks"
    id = Column(Integer, ForeignKey('communication_competencies.id'), primary_key=True)
    communication_action = Column(String)  # "Present", "Write", "Listen", "Explain", "Document"
    communication_object = Column(String)  # "Report", "Instructions", "Feedback", "Procedure"
    verification_method = Column(String)  # "Audience comprehension", "Document review", "Feedback"

    __mapper_args__ = {'polymorphic_identity': 'communication_task'}


class TrainingCompetency(CoreCompetency):
    __tablename__ = "training_competencies"
    id = Column(Integer, ForeignKey('core_competencies.id'), primary_key=True)
    training_type = Column(String)  # Mentoring, Knowledge Transfer, Skill Development
    training_method = Column(String)  # One-on-one, Group, Hands-on, Classroom

    __mapper_args__ = {'polymorphic_identity': 'training'}


class TrainingTask(TrainingCompetency):
    __tablename__ = "training_tasks"
    id = Column(Integer, ForeignKey('training_competencies.id'), primary_key=True)
    training_action = Column(String)  # "Teach", "Demonstrate", "Assess", "Guide", "Mentor"
    training_object = Column(String)  # "Skill", "Procedure", "Concept", "Behavior"
    verification_method = Column(String)  # "Student performance", "Skill demonstration", "Assessment"

    __mapper_args__ = {'polymorphic_identity': 'training_task'}


class TechnicalSkill(CoreCompetency):
    __tablename__ = "technical_skills"
    id = Column(Integer, ForeignKey('core_competencies.id'), primary_key=True)
    skill_category = Column(String)  # Electrical, Mechanical, Tools

    __mapper_args__ = {'polymorphic_identity': 'technical'}


class ElectricalSkill(TechnicalSkill):
    __tablename__ = "electrical_skills"
    id = Column(Integer, ForeignKey('technical_skills.id'), primary_key=True)
    sub_category = Column(String)  # "Low/High Voltage Wiring", "Control Circuits & Sensors", "VFDs", "MCC"
    voltage_level = Column(String)  # "Low", "High", "Low/High Voltage"
    electrical_type = Column(String)  # "Wiring", "Control Circuits", "VFDs", "MCC"

    __mapper_args__ = {'polymorphic_identity': 'electrical'}


class ElectricalTask(ElectricalSkill):
    __tablename__ = "electrical_tasks"
    id = Column(Integer, ForeignKey('electrical_skills.id'), primary_key=True)
    task_action = Column(String)
    task_object = Column(String)
    verification_method = Column(String)
    __mapper_args__ = {'polymorphic_identity': 'electrical_task'}
    skill_assignments = relationship("TaskSkillAssignment", back_populates="electrical_task")


class MechanicalSkill(TechnicalSkill):
    __tablename__ = "mechanical_skills"
    id = Column(Integer, ForeignKey('technical_skills.id'), primary_key=True)
    sub_category = Column(String)  # "Hydraulic Systems", "Pneumatic Systems", "Belt/Chain Drive", "Bearing Systems"
    mechanical_type = Column(String)  # "Hydraulic", "Pneumatic", "Belt/Chain", "Bearing", "Pump", "Motor"
    equipment_category = Column(String)  # "Pumps", "Motors", "Conveyor", "Compressors", "Actuators"

    __mapper_args__ = {'polymorphic_identity': 'mechanical'}


class MechanicalTask(MechanicalSkill):
    __tablename__ = "mechanical_tasks"
    id = Column(Integer, ForeignKey('mechanical_skills.id'), primary_key=True)
    task_action = Column(String)
    task_object = Column(String)
    verification_method = Column(String)
    __mapper_args__ = {'polymorphic_identity': 'mechanical_task'}
    skill_assignments = relationship("TaskSkillAssignment", back_populates="mechanical_task")


class ToolSkill(TechnicalSkill):
    __tablename__ = "tool_skills"
    id = Column(Integer, ForeignKey('technical_skills.id'), primary_key=True)
    tool_type = Column(String)  # Hand Tools, Power Tools, Measuring Tools, Test Equipment
    primary_application = Column(String)  # Electrical, Mechanical, Universal

    __mapper_args__ = {'polymorphic_identity': 'tools'}


class ToolTask(ToolSkill):
    __tablename__ = "tool_tasks"
    id = Column(Integer, ForeignKey('tool_skills.id'), primary_key=True)
    task_action = Column(String)
    task_object = Column(String)
    verification_method = Column(String)
    __mapper_args__ = {'polymorphic_identity': 'tool_task'}
    skill_assignments = relationship("TaskSkillAssignment", back_populates="tool_task")

# Checklist System
class AreaChecklist(Base):
    __tablename__ = "area_checklists"
    id = Column(Integer, primary_key=True)
    document_number = Column(String, unique=True)
    description = Column(String)
    area = Column(String)
    version = Column(String)  # For document control
    effective_date = Column(String)

    sections = relationship("ChecklistSection", back_populates="checklist")


class ChecklistSection(Base):
    __tablename__ = "checklist_sections"
    id = Column(Integer, primary_key=True)
    checklist_id = Column(Integer, ForeignKey('area_checklists.id'))
    section_name = Column(String)
    section_order = Column(Integer)  # For ordering sections

    checklist = relationship("AreaChecklist", back_populates="sections")
    tasks = relationship("ChecklistTask", back_populates="section")


class ChecklistTask(Base):
    __tablename__ = "checklist_tasks"
    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey('checklist_sections.id'))
    task_description = Column(String)
    task_order = Column(Integer)
    section = relationship("ChecklistSection", back_populates="tasks")
    required_competencies = relationship("CoreCompetency", secondary="checklist_task_competencies")
    skill_assignments = relationship("TaskSkillAssignment", back_populates="checklist_task")


class TaskSkillAssignment(Base):
    __tablename__ = "task_skill_assignment"
    id = Column(Integer, primary_key=True, autoincrement=True)
    checklist_task_id = Column(Integer, ForeignKey('checklist_tasks.id'), nullable=True)
    mechanical_task_id = Column(Integer, ForeignKey('mechanical_tasks.id'), nullable=True)
    electrical_task_id = Column(Integer, ForeignKey('electrical_tasks.id'), nullable=True)
    tool_task_id = Column(Integer, ForeignKey('tool_tasks.id'), nullable=True)
    operational_task_id = Column(Integer, ForeignKey('operational_tasks.id'), nullable=True)  # NEW

    checklist_task = relationship("ChecklistTask", back_populates="skill_assignments")
    mechanical_task = relationship("MechanicalTask", back_populates="skill_assignments")
    electrical_task = relationship("ElectricalTask", back_populates="skill_assignments")
    tool_task = relationship("ToolTask", back_populates="skill_assignments")
    operational_task = relationship("OperationalTask", back_populates="skill_assignments")  # NEW


class OperationalSkill(CoreCompetency):
    __tablename__ = "operational_skills"
    id = Column(Integer, ForeignKey('core_competencies.id'), primary_key=True)
    operation_type = Column(String)   # e.g., "Manual Mode", "Auto Mode", "Cleaning", "Lubrication"
    machine_type = Column(String)     # e.g., "Bag Sealer", "Conveyor"
    __mapper_args__ = {'polymorphic_identity': 'operational'}

class OperationalTask(OperationalSkill):
    __tablename__ = "operational_tasks"
    id = Column(Integer, ForeignKey('operational_skills.id'), primary_key=True)
    task_action = Column(String)          # e.g., "Operate"
    task_object = Column(String)          # e.g., "Bag Sealer"
    verification_method = Column(String)  # e.g., "Demonstrate operation in manual mode"
    __mapper_args__ = {'polymorphic_identity': 'operational_task'}
    skill_assignments = relationship("TaskSkillAssignment", back_populates="operational_task")


# Junction table for checklist task competencies
class ChecklistTaskCompetency(Base):
    __tablename__ = "checklist_task_competencies"
    checklist_task_id = Column(Integer, ForeignKey('checklist_tasks.id'), primary_key=True)
    competency_id = Column(Integer, ForeignKey('core_competencies.id'), primary_key=True)