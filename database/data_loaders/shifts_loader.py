"""
Shift Load Script for 24/7 Operations
Creates common 8, 10, and 12-hour shifts with specified start times
"""

import sys
import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import time

# Add the project root to the path so we can import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from models.configuration.config import DATABASE_URL
from models.configuration.log_config import info_id, debug_id, error_id, warning_id, with_request_id, set_request_id
from models.db_main import Shift, ShiftDay, Base


class ShiftsLoader:
    """
    Loads common shift patterns into the database for 24/7 operations
    """

    def __init__(self, db_url=None):
        """Initialize database connection"""
        self.request_id = set_request_id("SHIFTS_LOADER")
        info_id("Initializing ShiftsLoader", self.request_id)

        # Use config DATABASE_URL if no URL provided
        db_url = db_url or DATABASE_URL
        debug_id(f"Using database URL: {db_url}", self.request_id)

        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

        info_id("Database connection established", self.request_id)

    def shift_exists(self, shift_name):
        """
        Check if a shift with the given name already exists

        Args:
            shift_name: Name of the shift to check

        Returns:
            True if shift exists, False otherwise
        """
        debug_id(f"Checking if shift exists: {shift_name}", self.request_id)
        existing_shift = self.session.query(Shift).filter(Shift.shift_name == shift_name).first()
        exists = existing_shift is not None
        debug_id(f"Shift '{shift_name}' exists: {exists}", self.request_id)
        return exists

    def create_shift_with_days(self, shift_name, description, shift_pattern, shift_hours, start_times):
        """
        Create a shift with associated shift days (only if it doesn't already exist)

        Args:
            shift_name: Name of the shift
            description: Description of the shift
            shift_pattern: 'weekly' or 'biweekly'
            shift_hours: Number of hours for the shift
            start_times: List of tuples (day_of_week, week_number, start_time)
        """
        # Check if shift already exists
        if self.shift_exists(shift_name):
            warning_id(f"Skipping '{shift_name}' - already exists", self.request_id)
            print(f"  Skipping '{shift_name}' - already exists")
            return None

        debug_id(f"Creating shift: {shift_name} ({shift_hours}hr, {shift_pattern})", self.request_id)

        # Create the shift
        shift = Shift(
            shift_name=shift_name,
            description=description,
            shift_pattern=shift_pattern,
            is_active=True
        )
        self.session.add(shift)
        self.session.flush()  # Get the shift ID

        debug_id(f"Created shift with ID: {shift.id}", self.request_id)

        # Create shift days
        days_created = 0
        for day_of_week, week_number, start_time in start_times:
            # Calculate end time
            start_hour = start_time.hour
            start_minute = start_time.minute
            end_hour = (start_hour + shift_hours) % 24
            end_time = time(end_hour, start_minute)

            shift_day = ShiftDay(
                shift_id=shift.id,
                day_of_week=day_of_week,
                week_number=week_number,
                scheduled_start_time=start_time,
                scheduled_end_time=end_time
            )
            self.session.add(shift_day)
            days_created += 1

        info_id(f"Created '{shift_name}' with {days_created} shift days", self.request_id)
        print(f"  Created '{shift_name}' with {days_created} shift days")
        return shift

    @with_request_id
    def load_common_shifts(self):
        """
        Load common shifts for 24/7 operation
        """
        info_id("Starting to load common shifts for 24/7 operation", self.request_id)
        print("Loading common shifts for 24/7 operation...")

        # Define start times
        start_times = {
            '0530': time(5, 30),
            '0600': time(6, 0),
            '0700': time(7, 0)
        }

        debug_id(f"Using start times: {list(start_times.keys())}", self.request_id)
        shifts_created = []

        # =============================================================================
        # 8-HOUR SHIFTS (3 shifts per day for 24/7 coverage)
        # =============================================================================
        info_id("Creating 8-hour shifts", self.request_id)

        # Day Shift - 8 hours starting at different times
        for start_key, start_time in start_times.items():
            debug_id(f"Processing 8-hour shifts for start time: {start_key}", self.request_id)

            # Calculate the three 8-hour shifts for 24/7 coverage
            day_start = start_time
            swing_start = time((start_time.hour + 8) % 24, start_time.minute)
            night_start = time((start_time.hour + 16) % 24, start_time.minute)

            # Weekly 8-hour shifts
            all_days = [(i, 1, day_start) for i in range(7)]  # All 7 days
            weekdays_only = [(i, 1, day_start) for i in range(1, 6)]  # Monday-Friday
            weekends_only = [(i, 1, day_start) for i in [0, 6]]  # Saturday-Sunday

            # Day shifts
            shift = self.create_shift_with_days(
                f"Day Shift 8hr ({start_key})",
                f"8-hour day shift starting at {start_key}",
                'weekly', 8, all_days
            )
            if shift:
                shifts_created.append(shift)

            shift = self.create_shift_with_days(
                f"Day Shift 8hr Weekdays ({start_key})",
                f"8-hour day shift Monday-Friday starting at {start_key}",
                'weekly', 8, weekdays_only
            )
            if shift:
                shifts_created.append(shift)

            shift = self.create_shift_with_days(
                f"Day Shift 8hr Weekends ({start_key})",
                f"8-hour day shift weekends only starting at {start_key}",
                'weekly', 8, weekends_only
            )
            if shift:
                shifts_created.append(shift)

            # Swing shifts (8 hours later)
            shift = self.create_shift_with_days(
                f"Swing Shift 8hr ({swing_start.strftime('%H%M')})",
                f"8-hour swing shift starting at {swing_start.strftime('%H:%M')}",
                'weekly', 8, [(i, 1, swing_start) for i in range(7)]
            )
            if shift:
                shifts_created.append(shift)

            # Night shifts (16 hours later)
            shift = self.create_shift_with_days(
                f"Night Shift 8hr ({night_start.strftime('%H%M')})",
                f"8-hour night shift starting at {night_start.strftime('%H:%M')}",
                'weekly', 8, [(i, 1, night_start) for i in range(7)]
            )
            if shift:
                shifts_created.append(shift)

        # =============================================================================
        # 10-HOUR SHIFTS
        # =============================================================================
        info_id("Creating 10-hour shifts", self.request_id)

        for start_key, start_time in start_times.items():
            debug_id(f"Processing 10-hour shifts for start time: {start_key}", self.request_id)

            # Weekly 10-hour shifts
            all_days = [(i, 1, start_time) for i in range(7)]
            weekdays_only = [(i, 1, start_time) for i in range(1, 6)]

            shift = self.create_shift_with_days(
                f"Day Shift 10hr ({start_key})",
                f"10-hour day shift starting at {start_key}",
                'weekly', 10, all_days
            )
            if shift:
                shifts_created.append(shift)

            shift = self.create_shift_with_days(
                f"Day Shift 10hr Weekdays ({start_key})",
                f"10-hour day shift Monday-Friday starting at {start_key}",
                'weekly', 10, weekdays_only
            )
            if shift:
                shifts_created.append(shift)

            # 4-day/10-hour schedule (common pattern)
            four_day_pattern = [(i, 1, start_time) for i in range(1, 5)]  # Monday-Thursday
            shift = self.create_shift_with_days(
                f"4x10 Day Shift ({start_key})",
                f"4-day/10-hour shift Monday-Thursday starting at {start_key}",
                'weekly', 10, four_day_pattern
            )
            if shift:
                shifts_created.append(shift)

        # =============================================================================
        # 12-HOUR SHIFTS
        # =============================================================================
        info_id("Creating 12-hour shifts", self.request_id)

        for start_key, start_time in start_times.items():
            debug_id(f"Processing 12-hour shifts for start time: {start_key}", self.request_id)

            # Calculate night shift start time (12 hours later)
            night_start = time((start_time.hour + 12) % 24, start_time.minute)

            # Weekly 12-hour shifts
            all_days = [(i, 1, start_time) for i in range(7)]

            shift = self.create_shift_with_days(
                f"Day Shift 12hr ({start_key})",
                f"12-hour day shift starting at {start_key}",
                'weekly', 12, all_days
            )
            if shift:
                shifts_created.append(shift)

            shift = self.create_shift_with_days(
                f"Night Shift 12hr ({night_start.strftime('%H%M')})",
                f"12-hour night shift starting at {night_start.strftime('%H:%M')}",
                'weekly', 12, [(i, 1, night_start) for i in range(7)]
            )
            if shift:
                shifts_created.append(shift)

            # Common 12-hour patterns
            # 3-day pattern (Friday, Saturday, Sunday)
            weekend_pattern = [(i, 1, start_time) for i in [5, 6, 0]]  # Fri, Sat, Sun
            shift = self.create_shift_with_days(
                f"Weekend 12hr ({start_key})",
                f"12-hour weekend shift Fri-Sun starting at {start_key}",
                'weekly', 12, weekend_pattern
            )
            if shift:
                shifts_created.append(shift)

            # Bi-weekly 12-hour patterns (common in healthcare/manufacturing)
            debug_id(f"Creating bi-weekly patterns for {start_key}", self.request_id)

            # Week 1: Monday, Tuesday, Wednesday
            # Week 2: Thursday, Friday, Saturday, Sunday
            biweekly_week1 = [(1, 1, start_time), (2, 1, start_time), (3, 1, start_time)]  # Mon, Tue, Wed - Week 1
            biweekly_week2 = [(4, 2, start_time), (5, 2, start_time), (6, 2, start_time), (0, 2, start_time)]  # Thu, Fri, Sat, Sun - Week 2

            shift = self.create_shift_with_days(
                f"Biweekly 12hr Pattern A ({start_key})",
                f"Bi-weekly 12-hour shift pattern A starting at {start_key}",
                'biweekly', 12, biweekly_week1 + biweekly_week2
            )
            if shift:
                shifts_created.append(shift)

            # Alternative bi-weekly pattern
            # Week 1: Thursday, Friday, Saturday
            # Week 2: Sunday, Monday, Tuesday, Wednesday
            biweekly_alt_week1 = [(4, 1, start_time), (5, 1, start_time), (6, 1, start_time)]  # Thu, Fri, Sat - Week 1
            biweekly_alt_week2 = [(0, 2, start_time), (1, 2, start_time), (2, 2, start_time), (3, 2, start_time)]  # Sun, Mon, Tue, Wed - Week 2

            shift = self.create_shift_with_days(
                f"Biweekly 12hr Pattern B ({start_key})",
                f"Bi-weekly 12-hour shift pattern B starting at {start_key}",
                'biweekly', 12, biweekly_alt_week1 + biweekly_alt_week2
            )
            if shift:
                shifts_created.append(shift)

            # =============================================================================
            # 2/3 BI-WEEKLY 12-HOUR SHIFTS (Starting Sunday)
            # =============================================================================
            debug_id(f"Creating 2/3 bi-weekly patterns for {start_key}", self.request_id)

            # Pattern A: Sun/Mon (Week 1), Tue/Wed/Thu (Week 2), then Sat/Sun/Mon (next cycle)
            # Week 1: 2 days, Week 2: 3 days, Friday off
            biweekly_2of3_pattern_a = [
                (0, 1, start_time),  # Sunday - Week 1
                (1, 1, start_time),  # Monday - Week 1
                (2, 2, start_time),  # Tuesday - Week 2
                (3, 2, start_time),  # Wednesday - Week 2
                (4, 2, start_time),  # Thursday - Week 2
                # Friday off
                (6, 1, start_time),  # Saturday - Week 1 (next cycle)
            ]

            shift = self.create_shift_with_days(
                f"2/3 Biweekly 12hr Pattern A ({start_key})",
                f"2/3 Bi-weekly 12-hour shift Pattern A starting Sunday at {start_key} (Week1: Sun/Mon, Week2: Tue/Wed/Thu, Fri off, then Sat)",
                'biweekly', 12, biweekly_2of3_pattern_a
            )
            if shift:
                shifts_created.append(shift)

            # Pattern B: Complementary pattern to cover the gaps
            # Tue/Wed (Week 1), Thu/Fri/Sat (Week 2), then Sun/Mon (next cycle)
            biweekly_2of3_pattern_b = [
                (2, 1, start_time),  # Tuesday - Week 1
                (3, 1, start_time),  # Wednesday - Week 1
                (4, 2, start_time),  # Thursday - Week 2
                (5, 2, start_time),  # Friday - Week 2
                (6, 2, start_time),  # Saturday - Week 2
                (0, 1, start_time),  # Sunday - Week 1 (next cycle)
                (1, 2, start_time),  # Monday - Week 2 (next cycle)
            ]

            shift = self.create_shift_with_days(
                f"2/3 Biweekly 12hr Pattern B ({start_key})",
                f"2/3 Bi-weekly 12-hour shift Pattern B starting at {start_key} (Week1: Tue/Wed, Week2: Thu/Fri/Sat, then Sun/Mon)",
                'biweekly', 12, biweekly_2of3_pattern_b
            )
            if shift:
                shifts_created.append(shift)

        info_id(f"Shift creation completed: {len(shifts_created)} shifts created", self.request_id)
        print(f"Created {len(shifts_created)} shifts successfully!")
        return shifts_created

    def print_shift_summary(self, shifts):
        """
        Print a summary of created shifts
        """
        info_id(f"Generating shift summary for {len(shifts)} shifts", self.request_id)
        print("\n" + "="*80)
        print("SHIFT SUMMARY")
        print("="*80)

        for shift in shifts:
            debug_id(f"Shift summary: {shift.shift_name} - {len(shift.shift_days)} days", self.request_id)
            print(f"\nShift: {shift.shift_name}")
            print(f"Description: {shift.description}")
            print(f"Pattern: {shift.shift_pattern}")
            print(f"Days:")

            for day in shift.shift_days:
                day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
                week_info = f" (Week {day.week_number})" if shift.shift_pattern == 'biweekly' else ""
                print(f"  {day_names[day.day_of_week]}{week_info}: {day.scheduled_start_time.strftime('%H:%M')} - {day.scheduled_end_time.strftime('%H:%M')}")

    def close(self):
        """Close database session"""
        info_id("Closing database session", self.request_id)
        self.session.close()


def main():
    """
    Main function to run the shift loading script
    """
    request_id = set_request_id("MAIN_SHIFTS")
    info_id("=== SHIFT LOADER FOR 24/7 OPERATIONS ===", request_id)
    print("=== SHIFT LOADER FOR 24/7 OPERATIONS ===")

    loader = None

    try:
        info_id("Initializing ShiftsLoader", request_id)
        loader = ShiftsLoader()

        info_id("Starting shift loading process", request_id)
        shifts = loader.load_common_shifts()

        info_id("Committing shifts to database", request_id)
        loader.session.commit()

        loader.print_shift_summary(shifts)

        info_id(f"Shift loading completed successfully: {len(shifts)} shifts loaded", request_id)
        print(f"\nSuccessfully loaded {len(shifts)} shifts!")

    except Exception as e:
        error_id(f"Error during shift loading: {str(e)}", request_id)
        print(f"Error loading shifts: {e}")
        if loader:
            loader.session.rollback()
        raise

    finally:
        if loader:
            loader.close()


if __name__ == "__main__":
    main()