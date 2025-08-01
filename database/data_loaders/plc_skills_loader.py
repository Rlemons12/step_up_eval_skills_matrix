import pandas as pd
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import sys
import os

# Add the project root to the path so we can import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.configuration.config import DATABASE_URL, DATABASE_DIR
from models.configuration.log_config import info_id, debug_id, error_id, warning_id, with_request_id, set_request_id

# Import your models from db_main.py
from models.db_main import (
    Base, ElectricalSkill, ElectricalTask
)

# Use config-based paths
PLC_SKILLS_FILE = os.path.join(DATABASE_DIR, 'loadsheets', 'skills_matrix', 'plc_skills_mapping.xlsx')

KEYS = [
    "Skill ID", "Chapter", "Task Action", "Task Object", "Verification Method",
    "Required for Level 1", "Category", "ORM Class", "Subcategory", "Tool/Voltage/Note"
]

ORM_MAP = {
    "ElectricalSkill": ElectricalSkill,
    "ElectricalTask": ElectricalTask,
}


class PLCSkillsLoader:
    """
    Loads PLC skills data from Excel file into database tables.
    """

    def __init__(self, db_url=None):
        """Initialize database connection"""
        self.request_id = set_request_id("PLC_LOADER")
        info_id("Initializing PLCSkillsLoader", self.request_id)

        # Use config DATABASE_URL if no URL provided
        db_url = db_url or DATABASE_URL
        debug_id(f"Using database URL from config: {db_url}", self.request_id)

        self.engine = create_engine(db_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        info_id("Database connection established", self.request_id)

    @with_request_id
    def load_skills(self, filename=None):
        """Load skills from Excel/CSV file"""
        # Use default file if none provided
        filename = filename or PLC_SKILLS_FILE

        info_id(f"Loading PLC skills from: {filename}", self.request_id)

        # Check if file exists
        if not os.path.exists(filename):
            error_id(f"File not found: {filename}", self.request_id)
            raise FileNotFoundError(f"File not found: {filename}")

        try:
            # Auto-detect Excel vs CSV
            if filename.endswith(".xlsx"):
                debug_id("Reading Excel file", self.request_id)
                df = pd.read_excel(filename)
            else:
                debug_id("Reading CSV file", self.request_id)
                df = pd.read_csv(filename)

            info_id(f"Loaded file with {len(df)} rows and {len(df.columns)} columns", self.request_id)
            debug_id(f"Columns found: {list(df.columns)}", self.request_id)

            # Clean up columns
            df.columns = [c.strip() for c in df.columns]
            missing = set(KEYS) - set(df.columns)
            if missing:
                error_id(f"Missing required columns: {missing}", self.request_id)
                raise ValueError(f"Missing required columns: {missing}")

            count = 0
            skipped = 0

            for idx, row in df.iterrows():
                try:
                    orm_type = str(row["ORM Class"]).strip()

                    if orm_type not in ORM_MAP:
                        warning_id(
                            f"Skipping row {idx}: Unsupported ORM class '{orm_type}' (only ElectricalSkill/ElectricalTask supported)",
                            self.request_id)
                        skipped += 1
                        continue

                    cls = ORM_MAP[orm_type]
                    kwargs = {}

                    # Always set skill_category to "Electrical"
                    kwargs['skill_category'] = "Electrical"
                    # Set the correct competency_type based on ORM class
                    if orm_type == "ElectricalSkill":
                        kwargs['competency_type'] = "electrical"
                    elif orm_type == "ElectricalTask":
                        kwargs['competency_type'] = "electrical_task"

                    if orm_type == "ElectricalSkill":
                        debug_id(f"Processing ElectricalSkill row {idx}", self.request_id)
                        kwargs['sub_category'] = str(row["Subcategory"]) if pd.notnull(
                            row["Subcategory"]) else "PLC Systems"

                        # Set voltage_level if relevant (look for voltage-related terms)
                        tool_voltage_note = str(row["Tool/Voltage/Note"]) if pd.notnull(
                            row["Tool/Voltage/Note"]) else ""
                        if any(term in tool_voltage_note.lower() for term in
                               ["voltage", "volt", "24v", "120v", "480v", "low", "high"]):
                            kwargs['voltage_level'] = tool_voltage_note
                        else:
                            kwargs['voltage_level'] = "Low Voltage"  # Default for PLC systems

                        # Set competency name and description
                        kwargs['competency_name'] = f"PLC - {row['Subcategory']}" if pd.notnull(
                            row["Subcategory"]) else "PLC Skills"
                        kwargs['description'] = f"PLC system skills - {row['Subcategory']}" if pd.notnull(
                            row["Subcategory"]) else "General PLC system skills"

                    elif orm_type == "ElectricalTask":
                        debug_id(f"Processing ElectricalTask row {idx}", self.request_id)
                        kwargs['sub_category'] = str(row["Subcategory"]) if pd.notnull(
                            row["Subcategory"]) else "PLC Systems"

                        # Set voltage_level
                        tool_voltage_note = str(row["Tool/Voltage/Note"]) if pd.notnull(
                            row["Tool/Voltage/Note"]) else ""
                        if tool_voltage_note and any(term in tool_voltage_note.lower() for term in
                                                     ["voltage", "volt", "24v", "120v", "480v", "low", "high"]):
                            kwargs['voltage_level'] = tool_voltage_note
                        else:
                            kwargs['voltage_level'] = "Low Voltage"  # Default for PLC systems

                        kwargs['task_action'] = str(row["Task Action"]) if pd.notnull(row["Task Action"]) else ""
                        kwargs['task_object'] = str(row["Task Object"]) if pd.notnull(row["Task Object"]) else ""
                        kwargs['verification_method'] = str(row["Verification Method"]) if pd.notnull(
                            row["Verification Method"]) else ""

                        # Set competency name and description
                        task_desc = f"{kwargs['task_action']} {kwargs['task_object']}".strip()
                        kwargs['competency_name'] = f"PLC Task - {task_desc}" if task_desc else "PLC Task"
                        kwargs['description'] = f"{task_desc} - {kwargs['verification_method']}" if task_desc and \
                                                                                                    kwargs[
                                                                                                        'verification_method'] else "PLC maintenance task"

                    # Always set to Level 2, Proficiency B as requested
                    kwargs['required_for_level_1'] = False
                    kwargs['required_for_level_2'] = True
                    kwargs['level'] = "2"
                    kwargs['proficiency_level'] = "Level_2_B"

                    # Remove empty/null fields
                    kwargs = {k: v for k, v in kwargs.items() if v is not None and not pd.isnull(v) and str(v).strip()}

                    # Create and add the skill/task
                    skill = cls(**kwargs)
                    self.session.add(skill)
                    count += 1

                    if count % 10 == 0:  # Log progress every 10 records
                        debug_id(f"Processed {count} records so far", self.request_id)

                except Exception as e:
                    error_id(f"Error processing row {idx}: {str(e)}", self.request_id)
                    skipped += 1
                    continue

            # Commit all changes
            self.session.commit()
            info_id(f"Successfully loaded {count} PLC skills/tasks to database (skipped: {skipped})", self.request_id)

            return count, skipped

        except Exception as e:
            error_id(f"Error loading skills file: {str(e)}", self.request_id)
            self.session.rollback()
            raise

    def close(self):
        """Close database session"""
        info_id("Closing database session", self.request_id)
        self.session.close()


def main():
    """Main function to run the PLC skills loader"""
    request_id = set_request_id("MAIN_PLC")
    info_id("=== PLC SKILLS LOADER ===", request_id)
    print("=== PLC SKILLS LOADER ===")

    loader = None

    try:
        info_id("Initializing PLCSkillsLoader", request_id)
        loader = PLCSkillsLoader()

        info_id(f"Loading PLC skills from: {PLC_SKILLS_FILE}", request_id)
        print(f"Loading PLC skills from {PLC_SKILLS_FILE}...")

        count, skipped = loader.load_skills()

        info_id(f"PLC skills loading completed: {count} loaded, {skipped} skipped", request_id)
        print(f"Successfully loaded {count} Electrical skills/tasks to DB (skipped: {skipped})")

    except FileNotFoundError as e:
        error_id(f"File not found error: {str(e)}", request_id)
        print(f"Error: {e}")
        print(f"Please check that the file exists at: {PLC_SKILLS_FILE}")

    except Exception as e:
        error_id(f"Unexpected error during PLC skills loading: {str(e)}", request_id)
        print(f"Error: {e}")

    finally:
        if loader:
            loader.close()

    print("Done!")


if __name__ == "__main__":
    main()