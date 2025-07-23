import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.db_main import Base, AreaChecklist, ChecklistSection, ChecklistTask


class ChecklistDataLoader:
    """
    Loads checklist data from Excel file into database tables.
    Creates AreaChecklist, ChecklistSection, and ChecklistTask records.
    """

    def __init__(self, db_url="sqlite:///models/maintenance_skills.db"):
        """Initialize database connection"""
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def process_excel_file(self, filepath):
        """
        Process the merged training plans Excel file.
        Expected columns: Area, Training Course/Item Description
        """
        print(f"Processing Excel file: {filepath}")

        try:
            # Read the Excel file
            df = pd.read_excel(filepath, engine='openpyxl')
            print(f"Loaded Excel file: {df.shape[0]} rows, {df.shape[1]} columns")
            print(f"Columns: {list(df.columns)}")

            # Process each row sequentially
            current_area = None
            current_checklist = None
            current_section = None
            section_order = 1
            task_order = 1

            for index, row in df.iterrows():
                area = str(row['Area']).strip() if not pd.isna(row['Area']) else ''
                description = str(row['Training Course/Item Description']).strip() if not pd.isna(
                    row['Training Course/Item Description']) else ''

                if not area or not description:
                    continue  # Skip empty rows

                print(f"Processing row {index + 1}: Area='{area}', Description='{description}'")

                # Check if we need to create/switch to a new AreaChecklist
                if area != current_area:
                    current_checklist = self.get_or_create_checklist(area)
                    current_area = area
                    current_section = None  # Reset section when switching areas
                    section_order = 1
                    task_order = 1
                    print(f"  Switched to area: {area}")

                # Check if this is a section definition
                if description.startswith("Section:"):
                    section_name = description.replace("Section:", "").strip()
                    current_section = self.create_section(current_checklist, section_name, section_order)
                    section_order += 1
                    task_order = 1  # Reset task order for new section
                    print(f"    Created section: {section_name}")

                else:
                    # This is a task - add to current section
                    if current_section is None:
                        # Create a default section if none exists
                        current_section = self.create_section(current_checklist, "General", section_order)
                        section_order += 1
                        task_order = 1
                        print(f"    Created default section: General")

                    self.create_task(current_section, description, task_order)
                    task_order += 1
                    print(f"      Added task: {description[:50]}...")

            # Commit all changes
            self.session.commit()
            print("\nAll data successfully loaded into database!")

        except Exception as e:
            print(f"Error processing file: {e}")
            self.session.rollback()
            raise

    def get_or_create_checklist(self, area):
        """Get existing checklist or create new one for the area"""
        # Check if checklist already exists
        checklist = self.session.query(AreaChecklist).filter_by(area=area).first()

        if checklist:
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
        print(f"  Created new checklist: {checklist.document_number}")
        return checklist

    def create_section(self, checklist, section_name, section_order):
        """Create a new section for the checklist"""
        section = ChecklistSection(
            checklist_id=checklist.id,
            section_name=section_name,
            section_order=section_order
        )

        self.session.add(section)
        self.session.flush()  # Get the ID
        return section

    def create_task(self, section, task_description, task_order):
        """Create a new task for the section"""
        task = ChecklistTask(
            section_id=section.id,
            task_description=task_description,
            task_order=task_order
        )

        self.session.add(task)
        return task

    def print_summary(self):
        """Print summary of loaded data"""
        print("\n=== DATABASE SUMMARY ===")
        checklist_count = self.session.query(AreaChecklist).count()
        section_count = self.session.query(ChecklistSection).count()
        task_count = self.session.query(ChecklistTask).count()

        print(f"Total Checklists: {checklist_count}")
        print(f"Total Sections: {section_count}")
        print(f"Total Tasks: {task_count}")

        # Show details for each checklist
        checklists = self.session.query(AreaChecklist).all()
        for checklist in checklists:
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
        self.session.close()


def main():
    # File path
    excel_file = r"C:\Users\10169062\PycharmProjects\pythonProject2\merged_training_plans1.xlsx"

    # Check if file exists
    if not os.path.exists(excel_file):
        print(f"Error: File not found: {excel_file}")
        return

    # Initialize loader
    loader = ChecklistDataLoader()

    try:
        # Process the Excel file
        loader.process_excel_file(excel_file)

        # Print summary
        loader.print_summary()

    except Exception as e:
        print(f"Error: {e}")
    finally:
        loader.close()

    print("Done!")


if __name__ == "__main__":
    main()