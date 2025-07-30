from sqlalchemy.ext.declarative import declarative_base
from datetime import time, datetime
from sqlalchemy.orm import relationship, backref
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Time, Date, Numeric, func
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
    proficiency_level = Column(String)  # A,B and C Ex: Level_1_A, Level_2_B

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


class Shift(Base):
    __tablename__ = "shifts"
    id = Column(Integer, primary_key=True)
    shift_name = Column(String, nullable=False)
    description = Column(String)
    is_active = Column(Boolean, default=True)

    # ADD THIS NEW FIELD:
    shift_pattern = Column(String, default='weekly')  # 'weekly' or 'biweekly'

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    shift_days = relationship("ShiftDay", back_populates="shift", cascade="all, delete-orphan")
    schedules = relationship("EmployeeSchedule", back_populates="shift")


class ShiftDay(Base):
    __tablename__ = "shift_days"
    id = Column(Integer, primary_key=True)
    shift_id = Column(Integer, ForeignKey('shifts.id'), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Sunday, 1=Monday, ..., 6=Saturday

    # ADD THIS NEW FIELD:
    week_number = Column(Integer, default=1)  # 1 or 2 for bi-weekly patterns (1=first week, 2=second week)

    scheduled_start_time = Column(Time, nullable=False)
    scheduled_end_time = Column(Time, nullable=False)

    # Relationships
    shift = relationship("Shift", back_populates="shift_days")


from datetime import date
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, or_


class EmployeeSchedule(Base):
    __tablename__ = "employee_schedules"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    shift_id = Column(Integer, ForeignKey('shifts.id'), nullable=False)

    # Date range for this schedule assignment
    effective_start_date = Column(Date, nullable=False)
    effective_end_date = Column(Date)  # NULL means ongoing

    is_active = Column(Boolean, default=True)
    notes = Column(String)  # "Temporary assignment", "Training period", etc.

    # Relationships
    employee = relationship("Employee")
    shift = relationship("Shift", back_populates="schedules")
    attendance_records = relationship("AttendanceRecord", back_populates="schedule")

    @classmethod
    def get_current_schedule(cls, session, employee_id, as_of_date=None):
        """
        Get the current active schedule for an employee

        Args:
            session: SQLAlchemy session
            employee_id: ID of the employee
            as_of_date: Date to check (defaults to today)

        Returns:
            EmployeeSchedule object or None
        """
        if as_of_date is None:
            as_of_date = date.today()

        return session.query(cls).filter(
            cls.employee_id == employee_id,
            cls.is_active == True,
            cls.effective_start_date <= as_of_date,
            or_(
                cls.effective_end_date.is_(None),
                cls.effective_end_date >= as_of_date
            )
        ).first()

    @classmethod
    def assign_shift(cls, session, employee_id, shift_id, start_date=None, end_current=True, notes=None):
        """
        Assign a shift to an employee

        Args:
            session: SQLAlchemy session
            employee_id: ID of the employee
            shift_id: ID of the shift to assign
            start_date: When the assignment starts (defaults to today)
            end_current: Whether to end current active assignments (default True)
            notes: Optional notes for the assignment

        Returns:
            New EmployeeSchedule object
        """
        if start_date is None:
            start_date = date.today()

        # End current assignments if requested
        if end_current:
            cls.end_current_assignments(session, employee_id, start_date)

        # Create new assignment
        new_schedule = cls(
            employee_id=employee_id,
            shift_id=shift_id,
            effective_start_date=start_date,
            effective_end_date=None,
            is_active=True,
            notes=notes
        )

        session.add(new_schedule)
        return new_schedule

    @classmethod
    def end_current_assignments(cls, session, employee_id, end_date=None):
        """
        End all current active assignments for an employee

        Args:
            session: SQLAlchemy session
            employee_id: ID of the employee
            end_date: Date to end assignments (defaults to today)

        Returns:
            Number of assignments ended
        """
        if end_date is None:
            end_date = date.today()

        current_assignments = session.query(cls).filter(
            cls.employee_id == employee_id,
            cls.is_active == True,
            or_(
                cls.effective_end_date.is_(None),
                cls.effective_end_date >= end_date
            )
        ).all()

        count = 0
        for assignment in current_assignments:
            assignment.effective_end_date = end_date
            assignment.is_active = False
            count += 1

        return count

    @classmethod
    def get_employee_schedule_history(cls, session, employee_id, include_inactive=False):
        """
        Get all schedule assignments for an employee

        Args:
            session: SQLAlchemy session
            employee_id: ID of the employee
            include_inactive: Whether to include inactive assignments

        Returns:
            List of EmployeeSchedule objects ordered by start date
        """
        query = session.query(cls).filter(cls.employee_id == employee_id)

        if not include_inactive:
            query = query.filter(cls.is_active == True)

        return query.order_by(cls.effective_start_date.desc()).all()

    @classmethod
    def get_shift_assignments(cls, session, shift_id, active_only=True, as_of_date=None):
        """
        Get all employees assigned to a specific shift

        Args:
            session: SQLAlchemy session
            shift_id: ID of the shift
            active_only: Whether to only return active assignments
            as_of_date: Date to check assignments for (defaults to today)

        Returns:
            List of EmployeeSchedule objects
        """
        if as_of_date is None:
            as_of_date = date.today()

        query = session.query(cls).filter(cls.shift_id == shift_id)

        if active_only:
            query = query.filter(
                cls.is_active == True,
                cls.effective_start_date <= as_of_date,
                or_(
                    cls.effective_end_date.is_(None),
                    cls.effective_end_date >= as_of_date
                )
            )

        return query.all()

    @classmethod
    def update_assignment(cls, session, schedule_id, shift_id=None, start_date=None,
                          end_date=None, is_active=None, notes=None):
        """
        Update an existing schedule assignment

        Args:
            session: SQLAlchemy session
            schedule_id: ID of the schedule to update
            shift_id: New shift ID (optional)
            start_date: New start date (optional)
            end_date: New end date (optional)
            is_active: New active status (optional)
            notes: New notes (optional)

        Returns:
            Updated EmployeeSchedule object or None if not found
        """
        schedule = session.get(cls, schedule_id)
        if not schedule:
            return None

        if shift_id is not None:
            schedule.shift_id = shift_id
        if start_date is not None:
            schedule.effective_start_date = start_date
        if end_date is not None:
            schedule.effective_end_date = end_date
        if is_active is not None:
            schedule.is_active = is_active
        if notes is not None:
            schedule.notes = notes

        return schedule

    @classmethod
    def has_schedule_conflict(cls, session, employee_id, start_date, end_date=None, exclude_schedule_id=None):
        """
        Check if a schedule assignment would conflict with existing assignments

        Args:
            session: SQLAlchemy session
            employee_id: ID of the employee
            start_date: Start date of proposed assignment
            end_date: End date of proposed assignment (None for ongoing)
            exclude_schedule_id: Schedule ID to exclude from conflict check (for updates)

        Returns:
            True if there's a conflict, False otherwise
        """
        query = session.query(cls).filter(
            cls.employee_id == employee_id,
            cls.is_active == True
        )

        if exclude_schedule_id:
            query = query.filter(cls.id != exclude_schedule_id)

        # Check for overlapping date ranges
        if end_date is None:
            # New assignment is ongoing, check if it overlaps with any existing
            query = query.filter(
                or_(
                    cls.effective_end_date.is_(None),
                    cls.effective_end_date >= start_date
                )
            )
        else:
            # New assignment has an end date
            query = query.filter(
                cls.effective_start_date <= end_date,
                or_(
                    cls.effective_end_date.is_(None),
                    cls.effective_end_date >= start_date
                )
            )

        return query.count() > 0

    def is_current(self, as_of_date=None):
        """
        Check if this schedule assignment is current

        Args:
            as_of_date: Date to check against (defaults to today)

        Returns:
            True if the assignment is current, False otherwise
        """
        if as_of_date is None:
            as_of_date = date.today()

        return (
                self.is_active and
                self.effective_start_date <= as_of_date and
                (self.effective_end_date is None or self.effective_end_date >= as_of_date)
        )

    def get_duration_days(self):
        """
        Get the duration of this assignment in days

        Returns:
            Number of days or None if ongoing
        """
        if self.effective_end_date is None:
            return None

        return (self.effective_end_date - self.effective_start_date).days + 1

    def __str__(self):
        """String representation of the schedule assignment"""
        end_str = self.effective_end_date.strftime('%Y-%m-%d') if self.effective_end_date else 'Ongoing'
        return f"Employee {self.employee_id} -> Shift {self.shift_id} ({self.effective_start_date} to {end_str})"

    def __repr__(self):
        """Developer representation of the schedule assignment"""
        return f"<EmployeeSchedule(id={self.id}, employee_id={self.employee_id}, shift_id={self.shift_id}, active={self.is_active})>"


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    id = Column(Integer, primary_key=True)
    schedule_id = Column(Integer, ForeignKey('employee_schedules.id'), nullable=False)
    work_date = Column(Date, nullable=False)  # The specific date being tracked
    day_of_week = Column(Integer, nullable=False)  # 0=Sunday, 1=Monday, etc.

    # Scheduled times for this specific day (copied from ShiftDay for historical record)
    scheduled_start_time = Column(Time, nullable=False)
    scheduled_end_time = Column(Time, nullable=False)

    # Actual clock in/out times
    actual_clock_in = Column(DateTime)
    actual_clock_out = Column(DateTime)

    # Calculated fields (could be computed properties or stored)
    minutes_late = Column(Integer, default=0)  # Positive if late
    minutes_early_out = Column(Integer, default=0)  # Positive if left early
    total_hours_worked = Column(Numeric(4, 2))  # 8.50 hours

    # Status tracking
    attendance_status = Column(String)  # "Present", "Late", "Early Out", "Absent", "Partial"

    # Optional: who recorded the attendance (if manual entry)
    recorded_by = Column(Integer, ForeignKey('employees.id'))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    notes = Column(String)  # "Equipment malfunction", "Approved late arrival", etc.

    # Relationships
    schedule = relationship("EmployeeSchedule", back_populates="attendance_records")
    recorder = relationship("Employee", foreign_keys=[recorded_by])

# Optional: For tracking attendance issues/patterns
class AttendanceIssue(Base):
    __tablename__ = "attendance_issues"
    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    issue_date = Column(Date, nullable=False)
    issue_type = Column(String, nullable=False)  # "Late Arrival", "Early Departure", "No Show"
    severity = Column(String)  # "Minor", "Major", "Critical"

    # Reference to the attendance record that triggered this
    attendance_record_id = Column(Integer, ForeignKey('attendance_records.id'))

    # Supervisor actions
    supervisor_notified = Column(Boolean, default=False)
    action_taken = Column(String)  # "Verbal Warning", "Written Warning", "PIP"
    resolved = Column(Boolean, default=False)
    resolution_notes = Column(String)

    created_at = Column(DateTime, default=func.now())

    # Relationships
    employee = relationship("Employee")
    attendance_record = relationship("AttendanceRecord")
