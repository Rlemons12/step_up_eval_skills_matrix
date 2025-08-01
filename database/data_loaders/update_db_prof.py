from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models.configuration.config import DATABASE_URL
from models.db_main import CoreCompetency  # or your base class

def update_proficiency_levels():
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    records = session.query(CoreCompetency).filter_by(proficiency_level="Level_2_B").all()
    count = 0
    for rec in records:
        rec.proficiency_level = "B"
        count += 1
    session.commit()
    print(f"Updated {count} records in core_competencies")
    session.close()

if __name__ == "__main__":
    update_proficiency_levels()
