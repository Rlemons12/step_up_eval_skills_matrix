"""
Simple SQLAlchemy Models for Task Evaluation Storage and Retrieval
Updated for SQLAlchemy 2.0 compatibility
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func
from datetime import datetime

# Create base class (SQLAlchemy 2.0 style)
Base = declarative_base()

# =====================================================
# SIMPLE REFERENCE TABLES
# =====================================================

class TechnicalDiscipline(Base):
    __tablename__ = 'technical_disciplines'

    discipline_id = Column(Integer, primary_key=True)
    discipline_code = Column(String(1), unique=True, nullable=False)
    discipline_name = Column(String(50), nullable=False)

    def __repr__(self):
        return f"<TechnicalDiscipline({self.discipline_code}: {self.discipline_name})>"

class TaskModifier(Base):
    __tablename__ = 'task_modifiers'

    modifier_id = Column(Integer, primary_key=True)
    modifier_code = Column(String(1), unique=True, nullable=False)
    modifier_name = Column(String(50), nullable=False)

    def __repr__(self):
        return f"<TaskModifier({self.modifier_code}: {self.modifier_name})>"

class EvaluationCriteria(Base):
    __tablename__ = 'evaluation_criteria'

    criteria_id = Column(Integer, primary_key=True)
    criteria_code = Column(String(20), unique=True, nullable=False)
    criteria_name = Column(String(100), nullable=False)

    def __repr__(self):
        return f"<EvaluationCriteria({self.criteria_code}: {self.criteria_name})>"

# =====================================================
# MAIN TASK EVALUATION TABLE
# =====================================================

class TaskEvaluation(Base):
    __tablename__ = 'task_evaluations'

    evaluation_id = Column(Integer, primary_key=True)
    task_name = Column(String(200), nullable=False)
    task_description = Column(Text)
    equipment_system = Column(String(100))
    location = Column(String(100))

    # Technical disciplines (stored as comma-separated codes)
    disciplines = Column(String(50))  # e.g., "E,M,P"
    modifiers = Column(String(50))    # e.g., "A,T"

    # Evaluation scores (1-4 for each criteria)
    technical_score = Column(Integer)
    problem_score = Column(Integer)
    decision_score = Column(Integer)
    impact_score = Column(Integer)
    supervision_score = Column(Integer)
    tools_score = Column(Integer)

    # Calculated results - Using Float instead of Decimal for SQLite compatibility
    overall_score = Column(Float)
    complexity_level = Column(Integer)
    recommended_role = Column(String(50))

    # Additional info
    prerequisites = Column(Text)
    safety_considerations = Column(Text)
    required_tools = Column(Text)
    estimated_time = Column(String(50))
    task_frequency = Column(String(50))
    success_criteria = Column(Text)
    quality_standards = Column(Text)

    # Metadata
    evaluator_name = Column(String(100))
    evaluation_date = Column(DateTime, default=func.now())
    evaluation_notes = Column(Text)

    def calculate_complexity(self):
        """Calculate overall complexity based on scores"""
        scores = [
            self.technical_score,
            self.problem_score,
            self.decision_score,
            self.impact_score,
            self.supervision_score,
            self.tools_score
        ]

        # Remove None values
        valid_scores = [s for s in scores if s is not None]

        if not valid_scores:
            return None

        avg_score = sum(valid_scores) / len(valid_scores)
        # Round to 2 decimal places for consistency
        self.overall_score = round(avg_score, 2)

        # Determine complexity level and recommended role
        if avg_score <= 1.5:
            self.complexity_level = 1
            self.recommended_role = "Mechanic I"
        elif avg_score <= 2.5:
            self.complexity_level = 2
            self.recommended_role = "Mechanic II"
        elif avg_score <= 3.5:
            self.complexity_level = 3
            self.recommended_role = "Mechanic III"
        else:
            self.complexity_level = 4
            self.recommended_role = "Maintenance Technician"

        return self.complexity_level

    def get_disciplines_list(self):
        """Get disciplines as a list"""
        return self.disciplines.split(',') if self.disciplines else []

    def get_modifiers_list(self):
        """Get modifiers as a list"""
        return self.modifiers.split(',') if self.modifiers else []

    def __repr__(self):
        return f"<TaskEvaluation({self.task_name} - Level {self.complexity_level})>"

# =====================================================
# DATABASE MANAGER
# =====================================================

class SimpleTaskEvaluationDB:
    def __init__(self, database_url="sqlite:///task_evaluations.db"):
        # Create engine with updated configuration
        self.engine = create_engine(
            database_url,
            echo=False,
            future=True  # Enable SQLAlchemy 2.0 style
        )
        self.Session = sessionmaker(bind=self.engine)

    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """Get a new database session"""
        return self.Session()

    def setup_reference_data(self):
        """Setup reference data"""
        with self.get_session() as session:
            try:
                # Technical Disciplines
                disciplines = [
                    ('E', 'Electrical'),
                    ('M', 'Mechanical'),
                    ('P', 'Pneumatic'),
                    ('H', 'Hydraulic'),
                    ('C', 'Controls/Programming'),
                    ('I', 'Instrumentation'),
                    ('S', 'Safety Systems'),
                    ('O', 'Operations/Process')
                ]

                for code, name in disciplines:
                    # Check if it already exists
                    existing = session.query(TechnicalDiscipline).filter_by(discipline_code=code).first()
                    if not existing:
                        discipline = TechnicalDiscipline(discipline_code=code, discipline_name=name)
                        session.add(discipline)

                # Task Modifiers
                modifiers = [
                    ('A', 'Alignment'),
                    ('T', 'Troubleshooting'),
                    ('R', 'Repair/Replacement'),
                    ('C', 'Calibration'),
                    ('P', 'Programming'),
                    ('D', 'Documentation')
                ]

                for code, name in modifiers:
                    # Check if it already exists
                    existing = session.query(TaskModifier).filter_by(modifier_code=code).first()
                    if not existing:
                        modifier = TaskModifier(modifier_code=code, modifier_name=name)
                        session.add(modifier)

                # Evaluation Criteria
                criteria = [
                    ('TECH', 'Technical Knowledge'),
                    ('PROB', 'Problem Solving'),
                    ('DECI', 'Decision Making'),
                    ('IMPA', 'Impact of Errors'),
                    ('SUPE', 'Supervision Required'),
                    ('TOOL', 'Tools & Equipment')
                ]

                for code, name in criteria:
                    # Check if it already exists
                    existing = session.query(EvaluationCriteria).filter_by(criteria_code=code).first()
                    if not existing:
                        criterion = EvaluationCriteria(criteria_code=code, criteria_name=name)
                        session.add(criterion)

                session.commit()
                print("Reference data setup complete!")

            except Exception as e:
                session.rollback()
                print(f"Error setting up reference data: {e}")
                raise

    def save_evaluation(self, evaluation_data):
        """Save a task evaluation"""
        with self.get_session() as session:
            try:
                # Create evaluation record
                evaluation = TaskEvaluation(
                    task_name=evaluation_data['task_name'],
                    task_description=evaluation_data.get('task_description'),
                    equipment_system=evaluation_data.get('equipment_system'),
                    location=evaluation_data.get('location'),
                    disciplines=','.join(evaluation_data.get('disciplines', [])),
                    modifiers=','.join(evaluation_data.get('modifiers', [])),
                    technical_score=evaluation_data.get('technical_score'),
                    problem_score=evaluation_data.get('problem_score'),
                    decision_score=evaluation_data.get('decision_score'),
                    impact_score=evaluation_data.get('impact_score'),
                    supervision_score=evaluation_data.get('supervision_score'),
                    tools_score=evaluation_data.get('tools_score'),
                    prerequisites=evaluation_data.get('prerequisites'),
                    safety_considerations=evaluation_data.get('safety_considerations'),
                    required_tools=evaluation_data.get('required_tools'),
                    estimated_time=evaluation_data.get('estimated_time'),
                    task_frequency=evaluation_data.get('task_frequency'),
                    success_criteria=evaluation_data.get('success_criteria'),
                    quality_standards=evaluation_data.get('quality_standards'),
                    evaluator_name=evaluation_data.get('evaluator_name'),
                    evaluation_notes=evaluation_data.get('evaluation_notes')
                )

                # Calculate complexity
                evaluation.calculate_complexity()

                session.add(evaluation)
                session.commit()

                return evaluation.evaluation_id

            except Exception as e:
                session.rollback()
                raise

    def get_evaluation(self, evaluation_id):
        """Get a specific evaluation by ID"""
        with self.get_session() as session:
            try:
                evaluation = session.query(TaskEvaluation).filter_by(evaluation_id=evaluation_id).first()
                if evaluation:
                    return {
                        'evaluation_id': evaluation.evaluation_id,
                        'task_name': evaluation.task_name,
                        'task_description': evaluation.task_description,
                        'equipment_system': evaluation.equipment_system,
                        'location': evaluation.location,
                        'disciplines': evaluation.get_disciplines_list(),
                        'modifiers': evaluation.get_modifiers_list(),
                        'scores': {
                            'technical': evaluation.technical_score,
                            'problem': evaluation.problem_score,
                            'decision': evaluation.decision_score,
                            'impact': evaluation.impact_score,
                            'supervision': evaluation.supervision_score,
                            'tools': evaluation.tools_score
                        },
                        'results': {
                            'overall_score': evaluation.overall_score,
                            'complexity_level': evaluation.complexity_level,
                            'recommended_role': evaluation.recommended_role
                        },
                        'additional_info': {
                            'prerequisites': evaluation.prerequisites,
                            'safety_considerations': evaluation.safety_considerations,
                            'required_tools': evaluation.required_tools,
                            'estimated_time': evaluation.estimated_time,
                            'task_frequency': evaluation.task_frequency,
                            'success_criteria': evaluation.success_criteria,
                            'quality_standards': evaluation.quality_standards
                        },
                        'metadata': {
                            'evaluator_name': evaluation.evaluator_name,
                            'evaluation_date': evaluation.evaluation_date,
                            'evaluation_notes': evaluation.evaluation_notes
                        }
                    }
                return None

            except Exception as e:
                raise

    def search_evaluations(self, search_term=None, complexity_level=None, disciplines=None):
        """Search evaluations"""
        with self.get_session() as session:
            try:
                query = session.query(TaskEvaluation)

                if search_term:
                    query = query.filter(
                        TaskEvaluation.task_name.contains(search_term) |
                        TaskEvaluation.task_description.contains(search_term)
                    )

                if complexity_level:
                    query = query.filter(TaskEvaluation.complexity_level == complexity_level)

                if disciplines:
                    for discipline in disciplines:
                        query = query.filter(TaskEvaluation.disciplines.contains(discipline))

                evaluations = query.order_by(TaskEvaluation.evaluation_date.desc()).all()

                return [
                    {
                        'evaluation_id': eval.evaluation_id,
                        'task_name': eval.task_name,
                        'equipment_system': eval.equipment_system,
                        'complexity_level': eval.complexity_level,
                        'recommended_role': eval.recommended_role,
                        'overall_score': eval.overall_score,
                        'disciplines': eval.get_disciplines_list(),
                        'evaluation_date': eval.evaluation_date,
                        'evaluator_name': eval.evaluator_name
                    } for eval in evaluations
                ]

            except Exception as e:
                raise

    def get_summary_statistics(self):
        """Get summary statistics of all evaluations"""
        with self.get_session() as session:
            try:
                total_evaluations = session.query(TaskEvaluation).count()

                # Complexity distribution
                complexity_stats = {}
                for level in [1, 2, 3, 4]:
                    count = session.query(TaskEvaluation).filter_by(complexity_level=level).count()
                    complexity_stats[level] = count

                # Average scores by criteria
                avg_scores = session.query(
                    func.avg(TaskEvaluation.technical_score).label('technical'),
                    func.avg(TaskEvaluation.problem_score).label('problem'),
                    func.avg(TaskEvaluation.decision_score).label('decision'),
                    func.avg(TaskEvaluation.impact_score).label('impact'),
                    func.avg(TaskEvaluation.supervision_score).label('supervision'),
                    func.avg(TaskEvaluation.tools_score).label('tools')
                ).first()

                return {
                    'total_evaluations': total_evaluations,
                    'complexity_distribution': {
                        'level_1': complexity_stats.get(1, 0),
                        'level_2': complexity_stats.get(2, 0),
                        'level_3': complexity_stats.get(3, 0),
                        'level_4': complexity_stats.get(4, 0)
                    },
                    'average_scores': {
                        'technical': float(avg_scores.technical) if avg_scores.technical else 0,
                        'problem': float(avg_scores.problem) if avg_scores.problem else 0,
                        'decision': float(avg_scores.decision) if avg_scores.decision else 0,
                        'impact': float(avg_scores.impact) if avg_scores.impact else 0,
                        'supervision': float(avg_scores.supervision) if avg_scores.supervision else 0,
                        'tools': float(avg_scores.tools) if avg_scores.tools else 0
                    }
                }

            except Exception as e:
                raise

    def get_all_evaluations(self):
        """Get all evaluations (simple list)"""
        with self.get_session() as session:
            try:
                evaluations = session.query(TaskEvaluation).order_by(TaskEvaluation.evaluation_date.desc()).all()

                return [
                    {
                        'evaluation_id': eval.evaluation_id,
                        'task_name': eval.task_name,
                        'equipment_system': eval.equipment_system,
                        'complexity_level': eval.complexity_level,
                        'recommended_role': eval.recommended_role,
                        'overall_score': eval.overall_score,
                        'evaluation_date': eval.evaluation_date,
                        'evaluator_name': eval.evaluator_name
                    } for eval in evaluations
                ]

            except Exception as e:
                raise

# =====================================================
# EXAMPLE USAGE
# =====================================================

def example_usage():
    """Example of how to use the simple evaluation database"""

    # Initialize database
    db = SimpleTaskEvaluationDB()
    db.create_tables()
    db.setup_reference_data()

    # Example evaluation data
    evaluation_data = {
        'task_name': 'Operate Station 1 in Manual Mode',
        'task_description': 'Operate Bag Maker Station 1 in manual mode for setup and troubleshooting',
        'equipment_system': 'Bag Maker Station 1',
        'location': 'Production Floor A',
        'disciplines': ['O'],
        'modifiers': [],
        'technical_score': 1,
        'problem_score': 1,
        'decision_score': 1,
        'impact_score': 2,
        'supervision_score': 1,
        'tools_score': 1,
        'prerequisites': 'Basic understanding of bag making process',
        'safety_considerations': 'Standard lockout/tagout procedures',
        'required_tools': 'Standard hand tools, basic meters',
        'estimated_time': '30 minutes',
        'task_frequency': 'As-Needed',
        'success_criteria': 'Station operates in manual mode without errors',
        'quality_standards': 'Follow all SOP procedures',
        'evaluator_name': 'John Smith',
        'evaluation_notes': 'Basic operational task suitable for entry-level personnel'
    }

    # Save evaluation
    eval_id = db.save_evaluation(evaluation_data)
    print(f"Saved evaluation with ID: {eval_id}")

    # Retrieve evaluation
    retrieved_eval = db.get_evaluation(eval_id)
    print(f"Retrieved evaluation: {retrieved_eval['task_name']}")
    print(f"Complexity Level: {retrieved_eval['results']['complexity_level']}")
    print(f"Recommended Role: {retrieved_eval['results']['recommended_role']}")

    # Get summary statistics
    stats = db.get_summary_statistics()
    print(f"Total evaluations: {stats['total_evaluations']}")
    print(f"Complexity distribution: {stats['complexity_distribution']}")

    # Search evaluations
    search_results = db.search_evaluations(search_term="Station")
    print(f"Found {len(search_results)} evaluations matching 'Station'")

if __name__ == "__main__":
    example_usage()