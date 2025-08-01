import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the path so we can import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models.configuration.config import DATABASE_URL,TRAINING_PLANS_XLSX
from models.configuration.log_config import info_id, debug_id, error_id, warning_id, with_request_id, set_request_id
from models.db_main import Base, AreaChecklist, ChecklistSection, ChecklistTask



class ChecklistDataLoader:
    """
    Loads checklist data from Excel file into database tables.
    Creates AreaChecklist, ChecklistSection, and ChecklistTask records.
    """

    def __init__(self, db_url=None):
        """Initialize database connection"""
        self.request_id = set_request_id("CHECKLIST_LOADER")
        info_id("Initializing ChecklistDataLoader", self.request_id)

        # Use config DATABASE_URL if no URL provided
        db_url = db_url or DATABASE_URL
        debug_id(f"Using database URL: {db_url}", self.request_id)

        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        info_id("Database connection established", self.request_id)

    @with_request_id
    def process_excel_file(self, filepath=None):
        """
        Process the merged training plans Excel file.
        Expected columns: Area, Training Course/Item Description
        """
        # Use config file path if no filepath provided
        filepath = filepath or TRAINING_PLANS_XLSX

        info_id(f"Processing Excel file: {filepath}", self.request_id)
        print(f"Processing Excel file: {filepath}")

        # Check if file exists
        if not os.path.exists(filepath):
            error_id(f"File not found: {filepath}", self.request_id)
            raise FileNotFoundError(f"File not found: {filepath}")

        try:
            # Read the Excel file
            debug_id("Reading Excel file", self.request_id)
            df = pd.read_excel(filepath, engine='openpyxl')
            info_id(f"Loaded Excel file: {df.shape[0]} rows, {df.shape[1]} columns", self.request_id)
            debug_id(f"Columns: {list(df.columns)}", self.request_id)

            print(f"Loaded Excel file: {df.shape[0]} rows, {df.shape[1]} columns")
            print(f"Columns: {list(df.columns)}")

            # Process each row sequentially
            current_area = None
            current_checklist = None
            current_section = None
            section_order = 1
            task_order = 1
            processed_rows = 0
            skipped_rows = 0

            for index, row in df.iterrows():
                area = str(row['Area']).strip() if not pd.isna(row['Area']) else ''
                description = str(row['Training Course/Item Description']).strip() if not pd.isna(
                    row['Training Course/Item Description']) else ''

                if not area or not description:
                    skipped_rows += 1
                    debug_id(f"Skipping empty row {index + 1}", self.request_id)
                    continue  # Skip empty rows

                debug_id(f"Processing row {index + 1}: Area='{area}', Description='{description[:50]}...'",
                         self.request_id)
                print(f"Processing row {index + 1}: Area='{area}', Description='{description}'")

                # Check if we need to create/switch to a new AreaChecklist
                if area != current_area:
                    current_checklist = self.get_or_create_checklist(area)
                    current_area = area
                    current_section = None  # Reset section when switching areas
                    section_order = 1
                    task_order = 1
                    info_id(f"Switched to area: {area}", self.request_id)
                    print(f"  Switched to area: {area}")

                # Check if this is a section definition
                if description.startswith("Section:"):
                    section_name = description.replace("Section:", "").strip()
                    current_section = self.create_section(current_checklist, section_name, section_order)
                    section_order += 1
                    task_order = 1  # Reset task order for new section
                    debug_id(f"Created section: {section_name}", self.request_id)
                    print(f"    Created section: {section_name}")

                else:
                    # This is a task - add to current section
                    if current_section is None:
                        # Create a default section if none exists
                        current_section = self.create_section(current_checklist, "General", section_order)
                        section_order += 1
                        task_order = 1
                        debug_id("Created default section: General", self.request_id)
                        print(f"    Created default section: General")

                    self.create_task(current_section, description, task_order)
                    task_order += 1
                    debug_id(f"Added task: {description[:50]}...", self.request_id)
                    print(f"      Added task: {description[:50]}...")

                processed_rows += 1

            # Commit all changes
            self.session.commit()
            info_id(f"Data processing completed: {processed_rows} rows processed, {skipped_rows} rows skipped",
                    self.request_id)
            print(f"\nAll data successfully loaded into database!")
            print(f"Processed: {processed_rows} rows, Skipped: {skipped_rows} rows")

        except Exception as e:
            error_id(f"Error processing file: {str(e)}", self.request_id)
            print(f"Error processing file: {e}")
            self.session.rollback()
            raise

    def get_or_create_checklist(self, area):
        """Get existing checklist or create new one for the area"""
        debug_id(f"Getting or creating checklist for area: {area}", self.request_id)

        # Check if checklist already exists
        checklist = self.session.query(AreaChecklist).filter_by(area=area).first()

        if checklist:
            debug_id(f"Found existing checklist for area: {area}", self.request_id)
            print(f"  Found existing checklist for area: {area}")
            return checklist

        # Create new checklist
        checklist = AreaChecklist(
            document_number=f"CL-{area}",
            description=f"Maintenance Checklist for {area}",
            area=area,
            version="1.0",
            effective_date="2025-01-01"
        )

        self.session.add(checklist)
        self.session.flush()  # Get the ID
        info_id(f"Created new checklist: {checklist.document_number} for area: {area}", self.request_id)
        print(f"  Created new checklist: {checklist.document_number}")
        return checklist

    def create_section(self, checklist, section_name, section_order):
        """Create a new section for the checklist"""
        debug_id(f"Creating section: {section_name} (order: {section_order})", self.request_id)

        section = ChecklistSection(
            checklist_id=checklist.id,
            section_name=section_name,
            section_order=section_order
        )

        self.session.add(section)
        self.session.flush()  # Get the ID
        debug_id(f"Created section ID: {section.id}", self.request_id)
        return section

    def create_task(self, section, task_description, task_order):
        """Create a new task for the section"""
        debug_id(f"Creating task: {task_description[:30]}... (order: {task_order})", self.request_id)

        task = ChecklistTask(
            section_id=section.id,
            task_description=task_description,
            task_order=task_order
        )

        self.session.add(task)
        return task

    def print_summary(self):
        """Print summary of loaded data"""
        info_id("Generating database summary", self.request_id)
        print("\n=== DATABASE SUMMARY ===")

        checklist_count = self.session.query(AreaChecklist).count()
        section_count = self.session.query(ChecklistSection).count()
        task_count = self.session.query(ChecklistTask).count()

        info_id(f"Database summary: {checklist_count} checklists, {section_count} sections, {task_count} tasks",
                self.request_id)
        print(f"Total Checklists: {checklist_count}")
        print(f"Total Sections: {section_count}")
        print(f"Total Tasks: {task_count}")

        # Show details for each checklist
        checklists = self.session.query(AreaChecklist).all()
        for checklist in checklists:
            debug_id(f"Checklist details: {checklist.document_number} - {len(checklist.sections)} sections",
                     self.request_id)
            print(f"\nChecklist: {checklist.document_number} ({checklist.area})")
            for section in checklist.sections:
                print(f"  Section: {section.section_name} ({len(section.tasks)} tasks)")
                # Show first few tasks as examples
                for i, task in enumerate(section.tasks[:3]):
                    print(f"    Task {task.task_order}: {task.task_description}")
                if len(section.tasks) > 3:
                    print(f"    ... and {len(section.tasks) - 3} more tasks")

    def close(self):
        """Close database session"""
        info_id("Closing database session", self.request_id)
        self.session.close()


def main():
    request_id = set_request_id("MAIN_CHECKLIST")
    info_id("=== CHECKLIST DATA LOADER ===", request_id)
    print("=== CHECKLIST DATA LOADER ===")

    # Initialize loader
    loader = None

    try:
        info_id("Initializing ChecklistDataLoader", request_id)
        loader = ChecklistDataLoader()

        # Process the Excel file (will use config file path)
        info_id("Starting Excel file processing", request_id)
        loader.process_excel_file()

        # Print summary
        loader.print_summary()

        info_id("Checklist data loading completed successfully", request_id)
        print("\nChecklist data loading completed successfully!")

    except FileNotFoundError as e:
        error_id(f"File not found error: {str(e)}", request_id)
        print(f"Error: {e}")
        print(f"Please check that the file exists at: {TRAINING_PLANS_XLSX}")

    except Exception as e:
        error_id(f"Unexpected error during checklist loading: {str(e)}", request_id)
        print(f"Error: {e}")

    finally:
        if loader:
            loader.close()

    print("Done!")


if __name__ == "__main__":
    main()