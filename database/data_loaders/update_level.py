from sqlalchemy import create_engine, text
from models.configuration.config import DATABASE_URL

def update_levels():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        result = conn.execute(
            text("UPDATE core_competencies SET level = 'Level 2' WHERE level = '2'")
        )
        print(f"Updated {result.rowcount} rows in core_competencies")

if __name__ == "__main__":
    update_levels()
