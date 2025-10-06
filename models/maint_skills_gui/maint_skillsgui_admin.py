import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import csv
from datetime import time, datetime
import os
import sys

# Add the project root to the path so we can import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from models.configuration.config import DATABASE_URL
from models.configuration.log_config import info_id, debug_id, error_id, warning_id, set_request_id

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
import hashlib, os, binascii
from sqlalchemy import Column, Integer, String, Boolean, DateTime, func

# ===================== Multi-user Auth: model + security helpers =====================
AuthBase = declarative_base()

class UserAuth(AuthBase):
    __tablename__ = "users_auth"

    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    # store hex strings for hash & salt
    password_hash = Column(String(256), nullable=False)
    salt = Column(String(64), nullable=False)
    role = Column(String(32), nullable=False, default="user")  # e.g., "admin", "manager", "user"
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())

def make_salt(n_bytes: int = 16) -> str:
    return binascii.hexlify(os.urandom(n_bytes)).decode("ascii")

def hash_password(password: str, salt_hex: str, iterations: int = 120_000) -> str:
    salt = binascii.unhexlify(salt_hex.encode("ascii"))
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)
    return binascii.hexlify(dk).decode("ascii")

def verify_password(password: str, salt_hex: str, expected_hash_hex: str) -> bool:
    return hash_password(password, salt_hex) == expected_hash_hex
# ================================================================================


from models.db_main import (
    Employee, MaintenancePerson, Supervisor, TechnicalSkill, MechanicalSkill, ElectricalSkill, ToolSkill,
    CoreCompetency, AreaChecklist, ChecklistSection, ChecklistTask, OperationalTask, OperationalSkill,
    MechanicalTask, ElectricalTask, ToolTask, TaskSkillAssignment, ChecklistTaskCompetency,
    EmployeeCompetency, EmployeeSchedule, Shift, ShiftDay
)

# Initialize logging for this GUI application
request_id = set_request_id("GUI_APP")
info_id("Initializing GUI application", request_id)

# Database setup using config
debug_id(f"Using database URL from config: {DATABASE_URL}", request_id)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


# --- Create the users_auth table if it doesn't exist ---
try:
    AuthBase.metadata.create_all(bind=engine)
    info_id("Auth table ready", request_id)
except Exception as e:
    error_id(f"Failed to create auth table: {e}", request_id)

def ensure_admin_user(default_user="admin"):
    """Create an initial admin if no users exist."""
    try:
        count = session.query(UserAuth).count()
        if count == 0:
            from tkinter import simpledialog, Tk
            boot = Tk()
            boot.withdraw()
            u = simpledialog.askstring("Setup Admin", "Create admin username:", initialvalue=default_user)
            p = simpledialog.askstring("Setup Admin", "Create admin password:", show="*")
            boot.destroy()

            if not u or not p:
                raise RuntimeError("Admin setup aborted; no users exist.")

            salt = make_salt()
            phash = hash_password(p, salt)
            admin = UserAuth(username=u.strip(), password_hash=phash, salt=salt, role="admin", is_active=True)
            session.add(admin)
            session.commit()
            info_id(f"Admin user '{u}' created.", request_id)
    except Exception as e:
        session.rollback()
        error_id(f"Admin bootstrap failed: {e}", request_id)

ensure_admin_user()

info_id("Database connection established", request_id)

def normalize_str(val):
    """Ensure blank or whitespace string is always stored as None, and trims spaces."""
    if val is None:
        return None
    val = str(val).strip()
    return val if val else None


class EmployeeForm(simpledialog.Dialog):
    """Popup dialog for adding/editing an employee with Active/Not Active status and maintenance level choices."""
    MAINTENANCE_LEVELS = ["Level 1", "Level 2", "Level 3", "Maintenance Tech"]

    def __init__(self, parent, title, employee=None):
        self.employee = employee
        super().__init__(parent, title)

    def body(self, master):
        labels = [
            "Employee ID", "First Name", "Last Name",
            "Hire Date", "Birthdate", "Status", "Employee Type", "Reports To ID"
        ]
        self.entries = {}

        for idx, label in enumerate(labels):
            ttk.Label(master, text=label).grid(row=idx, column=0, sticky='e', padx=5, pady=2)
            if label == "Status":
                self.status_var = tk.StringVar()
                combo = ttk.Combobox(master, textvariable=self.status_var, values=["Active", "Not Active"],
                                     state="readonly")
                combo.grid(row=idx, column=1, padx=5, pady=2)
                if self.employee and self.employee.status:
                    self.status_var.set(self.employee.status)
                else:
                    self.status_var.set("Active")
                self.entries[label] = combo
            elif label == "Employee Type":
                self.emp_type_var = tk.StringVar()
                combo = ttk.Combobox(master, textvariable=self.emp_type_var,
                                     values=["Employee", "Supervisor", "MaintenancePerson"], state="readonly")
                combo.grid(row=idx, column=1, padx=5, pady=2)
                if self.employee:
                    self.emp_type_var.set(type(self.employee).__name__)
                else:
                    self.emp_type_var.set("Employee")
                self.entries[label] = combo
            elif label == "Reports To ID":
                # List all supervisors for dropdown
                supervisors = session.query(Supervisor).all()
                self.supervisor_choices = [("", "")] + [
                    (sup.id, f"{sup.id} - {sup.name_first} {sup.name_last}") for sup in supervisors
                ]
                self.reports_to_var = tk.StringVar()
                combo = ttk.Combobox(
                    master,
                    textvariable=self.reports_to_var,
                    values=[label for _id, label in self.supervisor_choices],
                    state="readonly"
                )
                combo.grid(row=idx, column=1, padx=5, pady=2)
                # Pre-select for editing
                if self.employee and self.employee.reports_to_id:
                    for _id, label in self.supervisor_choices:
                        if str(_id) == str(self.employee.reports_to_id):
                            self.reports_to_var.set(label)
                            break
                else:
                    self.reports_to_var.set("")
                self.entries[label] = combo
            else:
                entry = ttk.Entry(master)
                entry.grid(row=idx, column=1, padx=5, pady=2)
                self.entries[label] = entry

        # Subclass-specific fields
        self.subfield_frame = ttk.Frame(master)
        self.subfield_frame.grid(row=len(labels), column=0, columnspan=2, pady=10)
        self.subfields = {}
        self.update_subfields()
        self.emp_type_var.trace_add("write", lambda *a: self.update_subfields())

        # NEW: Shift Assignment Section
        self.setup_shift_section(master, len(labels) + 1)

        # Prefill for editing
        if self.employee:
            self.entries["Employee ID"].insert(0, self.employee.employee_id)
            self.entries["First Name"].insert(0, self.employee.name_first)
            self.entries["Last Name"].insert(0, self.employee.name_last)
            self.entries["Hire Date"].insert(0, self.employee.hire_date)
            self.entries["Birthdate"].insert(0, self.employee.birthdate)
            # Reports To now handled above with dropdown
            if isinstance(self.employee, Supervisor):
                if "management_level" in self.subfields:
                    self.subfields["management_level"].insert(0, str(self.employee.management_level or ""))
            elif isinstance(self.employee, MaintenancePerson):
                if "maintenance_level" in self.subfields:
                    self.subfields["maintenance_level"].set(self.employee.maintenance_level or "")
                if "qualified_area" in self.subfields:
                    self.subfields["qualified_area"].insert(0, self.employee.qualified_area or "")

        return self.entries["Employee ID"]  # Focus

    def setup_shift_section(self, master, start_row):
        """Add shift assignment section to the form"""
        # Separator
        separator = ttk.Separator(master, orient='horizontal')
        separator.grid(row=start_row, column=0, columnspan=2, sticky='ew', pady=10)

        # Section header
        ttk.Label(master, text="Shift Assignment",
                  font=('TkDefaultFont', 10, 'bold')).grid(
            row=start_row + 1, column=0, columnspan=2, sticky='w', padx=5, pady=5)

        # Current shift display (for editing)
        if self.employee:
            current_schedule = EmployeeSchedule.get_current_schedule(session, self.employee.id)
            if current_schedule:
                current_shift_text = f"Current: {current_schedule.shift.shift_name}"
                if current_schedule.shift.description:
                    current_shift_text += f" - {current_schedule.shift.description}"
                current_shift_text += f" (Started: {current_schedule.effective_start_date})"
            else:
                current_shift_text = "Current: No shift assigned"

            ttk.Label(master, text=current_shift_text,
                      foreground='blue').grid(row=start_row + 2, column=0, columnspan=2, sticky='w', padx=5)

        # Shift selection
        ttk.Label(master, text="Assign Shift:").grid(row=start_row + 3, column=0, sticky='e', padx=5, pady=5)

        self.shift_var = tk.StringVar()
        self.shift_combo = ttk.Combobox(master, textvariable=self.shift_var,
                                        width=40, state='readonly')
        self.shift_combo.grid(row=start_row + 3, column=1, sticky='w', padx=5, pady=5)

        # Load shifts and set current selection
        self.load_shifts()

        # Bind to show shift details
        self.shift_combo.bind('<<ComboboxSelected>>', self.on_shift_selected)

        # Shift details display
        self.shift_details_var = tk.StringVar()
        self.shift_details_label = ttk.Label(master, textvariable=self.shift_details_var,
                                             foreground='gray', font=('TkDefaultFont', 8))
        self.shift_details_label.grid(row=start_row + 4, column=0, columnspan=2, sticky='w', padx=5)

    def load_shifts(self):
        """Load available shifts into the dropdown"""
        try:
            shifts = session.query(Shift).filter_by(is_active=True).all()
            shift_options = ["(No Change)" if self.employee else "(No Shift)"]

            for shift in shifts:
                option = shift.shift_name
                if shift.description:
                    option += f" - {shift.description}"
                shift_options.append(option)

            self.shift_combo['values'] = shift_options

            # Create mapping for later use
            self.shifts_dict = {}
            for shift in shifts:
                key = shift.shift_name
                if shift.description:
                    key += f" - {shift.description}"
                self.shifts_dict[key] = shift.id

            # Set default selection
            if self.employee:
                current_schedule = EmployeeSchedule.get_current_schedule(session, self.employee.id)
                if current_schedule:
                    current_key = current_schedule.shift.shift_name
                    if current_schedule.shift.description:
                        current_key += f" - {current_schedule.shift.description}"
                    if current_key in self.shifts_dict:
                        self.shift_var.set(current_key)
                        self.on_shift_selected()  # Show details
                    else:
                        self.shift_var.set("(No Change)")
                else:
                    self.shift_var.set("(No Change)")
            else:
                self.shift_var.set("(No Shift)")

        except Exception as e:
            print(f"Error loading shifts: {e}")
            self.shift_combo['values'] = ["(Error loading shifts)"]

    def on_shift_selected(self, event=None):
        """Show shift details when a shift is selected"""
        selected = self.shift_var.get()

        if selected in ["(No Shift)", "(No Change)", "(Error loading shifts)"]:
            self.shift_details_var.set("")
            return

        if selected not in self.shifts_dict:
            self.shift_details_var.set("")
            return

        try:
            shift_id = self.shifts_dict[selected]
            shift = session.get(Shift, shift_id)

            if not shift:
                self.shift_details_var.set("")
                return

            # Build details string
            details = f"Pattern: {shift.shift_pattern.title()}"

            if shift.shift_days:
                details += " | Schedule: "
                days_info = []
                for shift_day in sorted(shift.shift_days, key=lambda x: x.day_of_week):
                    day_name = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][shift_day.day_of_week]
                    time_info = f"{shift_day.scheduled_start_time.strftime('%H:%M')}-{shift_day.scheduled_end_time.strftime('%H:%M')}"

                    if shift.shift_pattern == 'biweekly':
                        week_prefix = f"W{shift_day.week_number}:"
                        days_info.append(f"{week_prefix}{day_name} {time_info}")
                    else:
                        days_info.append(f"{day_name} {time_info}")

                details += ", ".join(days_info)

            self.shift_details_var.set(details)

        except Exception as e:
            print(f"Error showing shift details: {e}")
            self.shift_details_var.set("Error loading shift details")

    def update_subfields(self):
        for child in self.subfield_frame.winfo_children():
            child.destroy()
        self.subfields = {}
        etype = self.emp_type_var.get() if hasattr(self, "emp_type_var") else "Employee"
        row = 0
        if etype == "Supervisor":
            ttk.Label(self.subfield_frame, text="Management Level").grid(row=row, column=0, sticky='e', padx=5)
            entry = ttk.Entry(self.subfield_frame)
            entry.grid(row=row, column=1, padx=5)
            self.subfields["management_level"] = entry
        elif etype == "MaintenancePerson":
            ttk.Label(self.subfield_frame, text="Maintenance Level").grid(row=row, column=0, sticky='e', padx=5)
            maint_level_var = tk.StringVar()
            combo = ttk.Combobox(self.subfield_frame, textvariable=maint_level_var,
                                 values=self.MAINTENANCE_LEVELS, state="readonly")
            combo.grid(row=row, column=1, padx=5)
            self.subfields["maintenance_level"] = maint_level_var  # Save StringVar, not widget

            row += 1
            ttk.Label(self.subfield_frame, text="Qualified Area").grid(row=row, column=0, sticky='e', padx=5)
            entry2 = ttk.Entry(self.subfield_frame)
            entry2.grid(row=row, column=1, padx=5)
            self.subfields["qualified_area"] = entry2

    def save_shift_assignment(self, employee_id):
        """Save or update the shift assignment using class methods"""
        selected_shift = self.shift_var.get()

        try:
            if selected_shift == "(No Shift)":
                # End current assignments
                EmployeeSchedule.end_current_assignments(session, employee_id)
            elif selected_shift == "(No Change)":
                # Do nothing - keep current assignment
                pass
            elif selected_shift in self.shifts_dict:
                # Assign new shift
                shift_id = self.shifts_dict[selected_shift]
                EmployeeSchedule.assign_shift(
                    session,
                    employee_id,
                    shift_id,
                    notes="Assigned via employee form"
                )

        except Exception as e:
            raise Exception(f"Could not save shift assignment: {e}")

    def apply(self):
        # Gather the basic form fields
        self.result = {label: entry.get() for label, entry in self.entries.items()}

        # Convert supervisor name/id label to just the ID (for Reports To)
        selected_label = self.reports_to_var.get()
        for _id, label in self.supervisor_choices:
            if label == selected_label:
                self.result["Reports To ID"] = str(_id) if _id else ""
                break

        # Add employee type
        self.result["emp_type"] = self.emp_type_var.get()

        # Gather subclass-specific fields (handle StringVar for maintenance_level)
        for k, v in self.subfields.items():
            if hasattr(v, "get"):
                self.result[k] = v.get()
            else:
                self.result[k] = v

        # Store shift assignment info for later processing
        self.result["selected_shift"] = self.shift_var.get()

class MultiUserLoginDialog(simpledialog.Dialog):
    """Login dialog that authenticates against users_auth table."""
    def __init__(self, parent, title, session):
        self.session = session
        self.current_user = None
        super().__init__(parent, title)

    def body(self, master):
        ttk.Label(master, text="Username:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(master, text="Password:").grid(row=1, column=0, sticky="e", padx=5, pady=5)

        self.u_var = tk.StringVar()
        self.p_var = tk.StringVar()

        self.u_entry = ttk.Entry(master, textvariable=self.u_var)
        self.p_entry = ttk.Entry(master, show="*", textvariable=self.p_var)

        self.u_entry.grid(row=0, column=1, padx=5, pady=5)
        self.p_entry.grid(row=1, column=1, padx=5, pady=5)

        return self.u_entry  # initial focus

    def validate(self):
        u = (self.u_var.get() or "").strip()
        p = self.p_var.get() or ""

        if not u or not p:
            messagebox.showerror("Login Failed", "Username and password are required.")
            return False

        try:
            user = self.session.query(UserAuth).filter_by(username=u, is_active=True).first()
            if not user:
                messagebox.showerror("Login Failed", "Invalid username or inactive user.")
                return False
            if not verify_password(p, user.salt, user.password_hash):
                messagebox.showerror("Login Failed", "Invalid username or password.")
                return False

            self.current_user = user
            return True
        except Exception as e:
            error_id(f"Login error for '{u}': {e}", request_id)
            messagebox.showerror("Login Error", f"An error occurred: {e}")
            return False

    def apply(self):
        pass

class ManageUsersDialog(tk.Toplevel):
    """
    Admin-only user management UI for the users_auth table.
    Features:
      - List users
      - Create user (username, password, role)
      - Edit user (username, role, is_active)
      - Reset password
      - Activate/Deactivate user
    """
    ROLES = ["admin", "manager", "user"]

    def __init__(self, parent, session):
        super().__init__(parent)
        self.title("Manage Users")
        self.session = session
        self.geometry("700x420")
        self.resizable(True, True)

        # Top controls
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="🔐 User Administration", font=("TkDefaultFont", 12, "bold")).pack(side="left")

        # Table
        table_frame = ttk.Frame(self, padding=(10, 0))
        table_frame.pack(fill="both", expand=True)

        cols = ("id", "username", "role", "is_active", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse", height=12)
        for c, w in zip(cols, (60, 200, 100, 80, 200)):
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)

        vscroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vscroll.set)
        vscroll.pack(side="right", fill="y")

        # Buttons
        btns = ttk.Frame(self, padding=10)
        btns.pack(fill="x")

        ttk.Button(btns, text="➕ Create", command=self.create_user).pack(side="left", padx=5)
        ttk.Button(btns, text="✏️ Edit", command=self.edit_user).pack(side="left", padx=5)
        ttk.Button(btns, text="🔑 Reset Password", command=self.reset_password).pack(side="left", padx=5)
        ttk.Button(btns, text="⏻ Activate/Deactivate", command=self.toggle_active).pack(side="left", padx=5)
        ttk.Button(btns, text="🔄 Refresh", command=self.refresh).pack(side="left", padx=5)

        ttk.Button(btns, text="Close", command=self.destroy).pack(side="right")

        self.refresh()

    # ---------- helpers ----------
    def _selected_user(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select User", "Please select a user from the list.")
            return None
        uid = int(self.tree.item(sel[0])["values"][0])
        return self.session.query(UserAuth).get(uid)

    def refresh(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            users = self.session.query(UserAuth).order_by(UserAuth.username.asc()).all()
            for u in users:
                self.tree.insert(
                    "",
                    "end",
                    iid=str(u.id),
                    values=(u.id, u.username, u.role, "Yes" if u.is_active else "No", str(u.created_at)),
                )
        except Exception as e:
            error_id(f"Failed to load users: {e}", request_id)
            messagebox.showerror("Error", f"Failed to load users: {e}")

    # ---------- actions ----------
    def create_user(self):
        dlg = UserEditorDialog(self, title="Create User", role_default="user")
        result = dlg.result
        if not result:
            return
        username = (result.get("username") or "").strip()
        role = result.get("role") or "user"
        password = result.get("password") or ""

        if not username or not password:
            messagebox.showerror("Missing", "Username and password are required.")
            return

        try:
            # ensure unique username
            if self.session.query(UserAuth).filter_by(username=username).first():
                messagebox.showerror("Duplicate", f"Username '{username}' already exists.")
                return

            salt = make_salt()
            phash = hash_password(password, salt)
            u = UserAuth(username=username, password_hash=phash, salt=salt, role=role, is_active=True)
            self.session.add(u)
            self.session.commit()
            info_id(f"User '{username}' created.", request_id)
            self.refresh()
        except Exception as e:
            self.session.rollback()
            error_id(f"Create user failed: {e}", request_id)
            messagebox.showerror("Error", f"Create user failed: {e}")

    def edit_user(self):
        user = self._selected_user()
        if not user:
            return
        dlg = UserEditorDialog(self, title="Edit User", username_default=user.username, role_default=user.role,
                               allow_password=False, allow_username_edit=True, is_active=user.is_active)
        result = dlg.result
        if not result:
            return

        new_username = (result.get("username") or "").strip()
        new_role = (result.get("role") or user.role).lower()
        new_active = bool(result.get("is_active"))

        if not new_username:
            messagebox.showerror("Missing", "Username is required.")
            return

        try:
            # prevent duplication when changing username
            if new_username != user.username and self.session.query(UserAuth).filter_by(username=new_username).first():
                messagebox.showerror("Duplicate", f"Username '{new_username}' already exists.")
                return

            # guard: don't let admin deactivate themselves here if desired (optional)
            user.username = new_username
            user.role = new_role
            user.is_active = new_active
            self.session.commit()
            info_id(f"User '{new_username}' updated.", request_id)
            self.refresh()
        except Exception as e:
            self.session.rollback()
            error_id(f"Edit user failed: {e}", request_id)
            messagebox.showerror("Error", f"Edit user failed: {e}")

    def reset_password(self):
        user = self._selected_user()
        if not user:
            return

        p1 = simpledialog.askstring("Reset Password", f"Enter new password for '{user.username}':", show="*")
        if p1 is None:
            return
        p2 = simpledialog.askstring("Reset Password", "Confirm new password:", show="*")
        if p2 is None:
            return
        if p1 != p2:
            messagebox.showerror("Mismatch", "Passwords do not match.")
            return

        try:
            salt = make_salt()
            phash = hash_password(p1, salt)
            user.salt = salt
            user.password_hash = phash
            self.session.commit()
            info_id(f"Password reset for '{user.username}'.", request_id)
            messagebox.showinfo("Success", "Password updated.")
        except Exception as e:
            self.session.rollback()
            error_id(f"Reset password failed: {e}", request_id)
            messagebox.showerror("Error", f"Reset password failed: {e}")

    def toggle_active(self):
        user = self._selected_user()
        if not user:
            return
        try:
            user.is_active = not user.is_active
            self.session.commit()
            state = "activated" if user.is_active else "deactivated"
            info_id(f"User '{user.username}' {state}.", request_id)
            self.refresh()
        except Exception as e:
            self.session.rollback()
            error_id(f"Toggle active failed: {e}", request_id)
            messagebox.showerror("Error", f"Toggle active failed: {e}")


class UserEditorDialog(simpledialog.Dialog):
    """
    Small dialog to create/update a user.
    If allow_password is False, hides password fields (used for editing).
    """
    def __init__(self, parent, title="User", username_default="", role_default="user",
                 allow_password=True, allow_username_edit=True, is_active=True):
        self.username_default = username_default
        self.role_default = role_default
        self.allow_password = allow_password
        self.allow_username_edit = allow_username_edit
        self.is_active_default = is_active
        self.result = None
        super().__init__(parent, title)

    def body(self, master):
        r = 0
        ttk.Label(master, text="Username:").grid(row=r, column=0, sticky="e", padx=5, pady=5)
        self.u_var = tk.StringVar(value=self.username_default)
        self.u_entry = ttk.Entry(master, textvariable=self.u_var, state=("normal" if self.allow_username_edit else "disabled"))
        self.u_entry.grid(row=r, column=1, padx=5, pady=5, sticky="w")
        r += 1

        ttk.Label(master, text="Role:").grid(row=r, column=0, sticky="e", padx=5, pady=5)
        self.role_var = tk.StringVar(value=self.role_default)
        self.role_cb = ttk.Combobox(master, textvariable=self.role_var, values=ManageUsersDialog.ROLES, state="readonly")
        self.role_cb.grid(row=r, column=1, padx=5, pady=5, sticky="w")
        r += 1

        if self.allow_password:
            ttk.Label(master, text="Password:").grid(row=r, column=0, sticky="e", padx=5, pady=5)
            self.p1_var = tk.StringVar()
            ttk.Entry(master, textvariable=self.p1_var, show="*").grid(row=r, column=1, padx=5, pady=5, sticky="w")
            r += 1

            ttk.Label(master, text="Confirm Password:").grid(row=r, column=0, sticky="e", padx=5, pady=5)
            self.p2_var = tk.StringVar()
            ttk.Entry(master, textvariable=self.p2_var, show="*").grid(row=r, column=1, padx=5, pady=5, sticky="w")
            r += 1

        # is_active (only for edit)
        if not self.allow_password:
            self.active_var = tk.BooleanVar(value=self.is_active_default)
            ttk.Checkbutton(master, text="Active", variable=self.active_var).grid(row=r, column=1, padx=5, pady=5, sticky="w")
            r += 1

        return self.u_entry

    def validate(self):
        username = (self.u_var.get() or "").strip()
        role = (self.role_var.get() or "user").lower()
        if not username:
            messagebox.showerror("Missing", "Username is required.")
            return False
        if role not in ManageUsersDialog.ROLES:
            messagebox.showerror("Invalid", "Role must be one of: admin, manager, user.")
            return False

        if self.allow_password:
            p1 = self.p1_var.get() or ""
            p2 = self.p2_var.get() or ""
            if not p1:
                messagebox.showerror("Missing", "Password is required.")
                return False
            if p1 != p2:
                messagebox.showerror("Mismatch", "Passwords do not match.")
                return False

        return True

    def apply(self):
        data = {
            "username": (self.u_var.get() or "").strip(),
            "role": (self.role_var.get() or "user").lower(),
        }
        if self.allow_password:
            data["password"] = self.p1_var.get()
        else:
            data["is_active"] = bool(self.active_var.get())
        self.result = data


class EmployeeViewerApp:
    def __init__(self, root, current_user):
        self.current_user = current_user
        self.role = (getattr(current_user, 'role', 'user') or 'user').lower()

        self.root = root
        self.root.title(f"Maintenance Skills Database — {self.current_user.username} ({self.role})")

        # Main notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)

        # ----------------- Employees Tab -----------------
        self.employee_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.employee_tab, text="Employees")
        self.setup_employee_table(parent=self.employee_tab)
        self.setup_buttons(parent=self.employee_tab)

        # Role-based UI gating: basic 'user' cannot add/edit/delete
        if self.role == "user":
            for child in self.employee_tab.winfo_children():
                if isinstance(child, ttk.Frame):
                    for btn in child.winfo_children():
                        try:
                            if isinstance(btn, ttk.Button) and btn.cget("text") in {"Add Employee", "Edit Employee", "Delete Employee"}:
                                btn.state(["disabled"])
                        except Exception:
                            pass

        try:
            self.refresh_employee_list()
        except Exception as e:
            error_id(f"Initial employee list load failed: {e}", request_id)

        # ----------------- Step-Up Eval Tab -----------------
        self.step_up_eval_tab = StepUpEvalTab(self.notebook, session)
        self.notebook.add(self.step_up_eval_tab, text="Step-Up Eval")

        # ----------------- Competency Assignment Form Tab -----------------
        self.competency_assignment_tab = CompetencyAssignmentFormTab(self.notebook, session)
        self.notebook.add(self.competency_assignment_tab, text="Competency Assignment Form")

        # ----------------- Attendance & Shifts Tab -----------------
        # FIX: Wrap non-widget logic class with a real Frame for the Notebook
        self.attendance_shift_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.attendance_shift_tab, text="Attendance & Shifts")
        # Build the AttendanceShift UI inside the frame; keep a reference if the class exposes methods
        # ----------------- Attendance & Shifts Tab -----------------
        # Pass the NOTEBOOK to AttendanceShiftTab; it will add its own frame internally.
        self.attendance_shift_ui = AttendanceShiftTab(self.notebook, session)
        # ----------------- Skill Category CRUD Tabs -----------------
        self.technical_category_tab = SkillCategoryCrudTab(self.notebook, session, "TechnicalSkillCategory")
        self.notebook.add(self.technical_category_tab, text="Technical Skill Categories")

        self.mechanical_subcat_tab = SkillCategoryCrudTab(self.notebook, session, "MechanicalSubCategory")
        self.notebook.add(self.mechanical_subcat_tab, text="Mechanical Subcategories")

        self.electrical_subcat_tab = SkillCategoryCrudTab(self.notebook, session, "ElectricalSubCategory")
        self.notebook.add(self.electrical_subcat_tab, text="Electrical Subcategories")

        self.tool_type_tab = SkillCategoryCrudTab(self.notebook, session, "ToolType")
        self.notebook.add(self.tool_type_tab, text="Tool Types")

        # NEW: Operational Types tab
        self.operational_type_tab = SkillCategoryCrudTab(self.notebook, session, "OperationalType")
        self.notebook.add(self.operational_type_tab, text="Operational Types")

        # ----------------- Admin Menu (admins only) -----------------
        if self.role == "admin":
            self._setup_admin_menu()

        # Tab change bindings
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    # ----------------- Menus -----------------
    def _setup_admin_menu(self):
        """Create/attach an Admin menu with Manage Users… (admins only)."""
        # 1) Get an existing menubar if valid, else create a new one
        menubar = None
        try:
            existing_name = self.root.cget("menu")  # Tcl name or ''
        except Exception:
            existing_name = ""

        if existing_name:
            try:
                candidate = self.root.nametowidget(existing_name)
                if isinstance(candidate, tk.Menu):
                    menubar = candidate
            except Exception:
                menubar = None

        if menubar is None:
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)

        # 2) Check if an "Admin" cascade already exists; if not, add it
        admin_menu = None
        try:
            end_idx = menubar.index("end")
        except Exception:
            end_idx = None

        if isinstance(end_idx, int):
            for i in range(end_idx + 1):
                try:
                    if menubar.type(i) == "cascade":
                        if menubar.entrycget(i, "label") == "Admin":
                            # Get the submenu widget bound to this cascade
                            submenu_name = menubar.entrycget(i, "menu")
                            admin_menu = menubar.nametowidget(submenu_name)
                            break
                except Exception:
                    pass

        if admin_menu is None:
            admin_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Admin", menu=admin_menu)

        # 3) Ensure we have exactly one "Manage Users…" command (dedupe then add)
        try:
            end2 = admin_menu.index("end")
        except Exception:
            end2 = None

        if isinstance(end2, int):
            for i in range(end2, -1, -1):
                try:
                    if admin_menu.type(i) == "command" and admin_menu.entrycget(i, "label") == "Manage Users…":
                        admin_menu.delete(i)
                except Exception:
                    pass

        admin_menu.add_command(label="Manage Users…", command=lambda: ManageUsersDialog(self.root, session))

    # ----------------- Tab Events -----------------
    def on_tab_changed(self, event):
        selected_tab = event.widget.select()
        tab_text = event.widget.tab(selected_tab, "text")

        # Keep this resilient if some tabs are commented out
        if tab_text == "Competency Assignment Form":
            if hasattr(self, "competency_assignment_tab") and hasattr(self.competency_assignment_tab, "refresh_dropdowns"):
                try:
                    self.competency_assignment_tab.refresh_dropdowns()
                except Exception as e:
                    error_id(f"CompetencyAssignmentFormTab refresh failed: {e}", request_id)

        elif tab_text == "Skills Matrix Assignment":
            # Only run if you later re-enable the Skills Matrix tab
            if hasattr(self, "skills_matrix_tab"):
                try:
                    if hasattr(self.skills_matrix_tab, "populate_skill_combos"):
                        self.skills_matrix_tab.populate_skill_combos()
                    if hasattr(self.skills_matrix_tab, "refresh_tasks"):
                        self.skills_matrix_tab.refresh_tasks()
                except Exception as e:
                    error_id(f"SkillsMatrixAssignmentTab refresh failed: {e}", request_id)

        elif tab_text == "Employees":
            # Keep employee table fresh when coming back
            try:
                self.refresh_employee_list()
            except Exception as e:
                error_id(f"Employee list refresh on tab change failed: {e}", request_id)

    # ----------------- Employees Table -----------------
    def setup_employee_table(self, parent):
        columns = (
            'id', 'employee_id', 'name_first', 'name_last', 'hire_date',
            'birthdate', 'status', 'employee_type', 'reports_to_id'
        )
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill='both', expand=True)
        self.tree = ttk.Treeview(frame, columns=columns, show='headings', height=20)
        for col in columns:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            self.tree.column(col, width=110 if col == 'id' else 120, anchor=tk.W)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)

    def setup_buttons(self, parent):
        btn_frame = ttk.Frame(parent, padding=10)
        btn_frame.pack(fill='x')
        ttk.Button(btn_frame, text="Add Employee", command=self.add_employee).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Edit Employee", command=self.edit_employee).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Employee", command=self.delete_employee).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_employee_list).pack(side='left', padx=5)

    def get_selected_employee_id(self):
        selected = self.tree.selection()
        if not selected:
            return None
        return self.tree.item(selected[0])['values'][0]

    def refresh_employee_list(self):
        try:
            for row in self.tree.get_children():
                self.tree.delete(row)
            employees = session.query(Employee).all()
            for emp in employees:
                self.tree.insert('', 'end', values=(
                    emp.id, emp.employee_id, emp.name_first, emp.name_last,
                    emp.hire_date, emp.birthdate, emp.status,
                    emp.employee_type, emp.reports_to_id
                ))
        except Exception as e:
            error_id(f"refresh_employee_list failed: {e}", request_id)
            messagebox.showerror("Error", f"Could not refresh employees: {e}")

    # ----------------- Employee CRUD -----------------
    def add_employee(self):
        dlg = EmployeeForm(self.root, "Add Employee")
        if not getattr(dlg, "result", None):
            return

        data = dlg.result
        etype = data.get("emp_type", "Employee")
        if not data.get('Employee ID'):
            messagebox.showerror("Error", "Employee ID is required.")
            return

        # Create employee (existing code paths)
        if etype == "Supervisor":
            new_emp = Supervisor(
                employee_id=data['Employee ID'],
                name_first=data['First Name'],
                name_last=data['Last Name'],
                hire_date=data['Hire Date'],
                birthdate=data['Birthdate'],
                status=data['Status'],
                employee_type=etype,
                reports_to_id=int(data['Reports To ID']) if data.get('Reports To ID') else None,
                management_level=int(data.get("management_level") or 0)
            )
        elif etype == "MaintenancePerson":
            new_emp = MaintenancePerson(
                employee_id=data['Employee ID'],
                name_first=data['First Name'],
                name_last=data['Last Name'],
                hire_date=data['Hire Date'],
                birthdate=data['Birthdate'],
                status=data['Status'],
                employee_type=etype,
                reports_to_id=int(data['Reports To ID']) if data.get('Reports To ID') else None,
                maintenance_level=data.get("maintenance_level"),
                qualified_area=data.get("qualified_area")
            )
        else:
            new_emp = Employee(
                employee_id=data['Employee ID'],
                name_first=data['First Name'],
                name_last=data['Last Name'],
                hire_date=data['Hire Date'],
                birthdate=data['Birthdate'],
                status=data['Status'],
                employee_type=etype,
                reports_to_id=int(data['Reports To ID']) if data.get('Reports To ID') else None
            )

        session.add(new_emp)
        try:
            session.commit()

            # Save shift assignment after employee is created
            if hasattr(dlg, "save_shift_assignment"):
                dlg.save_shift_assignment(new_emp.id)
                session.commit()

            self.refresh_employee_list()
            messagebox.showinfo("Success", f"Employee {new_emp.employee_id} added successfully!")
        except Exception as e:
            session.rollback()
            error_id(f"add_employee failed: {e}", request_id)
            messagebox.showerror("Error", f"Could not add employee: {e}")

    def edit_employee(self):
        emp_id = self.get_selected_employee_id()
        if emp_id is None:
            messagebox.showwarning("Select Employee", "Please select an employee to edit.")
            return

        emp = session.get(Employee, emp_id)
        if not emp:
            messagebox.showerror("Error", f"Employee id {emp_id} not found.")
            return

        dlg = EmployeeForm(self.root, "Edit Employee", employee=emp)
        if not getattr(dlg, "result", None):
            return

        data = dlg.result
        # Update employee fields (existing code)
        emp.employee_id = data['Employee ID']
        emp.name_first = data['First Name']
        emp.name_last = data['Last Name']
        emp.hire_date = data['Hire Date']
        emp.birthdate = data['Birthdate']
        emp.status = data['Status']
        emp.employee_type = data['emp_type']
        emp.reports_to_id = int(data['Reports To ID']) if data.get('Reports To ID') else None

        if isinstance(emp, Supervisor):
            emp.management_level = int(data.get("management_level") or 0)
        elif isinstance(emp, MaintenancePerson):
            emp.maintenance_level = data.get("maintenance_level")
            emp.qualified_area = data.get("qualified_area")

        try:
            session.commit()

            # Save shift assignment after employee is updated
            if hasattr(dlg, "save_shift_assignment"):
                dlg.save_shift_assignment(emp.id)
                session.commit()

            self.refresh_employee_list()
            messagebox.showinfo("Success", f"Employee {emp.employee_id} updated successfully!")
        except Exception as e:
            session.rollback()
            error_id(f"edit_employee failed: {e}", request_id)
            messagebox.showerror("Error", f"Could not update employee: {e}")

    def delete_employee(self):
        emp_id = self.get_selected_employee_id()
        if emp_id is None:
            messagebox.showwarning("Select Employee", "Please select an employee to delete.")
            return

        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected employee?"):
            return

        emp = session.get(Employee, emp_id)
        if not emp:
            messagebox.showerror("Error", f"Employee id {emp_id} not found.")
            return

        try:
            session.delete(emp)
            session.commit()
            self.refresh_employee_list()
            messagebox.showinfo("Deleted", f"Employee {emp.employee_id} deleted.")
        except Exception as e:
            session.rollback()
            error_id(f"delete_employee failed: {e}", request_id)
            messagebox.showerror("Error", f"Could not delete employee: {e}")



class SkillTaskCrudTab(ttk.Frame):
    def __init__(self, parent, session, skill_type, skills_matrix_tab=None):
        super().__init__(parent)
        self.session = session
        self.skill_type = skill_type
        self.skills_matrix_tab = skills_matrix_tab

        if skill_type == "Mechanical":
            self.TaskModel = MechanicalTask
            self.columns = ["competency_name", "description", "proficiency_level", "task_action", "task_object", "verification_method"]
        elif skill_type == "Electrical":
            self.TaskModel = ElectricalTask
            self.columns = ["competency_name", "description", "proficiency_level", "task_action", "task_object", "verification_method"]
        elif skill_type == "Tool":
            self.TaskModel = ToolTask
            self.columns = ["competency_name", "description", "proficiency_level", "task_action", "task_object", "verification_method"]
        elif skill_type == "Operational":
            self.TaskModel = OperationalTask
            self.columns = ["competency_name", "description", "proficiency_level", "task_action", "task_object",
                            "verification_method", "operation_type", "machine_type"]

        else:
            raise ValueError("Unknown skill type")

        ttk.Label(self, text=f"{skill_type} Tasks").pack(anchor="w", padx=5, pady=5)

        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", selectmode="browse", height=15)
        for col in self.columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=140)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Add", command=self.add_task).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_task).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_task).pack(side="left", padx=5)

        self.refresh_task_list()

    def refresh_task_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        tasks = self.session.query(self.TaskModel).all()
        for t in tasks:
            self.tree.insert('', 'end', iid=t.id, values=[getattr(t, col) for col in self.columns])

    def add_task(self):
        values = self.open_task_dialog()
        if not values:
            return
        t = self.TaskModel(**values)
        self.session.add(t)
        try:
            self.session.commit()
            self.refresh_task_list()
            if self.skills_matrix_tab:
                self.skills_matrix_tab.refresh_tasks()
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Could not add task: {e}")

    def edit_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select a task to edit.")
            return
        task_id = int(selected[0])
        t = self.session.query(self.TaskModel).get(task_id)
        initial = t  # Pass the ORM object directly
        values = self.open_task_dialog(initial)
        if not values:
            return
        for k, v in values.items():
            setattr(t, k, v)
        try:
            self.session.commit()
            self.refresh_task_list()
            if self.skills_matrix_tab:
                self.skills_matrix_tab.refresh_tasks()
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Could not edit task: {e}")

    def delete_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select a task to delete.")
            return
        task_id = int(selected[0])
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this task?"):
            return
        t = self.session.query(self.TaskModel).get(task_id)
        self.session.delete(t)
        try:
            self.session.commit()
            self.refresh_task_list()
            if self.skills_matrix_tab:
                self.skills_matrix_tab.refresh_tasks()
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Could not delete task: {e}")

    def open_task_dialog(self, initial=None):
        dlg = tk.Toplevel(self)
        dlg.title(f"{'Edit' if initial else 'Add'} {self.skill_type} Task")

        # Competency Combo
        all_comps = self.session.query(self.TaskModel.competency_name, self.TaskModel.description).distinct().all()
        comp_names = sorted(set([c[0] for c in all_comps if c[0]]))
        all_comps = self.session.query(self.TaskModel.competency_name, self.TaskModel.description).distinct().all()
        comp_names = sorted(set([c[0] for c in all_comps if c[0]]))
        comp_map = {c[0]: c[1] for c in all_comps if c[0]}

        ttk.Label(dlg, text="Competency Name:").grid(row=0, column=0, sticky="e")
        comp_var = tk.StringVar()
        comp_cb = ttk.Combobox(dlg, textvariable=comp_var, values=comp_names)
        comp_cb.grid(row=0, column=1, padx=5, pady=3)
        if initial:
            comp_var.set(getattr(initial, "competency_name", ""))

        ttk.Label(dlg, text="Description:").grid(row=1, column=0, sticky="e")
        desc_var = tk.StringVar()
        desc_entry = ttk.Entry(dlg, textvariable=desc_var, width=35)
        desc_entry.grid(row=1, column=1, padx=5, pady=3)
        if initial:
            desc_var.set(getattr(initial, "description", ""))

        def on_comp_selected(event):
            name = comp_var.get()
            desc = comp_map.get(name, "")
            desc_var.set(desc)

        comp_cb.bind("<<ComboboxSelected>>", on_comp_selected)

        # Base fields for all skills
        labels = [
            ("proficiency_level", "Proficiency Level"),
            ("task_action", "Task Action"),
            ("task_object", "Task Object"),
            ("verification_method", "Verification Method"),
        ]
        # Add extra fields for Operational tasks
        if self.skill_type == "Operational":
            labels += [
                ("operation_type", "Operation Type"),
                ("machine_type", "Machine Type"),
            ]
        entries = {}
        for i, (col, label) in enumerate(labels, start=2):
            ttk.Label(dlg, text=label + ":").grid(row=i, column=0, sticky="e")
            e = ttk.Entry(dlg, width=35)
            e.grid(row=i, column=1, padx=5, pady=3)
            if initial:
                e.insert(0, getattr(initial, col, ""))
            entries[col] = e

        # Level checkboxes (default Level 1 to checked)
        level_vars = {
            "required_for_level_1": tk.BooleanVar(
                value=True if not initial else bool(getattr(initial, "required_for_level_1", False))),
            "required_for_level_2": tk.BooleanVar(
                value=bool(getattr(initial, "required_for_level_2", False)) if initial else False),
            "required_for_level_3": tk.BooleanVar(
                value=bool(getattr(initial, "required_for_level_3", False)) if initial else False),
            "required_for_maintenance_tech": tk.BooleanVar(
                value=bool(getattr(initial, "required_for_maintenance_tech", False)) if initial else False),
        }
        level_labels = [
            ("required_for_level_1", "Level 1"),
            ("required_for_level_2", "Level 2"),
            ("required_for_level_3", "Level 3"),
            ("required_for_maintenance_tech", "Maintenance Tech"),
        ]
        levels_row = len(labels) + 2
        ttk.Label(dlg, text="Required for Levels:").grid(row=levels_row, column=0, sticky="ne", pady=(10, 0))
        level_frame = ttk.Frame(dlg)
        level_frame.grid(row=levels_row, column=1, sticky="w", pady=(10, 0))
        for i, (field, label) in enumerate(level_labels):
            chk = ttk.Checkbutton(level_frame, text=label, variable=level_vars[field])
            chk.grid(row=0, column=i, padx=5, sticky="w")

        result = {}

        def on_ok():
            result["competency_name"] = comp_var.get().strip()
            result["description"] = desc_var.get().strip()
            for col, _ in labels:
                result[col] = entries[col].get().strip()
            for field, var in level_vars.items():
                result[field] = var.get()
            dlg.destroy()

        ttk.Button(dlg, text="OK", command=on_ok).grid(row=levels_row + 1, column=0, columnspan=2, pady=10)
        dlg.grab_set()
        dlg.wait_window()
        if not result or not result.get("competency_name"):
            return None
        return result

class SkillCategoryCrudTab(ttk.Frame):
    def __init__(self, parent, session, category_type):
        super().__init__(parent)
        self.session = session
        self.category_type = category_type

        # Map category type to model, columns, fields, labels
        if category_type == "TechnicalSkillCategory":
            self.CategoryModel = TechnicalSkill
            self.display_columns = ["competency_name", "skill_category", "description"]
            self.dialog_fields = [
                ("competency_name", "Category Name", "Entry"),
                ("skill_category", "Skill Category", "Combo", ["Electrical", "Mechanical", "Tools"]),
                ("description", "Description", "Entry"),
            ]
            self.label_text = "Technical Skill Categories"
            self.help_text = "Create high-level technical skill categories (Electrical, Mechanical, Tools)"

        elif category_type == "MechanicalSubCategory":
            self.CategoryModel = MechanicalSkill
            # REMOVED: "mechanical_type" from display_columns
            self.display_columns = ["sub_category", "equipment_category", "description"]
            self.dialog_fields = [
                ("sub_category", "Mechanical System", "Combo",
                 ["Hydraulic Systems", "Pneumatic Systems", "Belt/Chain Drive", "Bearing Systems",
                  "Pump Systems", "Motor Systems", "Conveyor Systems"]),
                # REMOVED: ("mechanical_type", "Mechanical Type", "Entry"),
                ("equipment_category", "Equipment Category", "Entry"),
                ("description", "Description", "Entry"),
            ]
            self.label_text = "Mechanical Subcategories"
            self.help_text = "Create mechanical system subcategories that will populate the Competency Assignment Form dropdowns"

        elif category_type == "ElectricalSubCategory":
            self.CategoryModel = ElectricalSkill
            # REMOVED: "electrical_type" from display_columns
            self.display_columns = ["sub_category", "voltage_level", "description"]
            self.dialog_fields = [
                ("sub_category", "Electrical System", "Combo",
                 ["Low Voltage Wiring", "High Voltage Wiring", "Control Circuits & Sensors",
                  "VFDs", "MCC", "Motor Controls"]),
                ("voltage_level", "Voltage Level", "Combo", ["Low", "High", "Low/High"]),
                # REMOVED: ("electrical_type", "Electrical Type", "Entry"),
                ("description", "Description", "Entry"),
            ]
            self.label_text = "Electrical Subcategories"
            self.help_text = "Create electrical system subcategories that will populate the Competency Assignment Form dropdowns"

        elif category_type == "ToolType":
            self.CategoryModel = ToolSkill
            self.display_columns = ["tool_type", "primary_application", "description"]
            self.dialog_fields = [
                ("tool_type", "Tool Type", "Combo",
                 ["Hand Tools", "Power Tools", "Measuring Tools", "Test Equipment"]),
                ("primary_application", "Primary Application", "Combo",
                 ["Electrical", "Mechanical", "Universal"]),
                ("description", "Description", "Entry"),
            ]
            self.label_text = "Tool Types"
            self.help_text = "Create tool categories that will populate the Competency Assignment Form dropdowns"

        elif category_type == "OperationalType":
            self.CategoryModel = OperationalSkill
            self.display_columns = ["operation_type", "machine_type", "description"]
            self.dialog_fields = [
                ("operation_type", "Operation Type", "Combo",
                 ["Manual Mode", "Auto Mode", "Cleaning", "Lubrication", "Setup", "Changeover"]),
                ("machine_type", "Machine Type", "Entry"),
                ("description", "Description", "Entry"),
            ]
            self.label_text = "Operational Types"
            self.help_text = "Create operational categories that will populate the Competency Assignment Form dropdowns"

        else:
            raise ValueError("Unknown category type")

        # Create UI
        self.create_ui()
        self.refresh_category_list()

    def create_ui(self):
        # Title and description
        title_frame = ttk.Frame(self)
        title_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(title_frame, text=self.label_text,
                  font=('TkDefaultFont', 12, 'bold')).pack(anchor="w")
        ttk.Label(title_frame, text=self.help_text,
                  font=('TkDefaultFont', 9), foreground='gray').pack(anchor="w", pady=(2, 0))

        # Treeview
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.tree = ttk.Treeview(tree_frame, columns=self.display_columns, show="headings", height=12)
        for col in self.display_columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=170)

        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)

        self.tree.pack(side='left', fill="both", expand=True)
        scrollbar.pack(side='right', fill='y')

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Add", command=self.add_category).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Edit", command=self.edit_category).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_category).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_category_list).pack(side="left", padx=5)

    def refresh_category_list(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        # Filter by specific polymorphic identity to avoid inheritance issues
        if self.category_type == "MechanicalSubCategory":
            cats = self.session.query(self.CategoryModel).filter(
                self.CategoryModel.competency_type == 'mechanical'
            ).all()
        elif self.category_type == "ElectricalSubCategory":
            cats = self.session.query(self.CategoryModel).filter(
                self.CategoryModel.competency_type == 'electrical'
            ).all()
        elif self.category_type == "ToolType":
            cats = self.session.query(self.CategoryModel).filter(
                self.CategoryModel.competency_type == 'tools'
            ).all()
        elif self.category_type == "OperationalType":
            cats = self.session.query(self.CategoryModel).filter(
                self.CategoryModel.competency_type == 'operational'
            ).all()
        else:
            # For TechnicalSkillCategory, get only the base level
            cats = self.session.query(self.CategoryModel).filter(
                self.CategoryModel.competency_type == 'technical'
            ).all()

        for c in cats:
            values = []
            for col in self.display_columns:
                # Use getattr with a default value to handle missing attributes gracefully
                val = getattr(c, col, "")
                values.append(val if val is not None else "")
            self.tree.insert('', 'end', iid=c.id, values=values)

    def add_category(self):
        values = self.open_category_dialog()
        if not values:
            return

        # Set automatic fields based on category type
        if self.category_type == "MechanicalSubCategory":
            values["competency_name"] = f"Mechanical - {values.get('sub_category', '')}"
            values["skill_category"] = "Mechanical"
            values["competency_type"] = "mechanical"  # CRITICAL: Set polymorphic identity
            # REMOVED: Auto-set mechanical_type logic

        elif self.category_type == "ElectricalSubCategory":
            values["competency_name"] = f"Electrical - {values.get('sub_category', '')}"
            values["skill_category"] = "Electrical"
            values["competency_type"] = "electrical"  # CRITICAL: Set polymorphic identity
            # REMOVED: Auto-set electrical_type logic

        elif self.category_type == "ToolType":
            values["competency_name"] = f"Tools - {values.get('tool_type', '')}"
            values["skill_category"] = "Tools"
            values["competency_type"] = "tools"  # CRITICAL: Set polymorphic identity

        elif self.category_type == "OperationalType":
            values["competency_name"] = f"Operational - {values.get('operation_type', '')} - {values.get('machine_type', '')}"
            values["competency_type"] = "operational"  # CRITICAL: Set polymorphic identity

        elif self.category_type == "TechnicalSkillCategory":
            # For the base technical skill category
            values["competency_type"] = "technical"

        # Validate required fields
        required_fields = self.get_required_fields()
        for field in required_fields:
            if not values.get(field):
                messagebox.showerror("Missing Required Field", f"{field.replace('_', ' ').title()} is required.")
                return

        try:
            cat = self.CategoryModel(**values)
            self.session.add(cat)
            self.session.commit()
            self.refresh_category_list()
            messagebox.showinfo("Success", f"{self.label_text[:-1]} added successfully!")
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Could not add category: {e}")

    def edit_category(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select a category to edit.")
            return

        cat_id = int(selected[0])
        c = self.session.query(self.CategoryModel).get(cat_id)

        # Prepare initial values for dialog
        initial = {}
        for field_info in self.dialog_fields:
            col = field_info[0]
            initial[col] = getattr(c, col, "")

        values = self.open_category_dialog(initial)
        if not values:
            return

        # Update automatic fields
        if self.category_type == "MechanicalSubCategory":
            values["competency_name"] = f"Mechanical - {values.get('sub_category', '')}"
            values["skill_category"] = "Mechanical"
            values["competency_type"] = "mechanical"  # CRITICAL: Set polymorphic identity
            # REMOVED: Auto-set mechanical_type logic

        elif self.category_type == "ElectricalSubCategory":
            values["competency_name"] = f"Electrical - {values.get('sub_category', '')}"
            values["skill_category"] = "Electrical"
            values["competency_type"] = "electrical"  # CRITICAL: Set polymorphic identity
            # REMOVED: Auto-set electrical_type logic

        elif self.category_type == "ToolType":
            values["competency_name"] = f"Tools - {values.get('tool_type', '')}"
            values["skill_category"] = "Tools"
            values["competency_type"] = "tools"  # CRITICAL: Set polymorphic identity

        elif self.category_type == "OperationalType":
            values["competency_name"] = f"Operational - {values.get('operation_type', '')} - {values.get('machine_type', '')}"
            values["competency_type"] = "operational"  # CRITICAL: Set polymorphic identity

        elif self.category_type == "TechnicalSkillCategory":
            values["competency_type"] = "technical"

        # Validate required fields
        required_fields = self.get_required_fields()
        for field in required_fields:
            if not values.get(field):
                messagebox.showerror("Missing Required Field", f"{field.replace('_', ' ').title()} is required.")
                return

        try:
            for k, v in values.items():
                setattr(c, k, v)
            self.session.commit()
            self.refresh_category_list()
            messagebox.showinfo("Success", f"{self.label_text[:-1]} updated successfully!")
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Could not edit category: {e}")

    def delete_category(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Select a category to delete.")
            return

        cat_id = int(selected[0])
        if not messagebox.askyesno("Confirm Delete",
                                   "Are you sure you want to delete this category?\n\n"
                                   "Warning: This may affect existing competency assignments."):
            return

        try:
            c = self.session.query(self.CategoryModel).get(cat_id)
            self.session.delete(c)
            self.session.commit()
            self.refresh_category_list()
            messagebox.showinfo("Deleted", f"{self.label_text[:-1]} deleted successfully!")
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Could not delete category: {e}")

    def get_required_fields(self):
        """Return list of required fields based on category type"""
        if self.category_type == "TechnicalSkillCategory":
            return ["skill_category"]
        elif self.category_type == "MechanicalSubCategory":
            return ["sub_category"]
        elif self.category_type == "ElectricalSubCategory":
            return ["sub_category", "voltage_level"]
        elif self.category_type == "ToolType":
            return ["tool_type", "primary_application"]
        elif self.category_type == "OperationalType":
            return ["operation_type", "machine_type"]
        return []

    def open_category_dialog(self, initial=None):
        dlg = tk.Toplevel(self)
        dlg.title(f"{'Edit' if initial else 'Add'} {self.label_text[:-1]}")
        dlg.geometry("500x400")
        dlg.resizable(True, True)

        # Main frame with padding
        main_frame = ttk.Frame(dlg, padding=10)
        main_frame.pack(fill='both', expand=True)

        # Create a canvas and scrollbar for scrolling
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Add description
        if not initial:
            desc_text = {
                "TechnicalSkillCategory": "Create a high-level technical skill category.",
                "MechanicalSubCategory": "Create a mechanical system subcategory for competency assignments.",
                "ElectricalSubCategory": "Create an electrical system subcategory for competency assignments.",
                "ToolType": "Create a tool category for competency assignments.",
                "OperationalType": "Create an operational category for competency assignments."
            }
            desc_label = ttk.Label(scrollable_frame, text=desc_text.get(self.category_type, ""),
                                   font=('TkDefaultFont', 9), foreground='gray')
            desc_label.grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 15), padx=5)

        entries = {}
        row = 1  # Start from row 1 since row 0 is description

        for field_info in self.dialog_fields:
            col = field_info[0]
            label = field_info[1]
            field_type = field_info[2] if len(field_info) > 2 else "Entry"
            options = field_info[3] if len(field_info) > 3 else []

            # Create label
            ttk.Label(scrollable_frame, text=label + ":").grid(row=row, column=0, sticky="ne", pady=5, padx=(5, 0))

            # Create appropriate widget
            if field_type == "Combo":
                widget = ttk.Combobox(scrollable_frame, values=options, width=40)
                if initial and col in initial:
                    widget.set(str(initial[col]))
            elif field_type == "Text":
                widget = tk.Text(scrollable_frame, width=40, height=4)
                if initial and col in initial:
                    widget.insert('1.0', str(initial[col]))
            else:  # Entry
                widget = ttk.Entry(scrollable_frame, width=40)
                if initial and col in initial:
                    widget.insert(0, str(initial[col]))

            widget.grid(row=row, column=1, sticky="w", padx=(10, 5), pady=5)
            entries[col] = (widget, field_type)
            row += 1

        # Add examples/help text
        if not initial:
            examples_frame = ttk.LabelFrame(scrollable_frame, text="Examples", padding=5)
            examples_frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(15, 0), padx=5)

            examples = self.get_examples()
            if examples:
                example_text = tk.Text(examples_frame, height=4, width=60, font=('TkDefaultFont', 8))
                example_text.pack(fill='x', padx=5, pady=5)
                example_text.insert('1.0', examples)
                example_text.config(state='disabled')
            row += 1

        result = {}

        def on_ok():
            for col, (widget, field_type) in entries.items():
                if field_type == "Text":
                    result[col] = widget.get('1.0', tk.END).strip()
                else:
                    result[col] = widget.get().strip()
            dlg.destroy()

        def on_cancel():
            result.clear()
            dlg.destroy()

        # Buttons frame - use pack here since it's separate from the grid layout above
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(side='bottom', fill='x', pady=(10, 0))

        ttk.Button(button_frame, text="OK", command=on_ok).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side='left', padx=5)

        # Configure grid weights for scrollable_frame
        scrollable_frame.columnconfigure(1, weight=1)

        # Make dialog modal
        dlg.transient(self)
        dlg.grab_set()

        # Center the dialog
        dlg.update_idletasks()
        x = (dlg.winfo_screenwidth() // 2) - (dlg.winfo_width() // 2)
        y = (dlg.winfo_screenheight() // 2) - (dlg.winfo_height() // 2)
        dlg.geometry(f"+{x}+{y}")

        dlg.wait_window()
        return result if result else None

    def get_examples(self):
        """Return examples text for the dialog"""
        examples = {
            "MechanicalSubCategory":
                "• Hydraulic Systems - for hydraulic pump, cylinder, valve maintenance\n"
                "• Pump Systems - for solution pumps, transfer pumps, centrifugal pumps\n"
                "• Motor Systems - for AC motors, DC motors, servo motor maintenance\n"
                "• Conveyor Systems - for belt, chain, and roller conveyor maintenance",

            "ElectricalSubCategory":
                "• Control Circuits & Sensors + Low - for 24V control work\n"
                "• Motor Controls + High - for 480V motor starter work\n"
                "• VFDs + Low/High - for variable frequency drive installation\n"
                "• MCC + High - for motor control center maintenance",

            "ToolType":
                "• Measuring Tools + Mechanical - calipers, micrometers\n"
                "• Test Equipment + Electrical - multimeters, oscilloscopes\n"
                "• Hand Tools + Universal - wrenches, screwdrivers\n"
                "• Power Tools + Universal - drills, grinders",

            "OperationalType":
                "• Manual Mode + Bag Sealer - for manual operation of bag sealing equipment\n"
                "• Auto Mode + Filling Line - for automated operation of filling equipment\n"
                "• Cleaning + Conveyor Belt - for proper cleaning procedures\n"
                "• Changeover + Packaging Machine - for product changeover procedures"
        }
        return examples.get(self.category_type, "")

class CompetencyAssignmentFormTab(ttk.Frame):

    def __init__(self, parent, session):
        """
        Initialize the Competency Assignment Form Tab with scrollable support.

        This form supports both 'Proficiency' (Basic, Intermediate, Advanced)
        and 'Level' (Level 1, Level 2, etc.) fields as optional values.
        """
        super().__init__(parent)
        self.session = session
        self.current_checklist_task = None
        self.selected_assignment_id = None
        self.selected_assignment_type = None
        self.setup_editing_indicators()

        # Optionally initialize the dynamic vars (for later assignment in each section)
        self.proficiency_var = None  # Will be created per-section in dynamic form
        self.level_var = None  # Will be created per-section in dynamic form

        # CREATE SCROLLABLE CONTAINER FIRST
        self.create_scrollable_container()

        # Title
        title_label = ttk.Label(self.scrollable_frame, text="Competency Assignment Form",
                                font=('TkDefaultFont', 14, 'bold'))
        title_label.pack(anchor='w', padx=10, pady=(10, 15))

        # Section 1: Checklist Task Selection
        self.create_checklist_section(self.scrollable_frame)

        # -- Section: Current Task Details
        self.create_current_task_details_section(self.scrollable_frame)
        self.task_details_tree.bind('<<TreeviewSelect>>', self.on_task_details_row_selected)
        self.task_details_tree.bind('<Double-1>', self.on_task_details_tree_double_click)

        # Section 2: Competency Type Selection
        self.create_competency_type_section(self.scrollable_frame)

        # Section 3: Dynamic competency details (will be populated based on selection)
        self.create_dynamic_section(self.scrollable_frame)

        # Section 4: Task Definition
        self.create_task_section(self.scrollable_frame)

        # Section 5: Action buttons
        self.create_action_buttons(self.scrollable_frame)

        # Initialize form fields and dropdowns
        self.reset_form()
        self.populate_checklist_dropdowns()

    def create_scrollable_container(self):
        """Create a scrollable container for the entire form."""

        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind mousewheel scrolling
        self.bind_mousewheel()

    def bind_mousewheel(self):
        """Bind mousewheel scrolling to the canvas."""

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_to_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_from_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")

        # Bind when mouse enters the widget
        self.canvas.bind('<Enter>', _bind_to_mousewheel)
        self.canvas.bind('<Leave>', _unbind_from_mousewheel)

    def refresh_current_task_details(self):
        """Refresh the treeview showing all competencies and assignments for the selected checklist task."""
        # Clear old rows
        for row in self.task_details_tree.get_children():
            self.task_details_tree.delete(row)

        task = self.current_checklist_task
        if not task:
            return

        # 1. Competencies linked to this checklist task
        comp_links = self.session.query(ChecklistTaskCompetency).filter_by(checklist_task_id=task.id).all()
        for comp_link in comp_links:
            competency = self.session.query(CoreCompetency).get(comp_link.competency_id)
            if not competency:
                continue

            # For competencies, task fields are empty/N/A
            self.task_details_tree.insert("", "end",
                                          iid=f"comp_{competency.id}",
                                          values=(
                                              competency.competency_type.title(),
                                              competency.competency_name or "",
                                              getattr(competency, "level", ""),
                                              getattr(competency, "proficiency_level", ""),
                                              "N/A",  # Task Action
                                              "N/A",  # Task Object
                                              "N/A"  # Verification Method
                                          ),
                                          tags=("competency",)
                                          )

        # 2. Specific skill assignments for this checklist task
        assignments = self.get_task_implementations_for_checklist_task(task.id)
        for typ, task_obj in assignments:
            if task_obj:
                self.task_details_tree.insert("", "end",
                                              iid=f"task_{typ}_{task_obj.id}",
                                              values=(
                                                  f"{typ.title()} Task",
                                                  getattr(task_obj, "competency_name", "") or getattr(task_obj,
                                                                                                      "description",
                                                                                                      ""),
                                                  getattr(task_obj, "level", ""),
                                                  getattr(task_obj, "proficiency_level", ""),
                                                  getattr(task_obj, "task_action", ""),  # NEW
                                                  getattr(task_obj, "task_object", ""),  # NEW
                                                  getattr(task_obj, "verification_method", "")  # NEW
                                              ),
                                              tags=("task", typ)
                                              )

        # Update column headers to show they're editable
        try:
            for col, editable in self.editable_columns.items():
                if editable:
                    self.task_details_tree.heading(col, text=f"{col} ✏️")
        except:
            pass

    def edit_selected_assignment(self):
        """Edit the selected assignment by populating the form fields."""
        selected = self.task_details_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an entry to edit.")
            return

        item_id = selected[0]
        tags = self.task_details_tree.item(item_id, 'tags')

        try:
            if 'competency' in tags:
                # Editing a core competency
                comp_id = int(item_id.split('_')[1])
                competency = self.session.query(CoreCompetency).get(comp_id)
                if competency:
                    self.populate_form_for_competency_edit(competency)

            elif 'task' in tags:
                # Editing a specific task
                parts = item_id.split('_')
                task_type = parts[1]
                task_id = int(parts[2])

                if task_type == "mechanical":
                    task = self.session.query(MechanicalTask).get(task_id)
                    if task:
                        self.populate_form_for_mechanical_edit(task)
                elif task_type == "electrical":
                    task = self.session.query(ElectricalTask).get(task_id)
                    if task:
                        self.populate_form_for_electrical_edit(task)
                elif task_type == "tool":
                    task = self.session.query(ToolTask).get(task_id)
                    if task:
                        self.populate_form_for_tool_edit(task)
                elif task_type == "operational":
                    task = self.session.query(OperationalTask).get(task_id)
                    if task:
                        self.populate_form_for_operational_edit(task)

            # Store edit context
            self.selected_assignment_id = item_id
            self.selected_assignment_type = tags[1] if len(tags) > 1 else tags[0]

            messagebox.showinfo("Edit Mode",
                                "Form populated for editing. Make your changes and click 'Save Assignment'.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load assignment for editing: {e}")

    def delete_selected_assignment(self, event=None):
        """Delete the selected assignment."""
        selected = self.task_details_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an entry to delete.")
            return

        item_id = selected[0]
        item_values = self.task_details_tree.item(item_id, 'values')

        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete",
                                   f"Are you sure you want to delete:\n\n{item_values[0]}: {item_values[1]}\n\nThis action cannot be undone."):
            return

        tags = self.task_details_tree.item(item_id, 'tags')

        try:
            if 'competency' in tags:
                # Deleting a core competency link
                comp_id = int(item_id.split('_')[1])

                # Remove the ChecklistTaskCompetency link
                link = self.session.query(ChecklistTaskCompetency).filter_by(
                    checklist_task_id=self.current_checklist_task.id,
                    competency_id=comp_id
                ).first()

                if link:
                    self.session.delete(link)
                    # Note: We're not deleting the actual CoreCompetency record,
                    # just the link to this checklist task

            elif 'task' in tags:
                # Deleting a specific task
                parts = item_id.split('_')
                task_type = parts[1]
                task_id = int(parts[2])

                # Remove the TaskSkillAssignment link
                assignment = self.session.query(TaskSkillAssignment).filter_by(
                    checklist_task_id=self.current_checklist_task.id
                )

                if task_type == "mechanical":
                    assignment = assignment.filter_by(mechanical_task_id=task_id).first()
                    task_obj = self.session.query(MechanicalTask).get(task_id)
                elif task_type == "electrical":
                    assignment = assignment.filter_by(electrical_task_id=task_id).first()
                    task_obj = self.session.query(ElectricalTask).get(task_id)
                elif task_type == "tool":
                    assignment = assignment.filter_by(tool_task_id=task_id).first()
                    task_obj = self.session.query(ToolTask).get(task_id)
                elif task_type == "operational":
                    assignment = assignment.filter_by(operational_task_id=task_id).first()
                    task_obj = self.session.query(OperationalTask).get(task_id)

                if assignment:
                    self.session.delete(assignment)

                # Optionally delete the task object itself if not used elsewhere
                delete_task = messagebox.askyesno("Delete Task Object",
                                                  "Also delete the task definition itself?\n\n"
                                                  "Choose 'No' if this task might be used by other checklist items.")
                if delete_task and task_obj:
                    # Check if task is used elsewhere
                    other_assignments = self.session.query(TaskSkillAssignment).filter(
                        getattr(TaskSkillAssignment, f"{task_type}_task_id") == task_id,
                        TaskSkillAssignment.checklist_task_id != self.current_checklist_task.id
                    ).count()

                    if other_assignments > 0:
                        messagebox.showwarning("Cannot Delete",
                                               f"This task is used by {other_assignments} other checklist items and cannot be deleted.")
                    else:
                        self.session.delete(task_obj)

            self.session.commit()
            self.refresh_current_task_details()
            messagebox.showinfo("Success", "Assignment deleted successfully.")

        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to delete assignment: {e}")

    def populate_form_for_operational_edit(self, task):
        """Populate the form for editing an operational task."""
        # Set competency type to operational
        self.competency_type_var.set("operational")
        self.on_competency_type_selected()

        # Wait for dynamic section to be created
        self.after(100, lambda: self._populate_operational_fields(task))

    def _populate_operational_fields(self, task):
        """Helper to populate operational fields after dynamic section is created."""
        if 'operational' in self.dynamic_widgets:
            widgets = self.dynamic_widgets['operational']

            # Populate competency details
            widgets['competency_name'].set(task.competency_name or "")
            widgets['operation_type'].set(task.operation_type or "")
            widgets['machine_type'].set(task.machine_type or "")

            if 'level' in widgets:
                widgets['level'].set(getattr(task, 'level', "") or "")
            if 'proficiency' in widgets:
                widgets['proficiency'].set(getattr(task, 'proficiency_level', "") or "")

        # Populate task definition fields
        self.task_action_var.set(task.task_action or "")
        self.task_object_var.set(task.task_object or "")

        # Clear and set verification text
        self.verification_text.delete('1.0', tk.END)
        if task.verification_method:
            self.verification_text.insert('1.0', task.verification_method)

    def populate_form_for_mechanical_edit(self, task):
        """Populate the form for editing a mechanical task."""
        self.competency_type_var.set("mechanical")
        self.on_competency_type_selected()
        self.after(100, lambda: self._populate_mechanical_fields(task))

    def _populate_mechanical_fields(self, task):
        """Helper to populate mechanical fields after dynamic section is created."""
        if 'mechanical' in self.dynamic_widgets:
            widgets = self.dynamic_widgets['mechanical']

            widgets['competency_name'].set(task.competency_name or "")
            widgets['subcategory'].set(task.sub_category or "")
            widgets['equipment'].set(task.equipment_category or "")

            if 'level' in widgets:
                widgets['level'].set(getattr(task, 'level', "") or "")
            if 'proficiency' in widgets:
                widgets['proficiency'].set(getattr(task, 'proficiency_level', "") or "")

        self.task_action_var.set(task.task_action or "")
        self.task_object_var.set(task.task_object or "")

        self.verification_text.delete('1.0', tk.END)
        if task.verification_method:
            self.verification_text.insert('1.0', task.verification_method)

    def populate_form_for_electrical_edit(self, task):
        """Populate the form for editing an electrical task."""
        self.competency_type_var.set("electrical")
        self.on_competency_type_selected()
        self.after(100, lambda: self._populate_electrical_fields(task))

    def _populate_electrical_fields(self, task):
        """Helper to populate electrical fields after dynamic section is created."""
        if 'electrical' in self.dynamic_widgets:
            widgets = self.dynamic_widgets['electrical']

            widgets['competency_name'].set(task.competency_name or "")
            widgets['subcategory'].set(task.sub_category or "")
            widgets['voltage'].set(task.voltage_level or "")

            if 'level' in widgets:
                widgets['level'].set(getattr(task, 'level', "") or "")
            if 'proficiency' in widgets:
                widgets['proficiency'].set(getattr(task, 'proficiency_level', "") or "")

        self.task_action_var.set(task.task_action or "")
        self.task_object_var.set(task.task_object or "")

        self.verification_text.delete('1.0', tk.END)
        if task.verification_method:
            self.verification_text.insert('1.0', task.verification_method)

    def populate_form_for_tool_edit(self, task):
        """Populate the form for editing a tool task."""
        self.competency_type_var.set("tools")
        self.on_competency_type_selected()
        self.after(100, lambda: self._populate_tool_fields(task))

    def _populate_tool_fields(self, task):
        """Helper to populate tool fields after dynamic section is created."""
        if 'tools' in self.dynamic_widgets:
            widgets = self.dynamic_widgets['tools']

            widgets['competency_name'].set(task.competency_name or "")
            widgets['tool_type'].set(task.tool_type or "")
            widgets['application'].set(task.primary_application or "")

            if 'level' in widgets:
                widgets['level'].set(getattr(task, 'level', "") or "")
            if 'proficiency' in widgets:
                widgets['proficiency'].set(getattr(task, 'proficiency_level', "") or "")

        self.task_action_var.set(task.task_action or "")
        self.task_object_var.set(task.task_object or "")

        self.verification_text.delete('1.0', tk.END)
        if task.verification_method:
            self.verification_text.insert('1.0', task.verification_method)

    def populate_form_for_competency_edit(self, competency):
        """Populate the form for editing a core competency."""
        comp_type = competency.competency_type

        if comp_type in ["safety", "training", "communication", "leadership"]:
            self.competency_type_var.set(comp_type)
            self.on_competency_type_selected()

            # These are simpler competencies that don't have task implementations
            messagebox.showinfo("Competency Edit",
                                f"This is a {comp_type} competency. You can only delete it or modify it through the appropriate specialized forms.")
        else:
            messagebox.showinfo("Complex Competency",
                                "This appears to be a complex competency. Please use the specific task entries to edit individual components.")

    # Method to add to your main class
    def setup_context_menu(self):
        """Setup right-click context menu for the task details tree."""
        self.context_menu = tk.Menu(self.task_details_tree, tearoff=0)
        self.context_menu.add_command(label="Edit", command=self.edit_selected_assignment)
        self.context_menu.add_command(label="Delete", command=self.delete_selected_assignment)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Refresh", command=self.refresh_current_task_details)

        def show_context_menu(event):
            # Select the item under the cursor
            item = self.task_details_tree.identify_row(event.y)
            if item:
                self.task_details_tree.selection_set(item)
                self.context_menu.post(event.x_root, event.y_root)

        self.task_details_tree.bind("<Button-3>", show_context_menu)  # Right click

    def create_current_task_details_section(self, parent):
        """Create enhanced task details section with inline editing capabilities."""
        self.task_details_frame = ttk.LabelFrame(parent, text="Current Task Details", padding=10)
        self.task_details_frame.pack(fill='x', pady=(0, 10))

        # Create a frame for the treeview and buttons
        tree_container = ttk.Frame(self.task_details_frame)
        tree_container.pack(fill='both', expand=True)

        # Button frame at the top
        button_frame = ttk.Frame(tree_container)
        button_frame.pack(fill='x', pady=(0, 5))

        ttk.Button(button_frame, text="Delete Selected",
                   command=self.delete_selected_assignment).pack(side='left', padx=(0, 5))
        ttk.Button(button_frame, text="Refresh",
                   command=self.refresh_current_task_details).pack(side='left', padx=(0, 5))

        # Instructions label
        instructions = ttk.Label(button_frame,
                                 text="💡 Double-click cells to edit | Right-click for menu | Press Delete to remove entries",
                                 font=('TkDefaultFont', 8), foreground='blue')
        instructions.pack(side='left', padx=(20, 0))

        # Status label
        self.task_details_status = ttk.Label(button_frame, text="", foreground='green')
        self.task_details_status.pack(side='right')

        # Updated columns - removed "Details", added task-specific columns
        columns = ("Type", "Competency/Task Name", "Level", "Proficiency", "Task Action", "Task Object",
                   "Verification Method")
        self.task_details_tree = ttk.Treeview(tree_container, columns=columns, show="headings", height=8)

        # Configure columns with specific widths and editability
        column_config = {
            "Type": (80, False),  # Not editable
            "Competency/Task Name": (200, True),  # Editable
            "Level": (120, True),  # Editable
            "Proficiency": (80, True),  # Editable
            "Task Action": (120, True),  # Editable - NEW
            "Task Object": (150, True),  # Editable - NEW
            "Verification Method": (200, True)  # Editable - NEW
        }

        for col in columns:
            width, editable = column_config[col]
            self.task_details_tree.heading(col, text=col)
            self.task_details_tree.column(col, anchor='w', width=width)

            # Add visual indicator for editable columns
            if editable:
                self.task_details_tree.heading(col, text=f"{col} ✏️")

        # Create scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.task_details_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.task_details_tree.xview)
        self.task_details_tree.configure(yscroll=v_scrollbar.set, xscroll=h_scrollbar.set)

        # Pack treeview and scrollbars
        self.task_details_tree.pack(side='left', fill='both', expand=True)
        v_scrollbar.pack(side='right', fill='y')
        h_scrollbar.pack(side='bottom', fill='x')

        # Bind events for inline editing
        self.task_details_tree.bind('<Double-1>', self.on_cell_double_click)
        self.task_details_tree.bind('<Button-3>', self.show_context_menu)  # Right-click
        self.task_details_tree.bind('<Delete>', self.delete_selected_assignment)
        self.task_details_tree.bind('<<TreeviewSelect>>', self.on_task_details_row_selected)

        # Store the column editability config
        self.editable_columns = {col: editable for col, (width, editable) in column_config.items()}

        # Create context menu
        self.create_context_menu()

    def create_context_menu(self):
        """Create right-click context menu for the task details tree."""
        self.context_menu = tk.Menu(self.task_details_tree, tearoff=0)
        self.context_menu.add_command(label="✏️ Edit Cell", command=self.edit_selected_cell)
        self.context_menu.add_command(label="📝 Edit Full Record", command=self.edit_full_record)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Delete Record", command=self.delete_selected_assignment)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🔄 Refresh Table", command=self.refresh_current_task_details)

    def show_context_menu(self, event):
        """Show context menu on right-click."""
        # Select the item under the cursor
        item = self.task_details_tree.identify_row(event.y)
        if item:
            self.task_details_tree.selection_set(item)
            # Store the clicked column for context
            self.clicked_column = self.task_details_tree.identify_column(event.x)
            self.context_menu.post(event.x_root, event.y_root)

    def on_cell_double_click(self, event):
        """Handle double-click on a cell for inline editing."""
        item_id = self.task_details_tree.identify_row(event.y)
        column = self.task_details_tree.identify_column(event.x)

        if not item_id or column == '#0':
            return

        # Get column name
        column_index = int(column.replace('#', '')) - 1
        column_names = list(self.editable_columns.keys())

        if column_index >= len(column_names):
            return

        column_name = column_names[column_index]

        # Check if column is editable
        if not self.editable_columns[column_name]:
            messagebox.showinfo("Not Editable",
                                f"The '{column_name}' column cannot be edited directly.\n"
                                f"Use right-click → 'Edit Full Record' for comprehensive editing.")
            return

        self.start_cell_edit(item_id, column, column_name)

    def start_cell_edit(self, item_id, column, column_name):
        """Start editing a specific cell."""
        try:
            # Get current value
            current_values = self.task_details_tree.item(item_id, 'values')
            col_index = int(column.replace('#', '')) - 1
            current_value = current_values[col_index] if col_index < len(current_values) else ""

            # Get cell bounding box
            bbox = self.task_details_tree.bbox(item_id, column)
            if not bbox:
                return  # Cell not visible

            x, y, width, height = bbox

            # Create appropriate editor widget based on column type
            if column_name in ['Level', 'Proficiency']:
                self.create_dropdown_cell_editor(item_id, column, column_name, current_value, x, y, width, height)
            elif column_name == 'Verification Method':
                # Special handling for verification method - use popup editor
                if current_value == "N/A":
                    messagebox.showinfo("Not Applicable", f"This field is not applicable for this type of record.")
                    return
                self.create_verification_editor(item_id, column_name, current_value, x, y, width, height)
            else:
                # Regular text fields: Competency/Task Name, Task Action, Task Object
                self.create_text_cell_editor(item_id, column, column_name, current_value, x, y, width, height)

        except Exception as e:
            messagebox.showerror("Edit Error", f"Could not start editing: {e}")

    def create_dropdown_cell_editor(self, item_id, column, column_name, current_value, x, y, width, height):
        """Create a dropdown editor for level/proficiency fields."""
        # Define options based on column
        if column_name == 'Level':
            options = ["", "Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"]
        elif column_name == 'Proficiency':
            options = ["", "A", "B", "C"]
        else:
            options = [""]

        # Create combobox
        combo_var = tk.StringVar(value=current_value)
        combo = ttk.Combobox(self.task_details_tree, textvariable=combo_var,
                             values=options, state="normal", font=('TkDefaultFont', 9))
        combo.place(x=x, y=y, width=width, height=height)
        combo.set(current_value)
        combo.focus_set()

        def save_edit(event=None):
            new_value = combo_var.get().strip()
            combo.destroy()
            self.save_cell_edit(item_id, column, column_name, new_value, current_value)

        def cancel_edit(event=None):
            combo.destroy()

        # Bind events
        combo.bind('<Return>', save_edit)
        combo.bind('<Escape>', cancel_edit)
        combo.bind('<FocusOut>', save_edit)
        combo.bind('<<ComboboxSelected>>', save_edit)

    def save_cell_edit(self, item_id, column, column_name, new_value, old_value):
        """Save the edited cell value to the database."""
        if new_value == old_value:
            return

        try:
            # Update the tree display first
            current_values = list(self.task_details_tree.item(item_id, 'values'))

            # Update the appropriate column based on the new column structure
            column_map = {
                "Type": 0,
                "Competency/Task Name": 1,
                "Level": 2,
                "Proficiency": 3,
                "Task Action": 4,  # NEW
                "Task Object": 5,  # NEW
                "Verification Method": 6  # NEW
            }

            if column_name in column_map:
                current_values[column_map[column_name]] = new_value
                self.task_details_tree.item(item_id, values=current_values)

            # Determine record type and update database
            tags = self.task_details_tree.item(item_id, 'tags')

            if 'competency' in tags:
                # Editing a core competency
                comp_id = int(item_id.split('_')[1])
                competency = self.session.query(CoreCompetency).get(comp_id)

                if competency:
                    if column_name == 'Competency/Task Name':
                        competency.competency_name = new_value
                    elif column_name == 'Level':
                        competency.level = new_value if new_value else None
                    elif column_name == 'Proficiency':
                        competency.proficiency_level = new_value if new_value else None
                    # Note: Task Action, Task Object, and Verification Method don't apply to base competencies

            elif 'task' in tags:
                # Editing a specific task
                parts = item_id.split('_')
                task_type = parts[1]
                task_id = int(parts[2])

                # Get the appropriate task object
                task_obj = self.get_task_object(task_type, task_id)

                if task_obj:
                    if column_name == 'Competency/Task Name':
                        task_obj.competency_name = new_value
                    elif column_name == 'Level':
                        if hasattr(task_obj, 'level'):
                            task_obj.level = new_value if new_value else None
                    elif column_name == 'Proficiency':
                        if hasattr(task_obj, 'proficiency_level'):
                            task_obj.proficiency_level = new_value if new_value else None
                    elif column_name == 'Task Action':  # NEW
                        if hasattr(task_obj, 'task_action'):
                            task_obj.task_action = new_value if new_value else None
                    elif column_name == 'Task Object':  # NEW
                        if hasattr(task_obj, 'task_object'):
                            task_obj.task_object = new_value if new_value else None
                    elif column_name == 'Verification Method':  # NEW
                        if hasattr(task_obj, 'verification_method'):
                            task_obj.verification_method = new_value if new_value else None

            # Commit changes
            self.session.commit()

            # Show success feedback
            if hasattr(self, 'task_details_status'):
                self.task_details_status.config(text=f"✅ Updated {column_name}: '{new_value}'")
                self.after(3000, lambda: self.task_details_status.config(text=""))

            print(f"✅ Updated {column_name} for {item_id}: '{old_value}' → '{new_value}'")

        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Save Error", f"Failed to save changes: {e}")
            # Refresh table to restore original values
            self.refresh_current_task_details()

    def get_task_object(self, task_type, task_id):
        """Get the appropriate task object based on type and ID."""
        if task_type == "mechanical":
            return self.session.query(MechanicalTask).get(task_id)
        elif task_type == "electrical":
            return self.session.query(ElectricalTask).get(task_id)
        elif task_type == "tool":
            return self.session.query(ToolTask).get(task_id)
        elif task_type == "operational":
            return self.session.query(OperationalTask).get(task_id)
        return None

    def flash_row(self, item_id):
        """Flash a row to indicate it was changed."""
        # Change background color temporarily
        self.task_details_tree.set(item_id, '#0', '✓')  # Add checkmark
        self.after(1500, lambda: self.task_details_tree.set(item_id, '#0', ''))  # Remove checkmark

    def edit_selected_cell(self):
        """Edit the selected cell (from context menu)."""
        selected = self.task_details_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a cell to edit.")
            return

        item_id = selected[0]
        column = getattr(self, 'clicked_column', '#2')  # Default to name column

        # Get column name
        column_index = int(column.replace('#', '')) - 1
        column_names = list(self.editable_columns.keys())

        if column_index >= len(column_names):
            return

        column_name = column_names[column_index]

        if not self.editable_columns[column_name]:
            messagebox.showinfo("Not Editable", f"The '{column_name}' column is not editable.")
            return

        self.start_cell_edit(item_id, column, column_name)

    def edit_full_record(self):
        """Edit the full record using the comprehensive form."""
        selected = self.task_details_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a record to edit.")
            return

        # This would call your existing comprehensive edit functionality
        self.edit_selected_assignment()

    def on_task_details_row_selected(self, event):
        """Handle row selection in task details tree."""
        selected = self.task_details_tree.selection()
        if selected:
            item_id = selected[0]
            values = self.task_details_tree.item(item_id, 'values')

            if values:
                self.task_details_status.config(text=f"Selected: {values[0]} - {values[1]}")
        else:
            self.task_details_status.config(text="")

    def create_checklist_section(self, parent):
        # Checklist Task Selection
        checklist_frame = ttk.LabelFrame(self.scrollable_frame, text="1. Select or Create Checklist Task", padding=10)
        checklist_frame.pack(fill='x', pady=(0, 10))

        # Add description label
        desc_label = ttk.Label(checklist_frame, text="Choose to use an existing checklist task or create a new one.",
                               font=('TkDefaultFont', 9), foreground='gray')
        desc_label.grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 10))

        # Mode selection radio buttons
        self.task_mode_var = tk.StringVar(value="existing")

        mode_frame = ttk.Frame(checklist_frame)
        mode_frame.grid(row=1, column=0, columnspan=4, sticky='w', pady=(0, 15))

        ttk.Radiobutton(mode_frame, text="Use Existing Task",
                        variable=self.task_mode_var, value="existing",
                        command=self.on_task_mode_changed).pack(side='left', padx=(0, 20))

        ttk.Radiobutton(mode_frame, text="Create New Task",
                        variable=self.task_mode_var, value="create",
                        command=self.on_task_mode_changed).pack(side='left')

        # Dynamic content frame that changes based on mode
        self.task_selection_frame = ttk.Frame(checklist_frame)
        self.task_selection_frame.grid(row=2, column=0, columnspan=4, sticky='ew', pady=(0, 5))
        checklist_frame.grid_columnconfigure(0, weight=1)

        # Create the initial form (existing task mode)
        self.create_existing_task_widgets()

    def on_task_mode_changed(self):
        """Handle switching between existing task and create new task modes"""
        # Clear the current widgets
        for widget in self.task_selection_frame.winfo_children():
            widget.destroy()

        # Reset current task
        self.current_checklist_task = None

        if self.task_mode_var.get() == "existing":
            self.create_existing_task_widgets()
        else:
            self.create_new_task_widgets()

    def create_existing_task_widgets(self):
        """Create widgets for selecting existing tasks"""
        # Area dropdown
        ttk.Label(self.task_selection_frame, text="Area:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        self.area_var = tk.StringVar()
        self.area_combo = ttk.Combobox(self.task_selection_frame, textvariable=self.area_var,
                                       state="readonly", width=50)
        self.area_combo.grid(row=0, column=1, sticky='w', padx=(0, 10))
        self.area_combo.bind("<<ComboboxSelected>>", self.on_area_selected)
        # Help text for area
        area_help = ttk.Label(self.task_selection_frame,
                              text="The work area or location (e.g., 'Production Floor', 'Warehouse')",
                              font=('TkDefaultFont', 8), foreground='blue')
        area_help.grid(row=0, column=2, sticky='w', padx=(10, 0))

        # Section dropdown
        ttk.Label(self.task_selection_frame, text="Section:").grid(row=1, column=0, sticky='e', padx=(0, 5),
                                                                   pady=(5, 0))
        self.section_var = tk.StringVar()
        self.section_combo = ttk.Combobox(self.task_selection_frame, textvariable=self.section_var,
                                          state="readonly", width=50)
        self.section_combo.grid(row=1, column=1, sticky='w', padx=(0, 10), pady=(5, 0))
        self.section_combo.bind("<<ComboboxSelected>>", self.on_section_selected)
        # Help text for section
        section_help = ttk.Label(self.task_selection_frame,
                                 text="The section within the checklist (e.g., 'Daily Inspections', 'Monthly Maintenance')",
                                 font=('TkDefaultFont', 8), foreground='blue')
        section_help.grid(row=1, column=2, sticky='w', padx=(10, 0), pady=(5, 0))

        # Task dropdown
        ttk.Label(self.task_selection_frame, text="Task:").grid(row=2, column=0, sticky='e', padx=(0, 5), pady=(5, 0))
        self.task_var = tk.StringVar()
        self.task_combo = ttk.Combobox(self.task_selection_frame, textvariable=self.task_var,
                                       state="readonly", width=50)
        self.task_combo.grid(row=2, column=1, sticky='w', padx=(0, 10), pady=(5, 0))
        self.task_combo.bind("<<ComboboxSelected>>", self.on_task_selected)
        # Help text for task
        task_help = ttk.Label(self.task_selection_frame,
                              text="The specific task from the checklist (e.g., 'Rebuild Solution Pump')",
                              font=('TkDefaultFont', 8), foreground='blue')
        task_help.grid(row=2, column=2, sticky='w', padx=(10, 0), pady=(5, 0))

        # Populate dropdowns if they exist
        if hasattr(self, 'area_choices'):
            self.populate_existing_task_dropdowns()

    def create_new_task_widgets(self):
        """Create widgets for creating new tasks"""

        # Area section
        ttk.Label(self.task_selection_frame, text="Area:").grid(row=0, column=0, sticky='w', padx=(0, 5), pady=(0, 2))
        self.new_area_var = tk.StringVar()
        self.new_area_combo = ttk.Combobox(self.task_selection_frame, textvariable=self.new_area_var,
                                           state="readonly", width=50)
        self.new_area_combo.grid(row=1, column=0, sticky='w', padx=(0, 10), pady=(0, 5))
        self.new_area_combo.bind("<<ComboboxSelected>>", self.on_new_area_selected)

        # Help text for area
        new_area_help = ttk.Label(self.task_selection_frame, text="Select the work area for the new task",
                                  font=('TkDefaultFont', 8), foreground='blue')
        new_area_help.grid(row=2, column=0, sticky='w', padx=(0, 5), pady=(0, 10))

        # Section selection/creation
        section_frame = ttk.Frame(self.task_selection_frame)
        section_frame.grid(row=3, column=0, sticky='ew', pady=(0, 10))

        ttk.Label(section_frame, text="Section:").grid(row=0, column=0, sticky='w', padx=(0, 5), pady=(0, 2))

        # Section mode selection
        self.section_mode_var = tk.StringVar(value="existing")
        section_mode_frame = ttk.Frame(section_frame)
        section_mode_frame.grid(row=1, column=0, sticky='w', pady=(0, 5))

        ttk.Radiobutton(section_mode_frame, text="Use Existing",
                        variable=self.section_mode_var, value="existing",
                        command=self.on_section_mode_changed).pack(side='left', padx=(0, 10))

        ttk.Radiobutton(section_mode_frame, text="Create New",
                        variable=self.section_mode_var, value="create",
                        command=self.on_section_mode_changed).pack(side='left')

        # Dynamic section selection frame
        self.section_selection_frame = ttk.Frame(section_frame)
        self.section_selection_frame.grid(row=2, column=0, sticky='ew', pady=(5, 0))

        # Create initial section widgets (existing mode)
        self.create_section_selection_widgets()

        # New task description section
        ttk.Label(self.task_selection_frame, text="New Task Description:").grid(row=4, column=0, sticky='w',
                                                                                padx=(0, 5), pady=(10, 2))
        self.new_task_var = tk.StringVar()
        self.new_task_entry = ttk.Entry(self.task_selection_frame, textvariable=self.new_task_var, width=50)
        self.new_task_entry.grid(row=5, column=0, sticky='w', padx=(0, 10), pady=(0, 5))

        # Help text for new task
        new_task_help = ttk.Label(self.task_selection_frame,
                                  text="Enter the description for the new task (e.g., 'Rebuild Solution Pump')",
                                  font=('TkDefaultFont', 8), foreground='blue')
        new_task_help.grid(row=6, column=0, sticky='w', padx=(0, 5), pady=(0, 5))

        # Create Task button
        create_task_btn = ttk.Button(self.task_selection_frame, text="Create Task",
                                     command=self.create_new_checklist_task)
        create_task_btn.grid(row=7, column=0, sticky='w', padx=(0, 10), pady=(10, 0))

        # Populate area dropdown
        self.populate_new_task_dropdowns()

    def on_section_mode_changed(self):
        """Handle switching between existing section and create new section"""
        # Clear current section widgets
        for widget in self.section_selection_frame.winfo_children():
            widget.destroy()

        self.create_section_selection_widgets()

    def create_section_selection_widgets(self):
        """Create widgets for section selection based on mode"""
        if self.section_mode_var.get() == "existing":
            # Existing section dropdown
            self.new_section_var = tk.StringVar()
            self.new_section_combo = ttk.Combobox(self.section_selection_frame, textvariable=self.new_section_var,
                                                  state="readonly", width=50)
            self.new_section_combo.grid(row=0, column=0, sticky='w')

            section_help = ttk.Label(self.section_selection_frame,
                                     text="Select an existing section",
                                     font=('TkDefaultFont', 8), foreground='blue')
            section_help.grid(row=0, column=1, sticky='w', padx=(10, 0))
        else:
            # New section entry
            self.new_section_name_var = tk.StringVar()
            self.new_section_entry = ttk.Entry(self.section_selection_frame, textvariable=self.new_section_name_var,
                                               width=50)
            self.new_section_entry.grid(row=0, column=0, sticky='w')

            section_help = ttk.Label(self.section_selection_frame,
                                     text="Enter new section name (e.g., 'Weekly Maintenance')",
                                     font=('TkDefaultFont', 8), foreground='blue')
            section_help.grid(row=0, column=1, sticky='w', padx=(10, 0))

    def on_new_area_selected(self, event=None):
        """Handle area selection for new task creation"""
        if not hasattr(self, 'new_section_combo'):
            return

        area_index = self.new_area_combo.current()
        if area_index == -1:
            self.new_section_combo['values'] = []
            return

        try:
            area_id = self.area_choices[area_index][0]
            sections = self.session.query(ChecklistSection).filter_by(checklist_id=area_id).all()
            section_choices = [s.section_name for s in sections]
            self.new_section_combo['values'] = section_choices
            self.new_section_var.set('')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sections: {e}")

    def create_new_checklist_task(self):
        """Create a new checklist task and set it as current"""
        # Validate inputs
        area_index = self.new_area_combo.current()
        if area_index == -1:
            messagebox.showwarning("Missing Area", "Please select an area.")
            return

        task_description = self.new_task_var.get().strip()
        if not task_description:
            messagebox.showwarning("Missing Task Description", "Please enter a task description.")
            return

        try:
            area_id = self.area_choices[area_index][0]
            area = self.session.query(AreaChecklist).get(area_id)

            # Handle section creation/selection
            section = None
            if self.section_mode_var.get() == "existing":
                section_name = self.new_section_var.get().strip()
                if not section_name:
                    messagebox.showwarning("Missing Section", "Please select a section.")
                    return

                # Find existing section
                section = self.session.query(ChecklistSection).filter_by(
                    checklist_id=area_id,
                    section_name=section_name
                ).first()

                if not section:
                    messagebox.showerror("Section Not Found", f"Section '{section_name}' not found.")
                    return
            else:
                # Create new section
                section_name = self.new_section_name_var.get().strip()
                if not section_name:
                    messagebox.showwarning("Missing Section Name", "Please enter a section name.")
                    return

                # Check if section already exists
                existing_section = self.session.query(ChecklistSection).filter_by(
                    checklist_id=area_id,
                    section_name=section_name
                ).first()

                if existing_section:
                    messagebox.showwarning("Section Exists",
                                           f"Section '{section_name}' already exists. Please choose a different name.")
                    return

                # Create new section
                # Get next section order
                max_order = self.session.query(ChecklistSection.section_order).filter_by(
                    checklist_id=area_id
                ).order_by(ChecklistSection.section_order.desc()).first()
                next_order = (max_order[0] + 1) if max_order and max_order[0] else 1

                section = ChecklistSection(
                    checklist_id=area_id,
                    section_name=section_name,
                    section_order=next_order
                )
                self.session.add(section)
                self.session.flush()  # Get the ID

            # Create the new task
            # Get next task order
            max_task_order = self.session.query(ChecklistTask.task_order).filter_by(
                section_id=section.id
            ).order_by(ChecklistTask.task_order.desc()).first()
            next_task_order = (max_task_order[0] + 1) if max_task_order and max_task_order[0] else 1

            new_task = ChecklistTask(
                section_id=section.id,
                task_description=task_description,
                task_order=next_task_order
            )
            self.session.add(new_task)
            self.session.commit()

            # Set as current task
            self.current_checklist_task = new_task

            # Update UI to show success
            messagebox.showinfo("Success",
                                f"Created new task: '{task_description}' in section '{section.section_name}'")

            # Auto-populate task object from task description (same logic as existing)
            words = task_description.split()
            if len(words) >= 2:
                potential_object = " ".join(words[1:])  # Everything after first word
                self.task_object_var.set(potential_object)

        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to create new task: {e}")

    def create_competency_type_section(self, parent):
        # Competency Type Selection
        comp_type_frame = ttk.LabelFrame(parent, text="2. Select Competency Type", padding=10)
        comp_type_frame.pack(fill='x', pady=(0, 10))

        # Add description
        desc_label = ttk.Label(comp_type_frame,
                               text="Choose the type of competency needed for this task. This determines what skills and knowledge are required.",
                               font=('TkDefaultFont', 9), foreground='gray')
        desc_label.grid(row=0, column=0, columnspan=3, sticky='w', pady=(0, 10))

        self.competency_type_var = tk.StringVar()

        # Create radio buttons in a grid with descriptions
        types_with_desc = [
            ("Academic", "academic", "Math, reading, writing skills"),
            ("Safety", "safety", "OSHA, PPE, LOTO procedures"),
            ("Leadership", "leadership", "Team management, coaching"),
            ("Communication", "communication", "Written/verbal communication"),
            ("Training", "training", "Teaching and mentoring others"),
            ("Technical - Mechanical", "mechanical", "Pumps, motors, hydraulics"),
            ("Technical - Electrical", "electrical", "Wiring, controls, motors"),
            ("Technical - Tools", "tools", "Hand tools, power tools, test equipment"),
            ("Operational", "operational", "Machine operation procedures")
        ]

        for i, (display_name, value, description) in enumerate(types_with_desc):
            row = (i // 2) + 1  # Start from row 1 (after description)
            col = (i % 2) * 2  # Columns 0, 2, 4...

            # Radio button
            ttk.Radiobutton(comp_type_frame, text=display_name,
                            variable=self.competency_type_var, value=value,
                            command=self.on_competency_type_selected).grid(
                row=row, column=col, sticky='w', padx=(0, 10), pady=2)

            # Description
            desc = ttk.Label(comp_type_frame, text=f"({description})",
                             font=('TkDefaultFont', 8), foreground='blue')
            desc.grid(row=row, column=col + 1, sticky='w', pady=2)

    def create_dynamic_section(self, parent):
        # Dynamic section that changes based on competency type
        self.dynamic_frame = ttk.LabelFrame(parent, text="3. Competency Details", padding=10)
        self.dynamic_frame.pack(fill='x', pady=(0, 10))

        self.dynamic_widgets = {}

    def create_task_section(self, parent):
        # Task Definition Section
        task_frame = ttk.LabelFrame(parent, text="4. Task Definition", padding=10)
        task_frame.pack(fill='x', pady=(0, 10))

        # Add description
        desc_label = ttk.Label(task_frame,
                               text="Define the specific task that demonstrates competency. This creates a measurable skill that can be assessed.",
                               font=('TkDefaultFont', 9), foreground='gray')
        desc_label.grid(row=0, column=0, columnspan=4, sticky='w', pady=(0, 10))

        # Task Action - Updated to populate from database based on competency type
        ttk.Label(task_frame, text="Task Action:").grid(row=1, column=0, sticky='e', padx=(0, 5))
        self.task_action_var = tk.StringVar()
        self.task_action_combo = ttk.Combobox(task_frame, textvariable=self.task_action_var,
                                              values=[],  # Start empty - will be populated dynamically
                                              width=20, state="normal")  # Allow typing custom actions
        self.task_action_combo.grid(row=1, column=1, sticky='w', padx=(0, 20))

        # Help text for action
        action_help = ttk.Label(task_frame, text="What action is performed? (verb)",
                                font=('TkDefaultFont', 8), foreground='blue')
        action_help.grid(row=2, column=0, columnspan=2, sticky='w', pady=(0, 5))

        # Task Object
        ttk.Label(task_frame, text="Task Object:").grid(row=1, column=2, sticky='e', padx=(0, 5))
        self.task_object_var = tk.StringVar()
        self.task_object_entry = ttk.Entry(task_frame, textvariable=self.task_object_var, width=25)
        self.task_object_entry.grid(row=1, column=3, sticky='w')

        # Help text for object
        object_help = ttk.Label(task_frame, text="What is being acted upon? (noun)",
                                font=('TkDefaultFont', 8), foreground='blue')
        object_help.grid(row=2, column=2, columnspan=2, sticky='w', pady=(0, 5))

        # Verification Method
        ttk.Label(task_frame, text="Verification Method:").grid(row=3, column=0, sticky='ne', padx=(0, 5), pady=(5, 0))
        self.verification_var = tk.StringVar()
        self.verification_text = tk.Text(task_frame, height=3, width=60)
        self.verification_text.grid(row=3, column=1, columnspan=3, sticky='w', pady=(5, 0))

        # Help text for verification
        verification_help = ttk.Label(task_frame,
                                      text="How will competency be demonstrated and verified? Be specific about success criteria.",
                                      font=('TkDefaultFont', 8), foreground='blue')
        verification_help.grid(row=4, column=0, columnspan=4, sticky='w', pady=(5, 0))

        # Examples frame
        examples_frame = ttk.Frame(task_frame)
        examples_frame.grid(row=5, column=0, columnspan=4, sticky='w', pady=(10, 0))

        ttk.Label(examples_frame, text="Examples:", font=('TkDefaultFont', 9, 'bold')).pack(anchor='w')
        examples_text = tk.Text(examples_frame, height=4, width=80, font=('TkDefaultFont', 8))
        examples_text.pack(fill='x', pady=(2, 0))
        examples_text.insert('1.0',
                             "• Action='Rebuild', Object='Solution Pump', Verification='Complete disassembly, part inspection, reassembly with pressure test to 50 PSI'\n"
                             "• Action='Install', Object='Motor Starter', Verification='Proper wiring per schematic, successful motor start/stop operation'\n"
                             "• Action='Operate', Object='Conveyor System', Verification='Demonstrate startup, normal operation, and shutdown procedures safely'")
        examples_text.config(state='disabled')

    def populate_task_actions_from_db(self, comp_type):
        """Populate task action dropdown from database based on competency type."""
        try:
            actions = []

            if comp_type == 'mechanical':
                # Use MechanicalTask table, not MechanicalSkill
                db_actions = self.session.query(MechanicalTask.task_action).filter(
                    MechanicalTask.task_action.isnot(None),
                    MechanicalTask.task_action != '',
                    MechanicalTask.task_action != 'None'  # Filter out string 'None'
                ).distinct().all()
                actions = [action[0] for action in db_actions if action[0]]

            elif comp_type == 'electrical':
                # Get distinct task actions from ElectricalTask table
                db_actions = self.session.query(ElectricalTask.task_action).distinct().all()
                actions = [action[0] for action in db_actions if action[0]]

            elif comp_type == 'tools':
                # Get distinct task actions from ToolTask table
                db_actions = self.session.query(ToolTask.task_action).distinct().all()
                actions = [action[0] for action in db_actions if action[0]]

            elif comp_type == 'operational':
                # Get distinct task actions from OperationalTask table
                db_actions = self.session.query(OperationalTask.task_action).distinct().all()
                actions = [action[0] for action in db_actions if action[0]]

            else:
                # For safety, training, communication, leadership - use common actions
                actions = ["Implement", "Follow", "Demonstrate", "Document", "Train",
                           "Assess", "Present", "Communicate", "Lead", "Coordinate"]

            # Remove duplicates and sort
            actions = sorted(list(set(actions))) if actions else []

            # Add some common fallback actions if database is empty
            if not actions:
                fallback_actions = {
                    'mechanical': ["Rebuild", "Install", "Remove", "Repair", "Inspect", "Test", "Calibrate",
                                   "Maintain"],
                    'electrical': ["Install", "Wire", "Test", "Troubleshoot", "Replace", "Calibrate", "Program"],
                    'tools': ["Use", "Operate", "Calibrate", "Maintain", "Test", "Measure"],
                    'operational': ["Operate", "Start", "Stop", "Monitor", "Setup", "Clean"],
                    'safety': ["Implement", "Follow", "Demonstrate", "Document", "Train"],
                    'training': ["Teach", "Mentor", "Demonstrate", "Assess", "Present"],
                    'communication': ["Communicate", "Present", "Document", "Report", "Discuss"],
                    'leadership': ["Lead", "Direct", "Coordinate", "Manage", "Decide"]
                }
                actions = fallback_actions.get(comp_type, ["Perform", "Execute", "Complete"])

            # Update the combobox
            if hasattr(self, 'task_action_combo'):
                self.task_action_combo['values'] = actions
                # Clear current selection when changing competency type
                self.task_action_var.set('')

            print(
                f"✅ Loaded {len(actions)} task actions for {comp_type}: {actions[:5]}{'...' if len(actions) > 5 else ''}")
            return actions

        except Exception as e:
            print(f"❌ Error loading task actions from database: {e}")
            # Fallback to basic actions
            basic_actions = ["Perform", "Execute", "Complete", "Inspect", "Test", "Maintain"]
            if hasattr(self, 'task_action_combo'):
                self.task_action_combo['values'] = basic_actions
            return basic_actions

    # MODIFY your existing on_competency_type_selected method by adding this line at the end:
    def on_competency_type_selected(self):
        comp_type = self.competency_type_var.get()

        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()
        self.dynamic_widgets.clear()

        if comp_type == "mechanical":
            self.create_mechanical_section()
        elif comp_type == "electrical":
            self.create_electrical_section()
        elif comp_type == "tools":
            self.create_tools_section()
        elif comp_type == "operational":
            self.create_operational_section()
        elif comp_type == "safety":
            self.create_safety_section()
        elif comp_type == "training":
            self.create_training_section()
        elif comp_type == "communication":
            self.create_communication_section()
        elif comp_type == "leadership":
            self.create_leadership_section()

        # ADD THIS LINE - populate task actions from database
        if comp_type:
            self.populate_task_actions_from_db(comp_type)

    def create_action_buttons(self, parent):
        # Action Buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill='x', pady=(10, 0))

        ttk.Button(button_frame, text="Preview Assignment",
                   command=self.preview_assignment).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Save Assignment",
                   command=self.save_assignment).pack(side='left', padx=(0, 10))
        ttk.Button(button_frame, text="Reset Form",
                   command=self.reset_form).pack(side='left')

        # Preview area
        preview_frame = ttk.LabelFrame(parent, text="Assignment Preview", padding=10)
        preview_frame.pack(fill='both', expand=True, pady=(10, 0))

        self.preview_text = tk.Text(preview_frame, height=8, state='disabled')
        self.preview_text.pack(fill='both', expand=True)

    def populate_checklist_dropdowns(self):
        """Populate the area dropdown for both modes"""
        try:
            areas = self.session.query(AreaChecklist).all()
            self.area_choices = [(area.id, f"{area.area or ''} - {area.description or ''}") for area in areas]

            # Populate based on current mode
            if self.task_mode_var.get() == "existing":
                self.populate_existing_task_dropdowns()
            else:
                self.populate_new_task_dropdowns()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load areas: {e}")

    def populate_existing_task_dropdowns(self):
        """Populate dropdowns for existing task mode"""
        if hasattr(self, 'area_combo') and hasattr(self, 'area_choices'):
            self.area_combo['values'] = [desc for _id, desc in self.area_choices]

    def populate_new_task_dropdowns(self):
        """Populate dropdowns for new task mode"""
        if hasattr(self, 'new_area_combo') and hasattr(self, 'area_choices'):
            self.new_area_combo['values'] = [desc for _id, desc in self.area_choices]

    def on_area_selected(self, event=None):
        """Handle area selection for existing tasks"""
        area_index = self.area_combo.current()
        if area_index == -1:
            self.section_combo['values'] = []
            self.task_combo['values'] = []
            return

        try:
            area_id = self.area_choices[area_index][0]
            sections = self.session.query(ChecklistSection).filter_by(checklist_id=area_id).all()
            self.section_choices = [(s.id, s.section_name) for s in sections]
            self.section_combo['values'] = [desc for _id, desc in self.section_choices]
            self.section_var.set('')
            self.task_combo['values'] = []
            self.task_var.set('')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sections: {e}")

    def on_section_selected(self, event=None):
        """Handle section selection for existing tasks"""
        section_index = self.section_combo.current()
        if section_index == -1:
            self.task_combo['values'] = []
            return

        try:
            section_id = self.section_choices[section_index][0]
            tasks = self.session.query(ChecklistTask).filter_by(section_id=section_id).all()
            self.task_choices = [(t.id, t.task_description) for t in tasks]
            self.task_combo['values'] = [desc for _id, desc in self.task_choices]
            self.task_var.set('')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load tasks: {e}")

    def on_task_selected(self, event=None):
        """Handle task selection and auto-fill task object, then update the current task details section."""
        task_index = self.task_combo.current()
        if task_index == -1:
            self.current_checklist_task = None
            self.refresh_current_task_details()  # Also clear the details section if nothing is selected
            return

        try:
            task_id = self.task_choices[task_index][0]
            self.current_checklist_task = self.session.query(ChecklistTask).get(task_id)

            # Auto-populate task object from checklist task description
            task_desc = self.current_checklist_task.task_description
            words = task_desc.split()
            if len(words) >= 2:
                potential_object = " ".join(words[1:])  # Everything after first word
                self.task_object_var.set(potential_object)

            # --- NEW: Refresh the current task details section ---
            self.refresh_current_task_details()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load task details: {e}")

    def refresh_dropdowns(self):
        """Refresh dropdown options from database - call this when tab becomes active"""
        comp_type = self.competency_type_var.get()

        print(f"Refreshing dropdowns for competency type: {comp_type}")

        if comp_type == "mechanical" and hasattr(self, 'mech_subcategory_combo'):
            # Refresh mechanical subcategories
            subcats = self.get_mechanical_subcategories()
            current_value = self.mech_subcategory_var.get()
            self.mech_subcategory_combo['values'] = subcats

            # Restore selection if it still exists
            if current_value in subcats:
                self.mech_subcategory_var.set(current_value)
                # Also refresh equipment categories
                self.on_mech_subcategory_selected()

        elif comp_type == "electrical" and hasattr(self, 'elec_subcategory_combo'):
            # Refresh electrical subcategories
            subcats = self.get_electrical_subcategories()
            current_value = self.elec_subcategory_var.get()
            self.elec_subcategory_combo['values'] = subcats

            # Refresh voltage levels
            voltage_levels = self.get_electrical_voltage_levels()
            current_voltage = self.elec_voltage_var.get()
            self.elec_voltage_combo['values'] = voltage_levels

            # Restore selections if they still exist
            if current_value in subcats:
                self.elec_subcategory_var.set(current_value)
            if current_voltage in voltage_levels:
                self.elec_voltage_var.set(current_voltage)

        elif comp_type == "tools" and hasattr(self, 'tool_type_combo'):
            # Refresh tool types and applications
            tool_types = self.get_tool_types()
            current_type = self.tool_type_var.get()
            self.tool_type_combo['values'] = tool_types

            applications = self.get_tool_applications()
            current_app = self.tool_application_var.get()
            self.tool_application_combo['values'] = applications

            # Restore selections if they still exist
            if current_type in tool_types:
                self.tool_type_var.set(current_type)
            if current_app in applications:
                self.tool_application_var.set(current_app)

        elif comp_type == "operational" and hasattr(self, 'oper_type_combo'):
            # Refresh operational types and machine types
            oper_types = self.get_operational_types()
            current_type = self.oper_type_var.get()
            self.oper_type_combo['values'] = oper_types

            machine_types = self.get_operational_machine_types()
            current_machine = self.oper_machine_var.get()
            self.oper_machine_combo['values'] = machine_types

            # Restore selections if they still exist
            if current_type in oper_types:
                self.oper_type_var.set(current_type)
            if current_machine in machine_types:
                self.oper_machine_var.set(current_machine)

        print("Dropdown refresh completed")

    def create_mechanical_section(self):
        """Create mechanical-specific form fields"""

        # --- Competency Name field ---
        self.competency_name_var = tk.StringVar()
        ttk.Label(self.dynamic_frame, text="Competency Name:").grid(row=0, column=0, sticky='e', pady=(0, 2))
        ttk.Entry(self.dynamic_frame, textvariable=self.competency_name_var, width=40).grid(
            row=0, column=1, columnspan=3, sticky='w', padx=(0, 10), pady=(0, 2)
        )

        # --- Level and Proficiency fields side by side ---
        level_prof_frame = ttk.Frame(self.dynamic_frame)
        level_prof_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 8))

        # Level field
        ttk.Label(level_prof_frame, text="Level:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        self.level_var = tk.StringVar()
        self.level_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.level_var,
            values=["Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"], width=15
        )
        self.level_combo.grid(row=0, column=1, sticky='w', padx=(0, 20))
        self.level_combo.set("Level 1")

        # Proficiency field
        ttk.Label(level_prof_frame, text="Proficiency:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        self.proficiency_var = tk.StringVar()
        self.proficiency_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.proficiency_var,
            values=["A", "B", "C"], width=15
        )
        self.proficiency_combo.grid(row=0, column=3, sticky='w')
        self.proficiency_combo.set("A")

        # --- Add description ---
        desc_label = ttk.Label(self.dynamic_frame,
                               text="Specify the mechanical system and equipment type for this competency.",
                               font=('TkDefaultFont', 9), foreground='gray')
        desc_label.grid(row=2, column=0, columnspan=4, sticky='w', pady=(0, 10))

        # --- Sub-category dropdown - populated from database ---
        ttk.Label(self.dynamic_frame, text="Mechanical System:").grid(row=3, column=0, sticky='e', padx=(0, 5))
        self.mech_subcategory_var = tk.StringVar()
        subcats = self.get_mechanical_subcategories()
        self.mech_subcategory_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.mech_subcategory_var,
            values=subcats, width=25
        )
        self.mech_subcategory_combo.grid(row=3, column=1, sticky='w', padx=(0, 20))
        self.mech_subcategory_combo.bind("<<ComboboxSelected>>", self.on_mech_subcategory_selected)

        # --- Help text for system ---
        system_help = ttk.Label(self.dynamic_frame, text="The type of mechanical system",
                                font=('TkDefaultFont', 8), foreground='blue')
        system_help.grid(row=4, column=0, columnspan=2, sticky='w', pady=(0, 5))

        # --- Equipment category (populated based on subcategory) ---
        ttk.Label(self.dynamic_frame, text="Equipment Category:").grid(row=3, column=2, sticky='e', padx=(0, 5))
        self.mech_equipment_var = tk.StringVar()
        self.mech_equipment_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.mech_equipment_var,
            width=25
        )
        self.mech_equipment_combo.grid(row=3, column=3, sticky='w')

        # --- Help text for equipment ---
        equipment_help = ttk.Label(self.dynamic_frame, text="Specific equipment type (updates based on system)",
                                   font=('TkDefaultFont', 8), foreground='blue')
        equipment_help.grid(row=4, column=2, columnspan=2, sticky='w', pady=(0, 5))

        # --- Examples ---
        examples_label = ttk.Label(self.dynamic_frame, text="Examples:", font=('TkDefaultFont', 9, 'bold'))
        examples_label.grid(row=5, column=0, sticky='w', pady=(10, 5))

        examples_text = tk.Text(self.dynamic_frame, height=3, width=80, font=('TkDefaultFont', 8))
        examples_text.grid(row=6, column=0, columnspan=4, sticky='w')
        examples_text.insert('1.0',
                             "• Hydraulic Systems → Pumps (for hydraulic pump maintenance)\n"
                             "• Pump Systems → Solution Pumps (for chemical processing pumps)\n"
                             "• Motor Systems → AC Motors (for standard motor maintenance)")
        examples_text.config(state='disabled')

        # --- Save all widget vars for saving later ---
        self.dynamic_widgets['mechanical'] = {
            'competency_name': self.competency_name_var,
            'subcategory': self.mech_subcategory_var,
            'equipment': self.mech_equipment_var,
            'level': self.level_var,
            'proficiency': self.proficiency_var
        }

    def get_mechanical_subcategories(self):
        """Get mechanical subcategories from database with fallback"""
        subcats = []
        try:
            print("=== DEBUG: Querying MechanicalSkill with polymorphic identity ===")

            # Query MechanicalSkill objects - polymorphic inheritance should work now
            mech_skills = self.session.query(MechanicalSkill).filter(
                MechanicalSkill.competency_type == 'mechanical'
            ).all()

            print(f"Query returned {len(mech_skills)} MechanicalSkill records")

            for i, skill in enumerate(mech_skills):
                print(f"Record {i + 1}:")
                print(f"  - ID: {skill.id}")
                print(f"  - competency_name: '{skill.competency_name}'")
                print(f"  - competency_type: '{skill.competency_type}'")
                print(f"  - sub_category: '{skill.sub_category}'")
                print(f"  - equipment_category: '{skill.equipment_category}'")

            # Extract subcategories
            subcats = [skill.sub_category for skill in mech_skills if skill.sub_category]
            print(f"Non-null subcategories: {subcats}")

            # Remove duplicates and sort
            subcats = sorted(list(set(subcats)))
            print(f"Unique sorted subcategories: {subcats}")

            if subcats:
                print(f"Using database subcategories: {subcats}")
                return subcats

        except Exception as e:
            print(f"Error querying MechanicalSkill: {e}")
            import traceback
            traceback.print_exc()

        # Fallback to hardcoded list
        print("Using fallback subcategories")
        return ["Hydraulic Systems", "Pneumatic Systems", "Belt/Chain Drive", "Bearing Systems",
                "Pump Systems", "Motor Systems", "Conveyor Systems"]

    def get_equipment_categories_for_subcategory(self, subcategory):
        """Get equipment categories for a specific mechanical subcategory"""
        equipment_options = []
        try:
            print(f"=== DEBUG: Querying equipment categories for: {subcategory} ===")

            # Query MechanicalSkill objects with polymorphic filtering
            matching_skills = self.session.query(MechanicalSkill).filter(
                MechanicalSkill.competency_type == 'mechanical',
                MechanicalSkill.sub_category == subcategory
            ).all()

            equipment_options = [skill.equipment_category for skill in matching_skills
                                 if skill.equipment_category]

            print(f"Found {len(matching_skills)} matching skills for subcategory: {subcategory}")
            print(f"Equipment options found: {equipment_options}")

            # Remove duplicates and sort
            equipment_options = sorted(list(set(equipment_options)))

            if equipment_options:
                print(f"Using database equipment categories: {equipment_options}")
                return equipment_options

        except Exception as e:
            print(f"Error querying equipment categories: {e}")

        # Fallback to hardcoded mapping if no database entries
        print(f"Using fallback equipment mapping for: {subcategory}")
        equipment_map = {
            "Hydraulic Systems": ["Pumps", "Actuators", "Valves", "Cylinders"],
            "Pneumatic Systems": ["Compressors", "Actuators", "Valves", "Cylinders"],
            "Belt/Chain Drive": ["Conveyors", "Motors", "Drives"],
            "Bearing Systems": ["Motors", "Pumps", "Conveyors"],
            "Pump Systems": ["Centrifugal Pumps", "Positive Displacement", "Solution Pumps"],
            "Motor Systems": ["AC Motors", "DC Motors", "Servo Motors"],
            "Conveyor Systems": ["Belt Conveyors", "Chain Conveyors", "Roller Conveyors"]
        }
        return equipment_map.get(subcategory, [])

    def create_electrical_section(self):
        """Create electrical-specific form fields"""

        # --- Competency Name field (per-section) ---
        elec_comp_name_var = tk.StringVar()
        ttk.Label(self.dynamic_frame, text="Competency Name:").grid(row=0, column=0, sticky='e', pady=(0, 2))
        ttk.Entry(self.dynamic_frame, textvariable=elec_comp_name_var, width=40).grid(
            row=0, column=1, columnspan=3, sticky='w', padx=(0, 10), pady=(0, 2)
        )

        # --- Level and Proficiency fields side by side ---
        level_prof_frame = ttk.Frame(self.dynamic_frame)
        level_prof_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 8))

        # Level field
        ttk.Label(level_prof_frame, text="Level:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        self.elec_level_var = tk.StringVar()
        self.elec_level_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.elec_level_var,
            values=["Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"], width=15
        )
        self.elec_level_combo.grid(row=0, column=1, sticky='w', padx=(0, 20))
        self.elec_level_combo.set("Level 1")

        # Proficiency field
        ttk.Label(level_prof_frame, text="Proficiency:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        self.elec_proficiency_var = tk.StringVar()
        self.elec_proficiency_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.elec_proficiency_var,
            values=["A", "B", "C"], width=15
        )
        self.elec_proficiency_combo.grid(row=0, column=3, sticky='w')
        self.elec_proficiency_combo.set("A")

        # --- Add description ---
        desc_label = ttk.Label(self.dynamic_frame,
                               text="Specify the electrical system type and voltage requirements for this competency.",
                               font=('TkDefaultFont', 9), foreground='gray')
        desc_label.grid(row=2, column=0, columnspan=4, sticky='w', pady=(0, 10))

        # --- Sub-category (from database) ---
        ttk.Label(self.dynamic_frame, text="Electrical System:").grid(row=3, column=0, sticky='e', padx=(0, 5))
        self.elec_subcategory_var = tk.StringVar()
        subcats = self.get_electrical_subcategories()
        self.elec_subcategory_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.elec_subcategory_var,
            values=subcats, width=25
        )
        self.elec_subcategory_combo.grid(row=3, column=1, sticky='w', padx=(0, 20))
        self.elec_subcategory_combo.bind("<<ComboboxSelected>>", self.on_elec_subcategory_selected)

        # --- Help text for electrical system ---
        system_help = ttk.Label(self.dynamic_frame, text="Type of electrical work",
                                font=('TkDefaultFont', 8), foreground='blue')
        system_help.grid(row=4, column=0, columnspan=2, sticky='w', pady=(0, 5))

        # --- Voltage level ---
        ttk.Label(self.dynamic_frame, text="Voltage Level:").grid(row=3, column=2, sticky='e', padx=(0, 5))
        self.elec_voltage_var = tk.StringVar()
        voltage_levels = self.get_electrical_voltage_levels()
        self.elec_voltage_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.elec_voltage_var,
            values=voltage_levels, width=15
        )
        self.elec_voltage_combo.grid(row=3, column=3, sticky='w')

        # --- Help text for voltage ---
        voltage_help = ttk.Label(self.dynamic_frame, text="Low=<600V, High=>600V",
                                 font=('TkDefaultFont', 8), foreground='blue')
        voltage_help.grid(row=4, column=2, columnspan=2, sticky='w', pady=(0, 5))

        # --- Examples ---
        examples_label = ttk.Label(self.dynamic_frame, text="Examples:", font=('TkDefaultFont', 9, 'bold'))
        examples_label.grid(row=5, column=0, sticky='w', pady=(10, 5))

        examples_text = tk.Text(self.dynamic_frame, height=3, width=80, font=('TkDefaultFont', 8))
        examples_text.grid(row=6, column=0, columnspan=4, sticky='w')
        examples_text.insert('1.0',
                             "• Control Circuits & Sensors + Low (for 24V control circuit work)\n"
                             "• Motor Controls + High (for 480V motor starter installation)\n"
                             "• VFDs + Low/High (for variable frequency drive work at any voltage)")
        examples_text.config(state='disabled')

        # --- Register all section-specific variables for later retrieval ---
        self.dynamic_widgets['electrical'] = {
            'competency_name': elec_comp_name_var,
            'subcategory': self.elec_subcategory_var,
            'voltage': self.elec_voltage_var,
            'level': self.elec_level_var,
            'proficiency': self.elec_proficiency_var
        }

    def get_electrical_subcategories(self):
        """Get electrical subcategories from database with fallback"""
        subcats = []
        try:
            print("=== DEBUG: Querying ElectricalSkill with polymorphic identity ===")

            # Query ElectricalSkill objects - polymorphic inheritance should work now
            elec_skills = self.session.query(ElectricalSkill).filter(
                ElectricalSkill.competency_type == 'electrical'
            ).all()

            subcats = [skill.sub_category for skill in elec_skills if skill.sub_category]

            print(f"Found {len(elec_skills)} ElectricalSkill records")
            print(f"Electrical subcategories found: {subcats}")

            # Remove duplicates and sort
            subcats = sorted(list(set(subcats)))

            if subcats:
                return subcats

        except Exception as e:
            print(f"Error querying ElectricalSkill: {e}")

        # Fallback to hardcoded list
        return ["Low Voltage Wiring", "High Voltage Wiring", "Control Circuits & Sensors",
                "VFDs", "MCC", "Motor Controls"]

    def get_electrical_voltage_levels(self):
        """Get electrical voltage levels from database with fallback"""
        voltage_levels = []
        try:
            # Try to get from ElectricalSkill table
            elec_skills = self.session.query(ElectricalSkill).filter(
                ElectricalSkill.competency_type == 'electrical'
            ).all()
            voltage_levels = [skill.voltage_level for skill in elec_skills if skill.voltage_level]

            # Remove duplicates and sort
            voltage_levels = sorted(list(set(voltage_levels)))

            if voltage_levels:
                return voltage_levels

        except Exception as e:
            print(f"Error querying ElectricalSkill voltage levels: {e}")

        # Fallback to hardcoded list
        return ["Low", "High", "Low/High"]

    def on_elec_subcategory_selected(self, event=None):
        """Update voltage levels based on electrical subcategory if needed"""
        # For now, voltage levels are independent, but this could be used
        # to filter voltage levels based on subcategory in the future
        pass

    def create_tools_section(self):
        """Create tools-specific form fields"""

        # --- Competency Name field (section-specific variable) ---
        tool_comp_name_var = tk.StringVar()
        ttk.Label(self.dynamic_frame, text="Competency Name:").grid(row=0, column=0, sticky='e', pady=(0, 2))
        ttk.Entry(self.dynamic_frame, textvariable=tool_comp_name_var, width=40).grid(
            row=0, column=1, columnspan=3, sticky='w', padx=(0, 10), pady=(0, 2)
        )

        # --- Level and Proficiency fields side by side ---
        level_prof_frame = ttk.Frame(self.dynamic_frame)
        level_prof_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 8))

        # Level field
        ttk.Label(level_prof_frame, text="Level:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        self.tool_level_var = tk.StringVar()
        self.tool_level_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.tool_level_var,
            values=["Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"], width=15
        )
        self.tool_level_combo.grid(row=0, column=1, sticky='w', padx=(0, 20))
        self.tool_level_combo.set("Level 1")

        # Proficiency field
        ttk.Label(level_prof_frame, text="Proficiency:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        self.tool_proficiency_var = tk.StringVar()
        self.tool_proficiency_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.tool_proficiency_var,
            values=["A", "B", "C"], width=15
        )
        self.tool_proficiency_combo.grid(row=0, column=3, sticky='w')
        self.tool_proficiency_combo.set("A")

        # --- Add description ---
        desc_label = ttk.Label(self.dynamic_frame,
                               text="Specify the tool category and its primary application area.",
                               font=('TkDefaultFont', 9), foreground='gray')
        desc_label.grid(row=2, column=0, columnspan=4, sticky='w', pady=(0, 10))

        # --- Tool type - populated from database ---
        ttk.Label(self.dynamic_frame, text="Tool Type:").grid(row=3, column=0, sticky='e', padx=(0, 5))
        self.tool_type_var = tk.StringVar()
        tool_types = self.get_tool_types()
        self.tool_type_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.tool_type_var,
            values=tool_types, width=20
        )
        self.tool_type_combo.grid(row=3, column=1, sticky='w', padx=(0, 20))

        # --- Help text for tool type ---
        type_help = ttk.Label(self.dynamic_frame, text="Category of tool",
                              font=('TkDefaultFont', 8), foreground='blue')
        type_help.grid(row=4, column=0, columnspan=2, sticky='w', pady=(0, 5))

        # --- Primary application - populated from database ---
        ttk.Label(self.dynamic_frame, text="Primary Application:").grid(row=3, column=2, sticky='e', padx=(0, 5))
        self.tool_application_var = tk.StringVar()
        applications = self.get_tool_applications()
        self.tool_application_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.tool_application_var,
            values=applications, width=15
        )
        self.tool_application_combo.grid(row=3, column=3, sticky='w')

        # --- Help text for application ---
        app_help = ttk.Label(self.dynamic_frame, text="Main field where tool is used",
                             font=('TkDefaultFont', 8), foreground='blue')
        app_help.grid(row=4, column=2, columnspan=2, sticky='w', pady=(0, 5))

        # --- Examples ---
        examples_label = ttk.Label(self.dynamic_frame, text="Examples:", font=('TkDefaultFont', 9, 'bold'))
        examples_label.grid(row=5, column=0, sticky='w', pady=(10, 5))

        examples_text = tk.Text(self.dynamic_frame, height=3, width=80, font=('TkDefaultFont', 8))
        examples_text.grid(row=6, column=0, columnspan=4, sticky='w')
        examples_text.insert('1.0',
                             "• Measuring Tools + Mechanical (calipers, micrometers for shaft measurements)\n"
                             "• Test Equipment + Electrical (multimeters, oscilloscopes for circuit testing)\n"
                             "• Power Tools + Universal (drills, grinders used in both electrical and mechanical work)")
        examples_text.config(state='disabled')

        # --- Register section-specific variables (now includes proficiency) ---
        self.dynamic_widgets['tools'] = {
            'competency_name': tool_comp_name_var,
            'tool_type': self.tool_type_var,
            'application': self.tool_application_var,
            'level': self.tool_level_var,
            'proficiency': self.tool_proficiency_var
        }

    def get_tool_types(self):
        """Get tool types from database with fallback"""
        tool_types = []
        try:
            print("=== DEBUG: Querying ToolSkill with polymorphic identity ===")

            # Query ToolSkill objects - polymorphic inheritance should work now
            tool_skills = self.session.query(ToolSkill).filter(
                ToolSkill.competency_type == 'tools'
            ).all()

            tool_types = [skill.tool_type for skill in tool_skills if skill.tool_type]

            print(f"Found {len(tool_skills)} ToolSkill records")
            print(f"Tool types found: {tool_types}")

            # Remove duplicates and sort
            tool_types = sorted(list(set(tool_types)))

            if tool_types:
                return tool_types

        except Exception as e:
            print(f"Error querying ToolSkill: {e}")

        # Fallback to hardcoded list
        return ["Hand Tools", "Power Tools", "Measuring Tools", "Test Equipment"]

    def get_tool_applications(self):
        """Get tool applications from database with fallback"""
        applications = []
        try:
            # Query ToolSkill objects - polymorphic inheritance should work now
            tool_skills = self.session.query(ToolSkill).filter(
                ToolSkill.competency_type == 'tools'
            ).all()

            applications = [skill.primary_application for skill in tool_skills if skill.primary_application]

            # Remove duplicates and sort
            applications = sorted(list(set(applications)))

            if applications:
                return applications

        except Exception as e:
            print(f"Error querying ToolSkill for applications: {e}")

        # Fallback to hardcoded list
        return ["Electrical", "Mechanical", "Universal"]

    def create_operational_section(self):
        """Create operational-specific form fields"""

        # --- Competency Name field (per-section) ---
        oper_comp_name_var = tk.StringVar()
        ttk.Label(self.dynamic_frame, text="Competency Name:").grid(row=0, column=0, sticky='e', pady=(0, 2))
        ttk.Entry(self.dynamic_frame, textvariable=oper_comp_name_var, width=40).grid(
            row=0, column=1, columnspan=3, sticky='w', padx=(0, 10), pady=(0, 2)
        )

        # --- Level and Proficiency fields side by side ---
        level_prof_frame = ttk.Frame(self.dynamic_frame)
        level_prof_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 8))

        # Level field
        ttk.Label(level_prof_frame, text="Level:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        self.oper_level_var = tk.StringVar()
        self.oper_level_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.oper_level_var,
            values=["Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"], width=15
        )
        self.oper_level_combo.grid(row=0, column=1, sticky='w', padx=(0, 20))
        self.oper_level_combo.set("Level 1")

        # Proficiency field
        ttk.Label(level_prof_frame, text="Proficiency:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        self.oper_proficiency_var = tk.StringVar()
        self.oper_proficiency_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.oper_proficiency_var,
            values=["A", "B", "C"], width=15
        )
        self.oper_proficiency_combo.grid(row=0, column=3, sticky='w')
        self.oper_proficiency_combo.set("A")

        # --- Add description ---
        desc_label = ttk.Label(self.dynamic_frame,
                               text="Specify the type of operation and the specific machine or equipment being operated.",
                               font=('TkDefaultFont', 9), foreground='gray')
        desc_label.grid(row=2, column=0, columnspan=4, sticky='w', pady=(0, 10))

        # --- Operation type - populated from database ---
        ttk.Label(self.dynamic_frame, text="Operation Type:").grid(row=3, column=0, sticky='e', padx=(0, 5))
        self.oper_type_var = tk.StringVar()
        oper_types = self.get_operational_types()
        self.oper_type_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.oper_type_var,
            values=oper_types, width=20
        )
        self.oper_type_combo.grid(row=3, column=1, sticky='w', padx=(0, 20))

        # --- Help text for operation type ---
        type_help = ttk.Label(self.dynamic_frame, text="Mode or type of operation",
                              font=('TkDefaultFont', 8), foreground='blue')
        type_help.grid(row=4, column=0, columnspan=2, sticky='w', pady=(0, 5))

        # --- Machine type - populated from database ---
        ttk.Label(self.dynamic_frame, text="Machine Type:").grid(row=3, column=2, sticky='e', padx=(0, 5))
        self.oper_machine_var = tk.StringVar()
        machine_types = self.get_operational_machine_types()
        self.oper_machine_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.oper_machine_var,
            values=machine_types, width=20
        )
        self.oper_machine_combo.grid(row=3, column=3, sticky='w')

        # --- Help text for machine ---
        machine_help = ttk.Label(self.dynamic_frame, text="Specific machine or equipment name",
                                 font=('TkDefaultFont', 8), foreground='blue')
        machine_help.grid(row=4, column=2, columnspan=2, sticky='w', pady=(0, 5))

        # --- Examples ---
        examples_label = ttk.Label(self.dynamic_frame, text="Examples:", font=('TkDefaultFont', 9, 'bold'))
        examples_label.grid(row=5, column=0, sticky='w', pady=(10, 5))

        examples_text = tk.Text(self.dynamic_frame, height=3, width=80, font=('TkDefaultFont', 8))
        examples_text.grid(row=6, column=0, columnspan=4, sticky='w')
        examples_text.insert('1.0',
                             "• Manual Mode + Bag Sealer (operating bag sealer in manual mode)\n"
                             "• Changeover + Filling Line (changing product on filling line)\n"
                             "• Cleaning + Conveyor Belt (proper cleaning procedures for conveyor)")
        examples_text.config(state='disabled')

        # --- Register section-specific variables (now includes proficiency) ---
        self.dynamic_widgets['operational'] = {
            'competency_name': oper_comp_name_var,
            'operation_type': self.oper_type_var,
            'machine_type': self.oper_machine_var,
            'level': self.oper_level_var,
            'proficiency': self.oper_proficiency_var
        }

    def get_operational_types(self):
        """Get operational types from database with fallback"""
        oper_types = []
        try:
            print("=== DEBUG: Querying OperationalSkill with polymorphic identity ===")

            # Query OperationalSkill objects - polymorphic inheritance should work now
            oper_skills = self.session.query(OperationalSkill).filter(
                OperationalSkill.competency_type == 'operational'
            ).all()

            oper_types = [skill.operation_type for skill in oper_skills if skill.operation_type]

            print(f"Found {len(oper_skills)} OperationalSkill records")
            print(f"Operation types found: {oper_types}")

            # Remove duplicates and sort
            oper_types = sorted(list(set(oper_types)))

            if oper_types:
                return oper_types

        except Exception as e:
            print(f"Error querying OperationalSkill: {e}")

        # Fallback to hardcoded list
        return ["Manual Mode", "Auto Mode", "Cleaning", "Lubrication", "Setup", "Changeover"]

    def get_operational_machine_types(self):
        """Get operational machine types from database with fallback"""
        machine_types = []
        try:
            # Try to get from OperationalSkill table
            oper_skills = self.session.query(OperationalSkill).filter(
                OperationalSkill.competency_type == 'operational'
            ).all()
            machine_types = [skill.machine_type for skill in oper_skills if skill.machine_type]

            print(f"Machine types found: {machine_types}")

            # Remove duplicates and sort
            machine_types = sorted(list(set(machine_types)))

            if machine_types:
                return machine_types

        except Exception as e:
            print(f"Error querying OperationalSkill machine types: {e}")

        # Return some common examples as fallback
        return ["Bag Sealer", "Filling Line", "Conveyor Belt", "Packaging Machine", "Palletizer", "Shrink Wrapper"]

    def on_mech_subcategory_selected(self, event=None):
        """Update equipment category based on mechanical subcategory - use database data"""
        subcategory = self.mech_subcategory_var.get()
        equipment_options = self.get_equipment_categories_for_subcategory(subcategory)
        self.mech_equipment_combo['values'] = equipment_options
        self.mech_equipment_var.set('')

    def preview_assignment(self):
        """Preview the assignment that will be created"""
        if not self.current_checklist_task:
            if self.task_mode_var.get() == "existing":
                messagebox.showwarning("No Task", "Please select a checklist task first.")
            else:
                messagebox.showwarning("No Task", "Please create a checklist task first.")
            return

        preview_text = f"Checklist Task: {self.current_checklist_task.task_description}\n"
        preview_text += f"Task Mode: {'Existing' if self.task_mode_var.get() == 'existing' else 'Newly Created'}\n"
        preview_text += f"Competency Type: {self.competency_type_var.get()}\n"

        comp_type = self.competency_type_var.get()
        if comp_type in self.dynamic_widgets:
            for key, var in self.dynamic_widgets[comp_type].items():
                preview_text += f"{key.title()}: {var.get()}\n"

        preview_text += f"Task Action: {self.task_action_var.get()}\n"
        preview_text += f"Task Object: {self.task_object_var.get()}\n"
        preview_text += f"Verification Method: {self.verification_text.get('1.0', tk.END).strip()}\n"

        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.insert('1.0', preview_text)
        self.preview_text.config(state='disabled')

    def save_assignment(self):
        """Save or update the competency assignment (edit or add)."""
        if not self.current_checklist_task:
            if self.task_mode_var.get() == "existing":
                messagebox.showwarning("No Task", "Please select a checklist task first.")
            else:
                messagebox.showwarning("No Task", "Please create a checklist task first.")
            return

        if not self.competency_type_var.get():
            messagebox.showwarning("No Competency Type", "Please select a competency type.")
            return

        if not self.task_action_var.get() or not self.task_object_var.get():
            messagebox.showwarning("Missing Task Info", "Please provide task action and object.")
            return

        # --- NEW: Detect edit mode ---
        editing_existing = self.selected_assignment_id is not None

        try:
            comp_type = self.competency_type_var.get()

            # Each assignment function must accept editing_existing as a parameter!
            if comp_type == "mechanical":
                self.create_mechanical_assignment(editing_existing=editing_existing)
            elif comp_type == "electrical":
                self.create_electrical_assignment(editing_existing=editing_existing)
            elif comp_type == "tools":
                self.create_tools_assignment(editing_existing=editing_existing)
            elif comp_type == "operational":
                self.create_operational_assignment(editing_existing=editing_existing)
            elif comp_type == "safety":
                self.create_safety_assignment(editing_existing=editing_existing)
            elif comp_type == "training":
                self.create_training_assignment(editing_existing=editing_existing)
            elif comp_type == "communication":
                self.create_communication_assignment(editing_existing=editing_existing)
            elif comp_type == "leadership":
                self.create_leadership_assignment(editing_existing=editing_existing)
            else:
                messagebox.showinfo("Not Implemented", f"{comp_type} competency type not yet implemented.")
                return

            # --- Always clear edit state after save ---
            self.selected_assignment_id = None
            self.selected_assignment_type = None

            messagebox.showinfo("Success", "Competency assignment saved successfully!")
            self.reset_form()
            self.refresh_current_task_details()  # Always refresh the table!

        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to save assignment: {e}")

    def create_mechanical_assignment(self, editing_existing=False):
        """Create or update mechanical skill and task assignment with proper linking"""
        widgets = self.dynamic_widgets['mechanical']
        custom_name = self.get_current_competency_name()

        # Normalize all fields
        sub_category = normalize_str(widgets['subcategory'].get())
        equipment_category = normalize_str(widgets['equipment'].get())
        level_value = normalize_str(widgets.get('level', tk.StringVar()).get())
        proficiency_value = normalize_str(widgets.get('proficiency', tk.StringVar()).get())
        custom_name = normalize_str(custom_name)

        try:
            # 1. Find or create MechanicalSkill (base competency)
            skill = self.session.query(MechanicalSkill).filter_by(
                sub_category=sub_category,
                equipment_category=equipment_category,
                level=level_value,
                proficiency_level=proficiency_value
            ).first()
            if skill:
                skill.competency_name = custom_name
                skill.description = f"{sub_category} maintenance and repair"
                skill.level = level_value
                skill.proficiency_level = proficiency_value
            else:
                skill = MechanicalSkill(
                    competency_name=custom_name,
                    description=f"{sub_category} maintenance and repair",
                    skill_category='Mechanical',
                    competency_type='mechanical',
                    sub_category=sub_category,
                    equipment_category=equipment_category,
                    level=level_value,
                    proficiency_level=proficiency_value
                )
                self.session.add(skill)
                self.session.flush()

            # 2. Find or create MechanicalTask for this skill+action+object
            task_action = self.task_action_var.get()
            task_object = self.task_object_var.get()
            verification = self.verification_text.get('1.0', tk.END).strip()
            task = self.session.query(MechanicalTask).filter_by(
                sub_category=skill.sub_category,
                equipment_category=skill.equipment_category,
                task_action=task_action,
                task_object=task_object
            ).first()
            if task:
                # Update task
                task.competency_name = custom_name
                task.description = f"{task_action} {task_object}"
                task.verification_method = verification
            else:
                # Create new
                task = MechanicalTask(
                    competency_name=custom_name,
                    description=f"{task_action} {task_object}",
                    skill_category='Mechanical',
                    competency_type='mechanical_task',
                    sub_category=skill.sub_category,
                    equipment_category=skill.equipment_category,
                    task_action=task_action,
                    task_object=task_object,
                    verification_method=verification
                )
                self.session.add(task)
                self.session.flush()

            # 3. Link checklist task to base competency (if not already linked)
            comp_link = self.session.query(ChecklistTaskCompetency).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                competency_id=skill.id
            ).first()
            if not comp_link:
                comp_link = ChecklistTaskCompetency(
                    checklist_task_id=self.current_checklist_task.id,
                    competency_id=skill.id
                )
                self.session.add(comp_link)

            # 4. Link (or update) TaskSkillAssignment for this task
            task_assignment = self.session.query(TaskSkillAssignment).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                mechanical_task_id=task.id
            ).first()
            if not task_assignment:
                task_assignment = TaskSkillAssignment(
                    checklist_task_id=self.current_checklist_task.id,
                    mechanical_task_id=task.id
                )
                self.session.add(task_assignment)

            self.session.commit()

            print(f"✅ Created/updated mechanical competency assignment:")
            print(f"   - Base Competency: {skill.competency_name} (ID: {skill.id})")
            print(f"   - Level: {skill.level}")
            print(f"   - Proficiency Level: {skill.proficiency_level}")
            print(f"   - Specific Task: {task.task_action} {task.task_object} (ID: {task.id})")

        except Exception as e:
            self.session.rollback()
            raise e

    def create_operational_assignment(self, editing_existing=False):
        """Create or update operational skill and task assignment with proper linking."""
        widgets = self.dynamic_widgets['operational']
        custom_name = widgets['competency_name'].get().strip()
        level_value = widgets.get('level', tk.StringVar()).get().strip() or None
        proficiency_value = widgets.get('proficiency', tk.StringVar()).get().strip() or None

        try:
            # 1. Find or create OperationalSkill (competency)
            skill = self.session.query(OperationalSkill).filter_by(
                operation_type=widgets['operation_type'].get().strip(),
                machine_type=widgets['machine_type'].get().strip(),
                level=level_value,
                proficiency_level=proficiency_value
            ).first()
            if skill:
                skill.competency_name = custom_name
                skill.description = f"{widgets['operation_type'].get()} operation of {widgets['machine_type'].get()}"
            else:
                skill = OperationalSkill(
                    competency_name=custom_name,
                    description=f"{widgets['operation_type'].get()} operation of {widgets['machine_type'].get()}",
                    competency_type='operational',
                    operation_type=widgets['operation_type'].get().strip(),
                    machine_type=widgets['machine_type'].get().strip(),
                    level=level_value,
                    proficiency_level=proficiency_value
                )
                self.session.add(skill)
                self.session.flush()

            # 2. Find or create OperationalTask for this skill+action+object
            task_action = self.task_action_var.get()
            task_object = self.task_object_var.get()
            verification = self.verification_text.get('1.0', tk.END).strip()
            task = self.session.query(OperationalTask).filter_by(
                operation_type=skill.operation_type,
                machine_type=skill.machine_type,
                task_action=task_action,
                task_object=task_object
            ).first()
            if task:
                # Update task
                task.competency_name = custom_name
                task.description = f"{task_action} {task_object}"
                task.verification_method = verification
            else:
                # Create new
                task = OperationalTask(
                    competency_name=custom_name,
                    description=f"{task_action} {task_object}",
                    competency_type='operational_task',
                    operation_type=skill.operation_type,
                    machine_type=skill.machine_type,
                    task_action=task_action,
                    task_object=task_object,
                    verification_method=verification
                )
                self.session.add(task)
                self.session.flush()

            # 3. Link ChecklistTask to OperationalSkill (competency assignment)
            existing_competency_link = self.session.query(ChecklistTaskCompetency).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                competency_id=skill.id
            ).first()
            if not existing_competency_link:
                self.session.add(ChecklistTaskCompetency(
                    checklist_task_id=self.current_checklist_task.id,
                    competency_id=skill.id
                ))

            # 4. Link (or update) TaskSkillAssignment for this task
            existing_task_assignment = self.session.query(TaskSkillAssignment).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                operational_task_id=task.id
            ).first()
            if not existing_task_assignment:
                self.session.add(TaskSkillAssignment(
                    checklist_task_id=self.current_checklist_task.id,
                    operational_task_id=task.id
                ))

            self.session.commit()
            print("✅ Operational assignment created/updated.")

        except Exception as e:
            self.session.rollback()
            raise e

    def create_electrical_assignment(self, editing_existing=False):
        """Create or update electrical skill and task assignment with proper linking"""
        widgets = self.dynamic_widgets['electrical']
        custom_name = self.get_current_competency_name()

        try:
            # 1. Find or create the base ElectricalSkill
            skill_data = {
                'competency_name': custom_name,
                'description': f"{widgets['subcategory'].get()} installation and maintenance",
                'skill_category': 'Electrical',
                'competency_type': 'electrical',
                'sub_category': widgets['subcategory'].get(),
                'voltage_level': widgets['voltage'].get(),
                'level': widgets['level'].get() or None,
                'proficiency_level': widgets.get('proficiency', tk.StringVar()).get() or None
            }

            existing_skill = self.session.query(ElectricalSkill).filter_by(
                sub_category=skill_data['sub_category'],
                voltage_level=skill_data['voltage_level'],
                level=skill_data['level'],
                proficiency_level=skill_data['proficiency_level']
            ).first()

            if existing_skill:
                skill = existing_skill
                skill.competency_name = custom_name
                skill.description = skill_data['description']
                skill.level = skill_data['level']
                skill.proficiency_level = skill_data['proficiency_level']
            else:
                skill = ElectricalSkill(**skill_data)
                self.session.add(skill)
                self.session.flush()

            # 2. Find or create the ElectricalTask (by all unique task fields)
            task_action = self.task_action_var.get()
            task_object = self.task_object_var.get()
            verification = self.verification_text.get('1.0', tk.END).strip()

            existing_task = self.session.query(ElectricalTask).filter_by(
                sub_category=skill.sub_category,
                voltage_level=skill.voltage_level,
                task_action=task_action,
                task_object=task_object
            ).first()

            if existing_task:
                task = existing_task
                task.competency_name = custom_name
                task.description = f"{task_action} {task_object}"
                task.verification_method = verification
            else:
                task = ElectricalTask(
                    competency_name=custom_name,
                    description=f"{task_action} {task_object}",
                    skill_category='Electrical',
                    competency_type='electrical_task',
                    sub_category=skill.sub_category,
                    voltage_level=skill.voltage_level,
                    task_action=task_action,
                    task_object=task_object,
                    verification_method=verification
                )
                self.session.add(task)
                self.session.flush()

            # 3. Link checklist task to base competency
            existing_competency_link = self.session.query(ChecklistTaskCompetency).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                competency_id=skill.id
            ).first()
            if not existing_competency_link:
                self.session.add(ChecklistTaskCompetency(
                    checklist_task_id=self.current_checklist_task.id,
                    competency_id=skill.id
                ))

            # 4. Link or update TaskSkillAssignment for this checklist+task
            existing_task_assignment = self.session.query(TaskSkillAssignment).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                electrical_task_id=task.id
            ).first()
            if not existing_task_assignment:
                self.session.add(TaskSkillAssignment(
                    checklist_task_id=self.current_checklist_task.id,
                    electrical_task_id=task.id
                ))

            self.session.commit()

            print(f"✅ Created/updated electrical competency assignment:")
            print(f"   - Base Competency: {skill.competency_name} (ID: {skill.id})")
            print(f"   - Level: {skill.level}")
            print(f"   - Proficiency Level: {skill.proficiency_level}")
            print(f"   - Specific Task: {task.task_action} {task.task_object} (ID: {task.id})")
            print(f"   - Linked to Checklist Task: {self.current_checklist_task.task_description}")

        except Exception as e:
            self.session.rollback()
            raise e

    def create_tools_assignment(self, editing_existing=False):
        """Create or update tools skill and task assignment with proper linking"""
        widgets = self.dynamic_widgets['tools']
        custom_name = self.get_current_competency_name()
        level_value = widgets.get('level', tk.StringVar()).get().strip() or None
        proficiency_value = widgets.get('proficiency', tk.StringVar()).get().strip() or None

        try:
            # 1. Find or create ToolSkill (competency)
            skill = self.session.query(ToolSkill).filter_by(
                tool_type=widgets['tool_type'].get(),
                primary_application=widgets['application'].get(),
                level=level_value,
                proficiency_level=proficiency_value
            ).first()
            if skill:
                skill.competency_name = custom_name
                skill.description = f"{widgets['tool_type'].get()} usage and maintenance"
                skill.level = level_value
                skill.proficiency_level = proficiency_value
            else:
                skill = ToolSkill(
                    competency_name=custom_name,
                    description=f"{widgets['tool_type'].get()} usage and maintenance",
                    skill_category='Tools',
                    competency_type='tools',
                    tool_type=widgets['tool_type'].get(),
                    primary_application=widgets['application'].get(),
                    level=level_value,
                    proficiency_level=proficiency_value
                )
                self.session.add(skill)
                self.session.flush()

            # 2. Find or create ToolTask (by tool_type, application, task_action, task_object)
            task_action = self.task_action_var.get()
            task_object = self.task_object_var.get()
            verification = self.verification_text.get('1.0', tk.END).strip()

            task = self.session.query(ToolTask).filter_by(
                tool_type=skill.tool_type,
                primary_application=skill.primary_application,
                task_action=task_action,
                task_object=task_object
            ).first()
            if task:
                task.competency_name = custom_name
                task.description = f"{task_action} {task_object}"
                task.verification_method = verification
            else:
                task = ToolTask(
                    competency_name=custom_name,
                    description=f"{task_action} {task_object}",
                    skill_category='Tools',
                    competency_type='tool_task',
                    tool_type=skill.tool_type,
                    primary_application=skill.primary_application,
                    task_action=task_action,
                    task_object=task_object,
                    verification_method=verification
                )
                self.session.add(task)
                self.session.flush()

            # 3. Link ChecklistTask to ToolSkill (competency assignment)
            existing_competency_link = self.session.query(ChecklistTaskCompetency).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                competency_id=skill.id
            ).first()
            if not existing_competency_link:
                self.session.add(ChecklistTaskCompetency(
                    checklist_task_id=self.current_checklist_task.id,
                    competency_id=skill.id
                ))

            # 4. Link (or update) TaskSkillAssignment for this task
            existing_task_assignment = self.session.query(TaskSkillAssignment).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                tool_task_id=task.id
            ).first()
            if not existing_task_assignment:
                self.session.add(TaskSkillAssignment(
                    checklist_task_id=self.current_checklist_task.id,
                    tool_task_id=task.id
                ))

            self.session.commit()
            print("✅ Tools assignment created/updated.")

        except Exception as e:
            self.session.rollback()
            raise e

    # Additional helper method to query what competencies are required for a checklist task
    def get_required_competencies_for_task(self, checklist_task_id):
        """Get all competencies required for a specific checklist task"""
        return self.session.query(CoreCompetency).join(
            ChecklistTaskCompetency,
            CoreCompetency.id == ChecklistTaskCompetency.competency_id
        ).filter(
            ChecklistTaskCompetency.checklist_task_id == checklist_task_id
        ).all()

    # Helper method to query specific task implementations for a checklist task
    def get_task_implementations_for_checklist_task(self, checklist_task_id):
        """Get all specific task implementations for a checklist task"""
        assignments = self.session.query(TaskSkillAssignment).filter_by(
            checklist_task_id=checklist_task_id
        ).all()

        implementations = []
        for assignment in assignments:
            if assignment.mechanical_task_id:
                task = self.session.query(MechanicalTask).get(assignment.mechanical_task_id)
                implementations.append(('mechanical', task))
            elif assignment.electrical_task_id:
                task = self.session.query(ElectricalTask).get(assignment.electrical_task_id)
                implementations.append(('electrical', task))
            elif assignment.tool_task_id:
                task = self.session.query(ToolTask).get(assignment.tool_task_id)
                implementations.append(('tool', task))
            elif assignment.operational_task_id:
                task = self.session.query(OperationalTask).get(assignment.operational_task_id)
                implementations.append(('operational', task))

        return implementations

    def reset_form(self):
        """Reset all form fields"""
        # Reset task mode to existing
        self.task_mode_var.set("existing")
        self.on_task_mode_changed()

        # Reset other form fields
        self.competency_type_var.set('')
        self.task_action_var.set('')
        self.task_object_var.set('')
        self.verification_text.delete('1.0', tk.END)
        self.current_checklist_task = None

        # Clear task action combobox values since no competency type is selected
        if hasattr(self, 'task_action_combo'):
            self.task_action_combo['values'] = []

        # Clear dynamic section
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()
        self.dynamic_widgets.clear()

        # Clear preview
        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.config(state='disabled')

        # Clear current task details
        if hasattr(self, 'refresh_current_task_details'):
            self.refresh_current_task_details()

        # Repopulate dropdowns
        self.populate_checklist_dropdowns()

    def get_current_competency_name(self):
        comp_type = self.competency_type_var.get()
        if comp_type in self.dynamic_widgets and 'competency_name' in self.dynamic_widgets[comp_type]:
            return self.dynamic_widgets[comp_type]['competency_name'].get().strip()
        return ""

    def create_safety_section(self):
        """Create safety-specific form fields."""

        # --- Competency Name field (per-section) ---
        safety_comp_name_var = tk.StringVar()
        ttk.Label(self.dynamic_frame, text="Competency Name:").grid(row=0, column=0, sticky='e', pady=(0, 2))
        ttk.Entry(self.dynamic_frame, textvariable=safety_comp_name_var, width=40).grid(
            row=0, column=1, columnspan=3, sticky='w', padx=(0, 10), pady=(0, 2)
        )

        # --- Level and Proficiency fields side by side ---
        level_prof_frame = ttk.Frame(self.dynamic_frame)
        level_prof_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 8))

        # Level field
        ttk.Label(level_prof_frame, text="Level:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        self.safety_level_var = tk.StringVar()
        self.safety_level_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.safety_level_var,
            values=["Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"], width=15
        )
        self.safety_level_combo.grid(row=0, column=1, sticky='w', padx=(0, 20))
        self.safety_level_combo.set("Level 1")

        # Proficiency field
        ttk.Label(level_prof_frame, text="Proficiency:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        self.safety_proficiency_var = tk.StringVar()
        self.safety_proficiency_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.safety_proficiency_var,
            values=["A", "B", "C"], width=15
        )
        self.safety_proficiency_combo.grid(row=0, column=3, sticky='w')
        self.safety_proficiency_combo.set("A")

        # --- Add description ---
        desc_label = ttk.Label(self.dynamic_frame,
                               text="Specify the safety topic or standard and competency details.",
                               font=('TkDefaultFont', 9), foreground='gray')
        desc_label.grid(row=2, column=0, columnspan=4, sticky='w', pady=(0, 10))

        # --- Safety Subcategory (from DB or fallback) ---
        ttk.Label(self.dynamic_frame, text="Safety Topic:").grid(row=3, column=0, sticky='e', padx=(0, 5))
        self.safety_subcategory_var = tk.StringVar()
        subcats = self.get_safety_subcategories()
        self.safety_subcategory_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.safety_subcategory_var,
            values=subcats, width=25
        )
        self.safety_subcategory_combo.grid(row=3, column=1, sticky='w', padx=(0, 20))

        # --- Regulatory Standard (optional, e.g. OSHA, LOTO, etc.) ---
        ttk.Label(self.dynamic_frame, text="Regulatory Standard:").grid(row=3, column=2, sticky='e', padx=(0, 5))
        self.safety_reg_var = tk.StringVar()
        self.safety_reg_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.safety_reg_var,
            values=["OSHA", "LOTO", "PPE", "Fire Safety", "Ergonomics", "Other"], width=20
        )
        self.safety_reg_combo.grid(row=3, column=3, sticky='w')

        # --- Examples ---
        examples_label = ttk.Label(self.dynamic_frame, text="Examples:", font=('TkDefaultFont', 9, 'bold'))
        examples_label.grid(row=5, column=0, sticky='w', pady=(10, 5))
        examples_text = tk.Text(self.dynamic_frame, height=3, width=80, font=('TkDefaultFont', 8))
        examples_text.grid(row=6, column=0, columnspan=4, sticky='w')
        examples_text.insert('1.0',
                             "• LOTO - OSHA (for Lockout/Tagout procedures)\n"
                             "• PPE - OSHA (for personal protective equipment use)\n"
                             "• Fire Safety - Local Code (for fire extinguisher training)\n"
                             "• Ergonomics - Other (for safe lifting techniques)")
        examples_text.config(state='disabled')

        # Register all section-specific variables for saving (now includes proficiency)
        self.dynamic_widgets['safety'] = {
            'competency_name': safety_comp_name_var,
            'subcategory': self.safety_subcategory_var,
            'regulatory_standard': self.safety_reg_var,
            'level': self.safety_level_var,
            'proficiency': self.safety_proficiency_var
        }

    # Updated assignment methods to handle proficiency properly

    def get_safety_subcategories(self):
        """Get safety subcategories from DB or fallback."""
        try:
            safety_skills = self.session.query(CoreCompetency).filter(
                CoreCompetency.competency_type == 'safety'
            ).all()
            subcats = [skill.competency_name for skill in safety_skills if skill.competency_name]
            subcats = sorted(list(set(subcats)))
            if subcats:
                return subcats
        except Exception:
            pass
        return ["LOTO", "PPE", "Fire Safety", "HazCom", "Confined Space", "Ergonomics", "Chemical Safety"]

    def create_safety_assignment(self, editing_existing=False):
        """Create safety competency and task assignment with linking."""
        widgets = self.dynamic_widgets['safety']
        custom_name = widgets['competency_name'].get().strip()
        subcategory = widgets['subcategory'].get().strip()
        regulatory_standard = widgets['regulatory_standard'].get().strip()

        # Get both level and proficiency values
        level_value = widgets.get('level', tk.StringVar()).get().strip() or None
        proficiency_value = widgets.get('proficiency', tk.StringVar()).get().strip() or None

        try:
            # 1. Create or get the CoreCompetency for Safety
            skill_data = {
                'competency_name': custom_name,
                'description': f"{subcategory} - {regulatory_standard}",
                'competency_type': 'safety',
                'level': level_value,
                'proficiency_level': proficiency_value
            }

            # Use all fields for uniqueness
            existing_skill = self.session.query(CoreCompetency).filter_by(
                competency_name=custom_name,
                description=skill_data['description'],
                competency_type='safety',
                level=level_value,
                proficiency_level=proficiency_value
            ).first()

            if existing_skill:
                skill = existing_skill
                skill.description = skill_data['description']
                skill.level = level_value
                skill.proficiency_level = proficiency_value
            else:
                skill = CoreCompetency(**skill_data)
                self.session.add(skill)
                self.session.flush()

            # 2. Link checklist task to base competency
            existing_competency_link = self.session.query(ChecklistTaskCompetency).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                competency_id=skill.id
            ).first()
            if not existing_competency_link:
                competency_assignment = ChecklistTaskCompetency(
                    checklist_task_id=self.current_checklist_task.id,
                    competency_id=skill.id
                )
                self.session.add(competency_assignment)

            self.session.commit()
            print(f"✅ Created safety competency assignment: {skill.competency_name} (ID: {skill.id})")
            print(f"   - Level: {skill.level}")
            print(f"   - Proficiency Level: {skill.proficiency_level}")

        except Exception as e:
            self.session.rollback()
            raise e

    def create_training_section(self):
        """Create training-specific form fields."""

        # Competency Name
        training_comp_name_var = tk.StringVar()
        ttk.Label(self.dynamic_frame, text="Competency Name:").grid(row=0, column=0, sticky='e', pady=(0, 2))
        ttk.Entry(self.dynamic_frame, textvariable=training_comp_name_var, width=40).grid(
            row=0, column=1, columnspan=3, sticky='w', padx=(0, 10), pady=(0, 2)
        )

        # --- Level and Proficiency fields side by side ---
        level_prof_frame = ttk.Frame(self.dynamic_frame)
        level_prof_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 8))

        # Level field
        ttk.Label(level_prof_frame, text="Level:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        self.training_level_var = tk.StringVar()
        self.training_level_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.training_level_var,
            values=["Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"], width=15
        )
        self.training_level_combo.grid(row=0, column=1, sticky='w', padx=(0, 20))
        self.training_level_combo.set("Level 1")

        # Proficiency field
        ttk.Label(level_prof_frame, text="Proficiency:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        self.training_proficiency_var = tk.StringVar()
        self.training_proficiency_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.training_proficiency_var,
            values=["A", "B", "C"], width=15
        )
        self.training_proficiency_combo.grid(row=0, column=3, sticky='w')
        self.training_proficiency_combo.set("A")

        # Training Type
        ttk.Label(self.dynamic_frame, text="Training Type:").grid(row=2, column=0, sticky='e', padx=(0, 5))
        self.training_type_var = tk.StringVar()
        self.training_type_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.training_type_var,
            values=["Mentoring", "Knowledge Transfer", "Skill Development"], width=20
        )
        self.training_type_combo.grid(row=2, column=1, sticky='w', padx=(0, 20))

        # Training Method
        ttk.Label(self.dynamic_frame, text="Training Method:").grid(row=2, column=2, sticky='e', padx=(0, 5))
        self.training_method_var = tk.StringVar()
        self.training_method_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.training_method_var,
            values=["One-on-one", "Group", "Hands-on", "Classroom"], width=20
        )
        self.training_method_combo.grid(row=2, column=3, sticky='w')

        # Examples
        examples_label = ttk.Label(self.dynamic_frame, text="Examples:", font=('TkDefaultFont', 9, 'bold'))
        examples_label.grid(row=3, column=0, sticky='w', pady=(10, 5))
        examples_text = tk.Text(self.dynamic_frame, height=3, width=80, font=('TkDefaultFont', 8))
        examples_text.grid(row=4, column=0, columnspan=4, sticky='w')
        examples_text.insert('1.0',
                             "• Mentoring - One-on-one (Senior mentoring junior tech)\n"
                             "• Knowledge Transfer - Group (Group classroom training)\n"
                             "• Skill Development - Hands-on (Hands-on practice on machine)")
        examples_text.config(state='disabled')

        self.dynamic_widgets['training'] = {
            'competency_name': training_comp_name_var,
            'training_type': self.training_type_var,
            'training_method': self.training_method_var,
            'level': self.training_level_var,
            'proficiency': self.training_proficiency_var
        }

    def create_communication_section(self):
        """Create communication-specific form fields."""

        # Competency Name
        comm_comp_name_var = tk.StringVar()
        ttk.Label(self.dynamic_frame, text="Competency Name:").grid(row=0, column=0, sticky='e', pady=(0, 2))
        ttk.Entry(self.dynamic_frame, textvariable=comm_comp_name_var, width=40).grid(
            row=0, column=1, columnspan=3, sticky='w', padx=(0, 10), pady=(0, 2)
        )

        # --- Level and Proficiency fields side by side ---
        level_prof_frame = ttk.Frame(self.dynamic_frame)
        level_prof_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 8))

        # Level field
        ttk.Label(level_prof_frame, text="Level:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        self.comm_level_var = tk.StringVar()
        self.comm_level_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.comm_level_var,
            values=["Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"], width=15
        )
        self.comm_level_combo.grid(row=0, column=1, sticky='w', padx=(0, 20))
        self.comm_level_combo.set("Level 1")

        # Proficiency field
        ttk.Label(level_prof_frame, text="Proficiency:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        self.comm_proficiency_var = tk.StringVar()
        self.comm_proficiency_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.comm_proficiency_var,
            values=["A", "B", "C"], width=15
        )
        self.comm_proficiency_combo.grid(row=0, column=3, sticky='w')
        self.comm_proficiency_combo.set("A")

        # Communication Method
        ttk.Label(self.dynamic_frame, text="Communication Method:").grid(row=2, column=0, sticky='e', padx=(0, 5))
        self.communication_method_var = tk.StringVar()
        self.communication_method_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.communication_method_var,
            values=["Verbal", "Written", "Technical", "Presentation"], width=20
        )
        self.communication_method_combo.grid(row=2, column=1, sticky='w', padx=(0, 20))

        # Audience
        ttk.Label(self.dynamic_frame, text="Audience:").grid(row=2, column=2, sticky='e', padx=(0, 5))
        self.communication_audience_var = tk.StringVar()
        self.communication_audience_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.communication_audience_var,
            values=["Peer", "Supervisor", "Team", "Customer", "Executive"], width=20
        )
        self.communication_audience_combo.grid(row=2, column=3, sticky='w')

        # Examples
        examples_label = ttk.Label(self.dynamic_frame, text="Examples:", font=('TkDefaultFont', 9, 'bold'))
        examples_label.grid(row=3, column=0, sticky='w', pady=(10, 5))
        examples_text = tk.Text(self.dynamic_frame, height=3, width=80, font=('TkDefaultFont', 8))
        examples_text.grid(row=4, column=0, columnspan=4, sticky='w')
        examples_text.insert('1.0',
                             "• Technical - Team (Explaining SOPs to maintenance team)\n"
                             "• Presentation - Executive (Presenting KPIs to managers)\n"
                             "• Written - Customer (Writing maintenance reports for customers)")
        examples_text.config(state='disabled')

        self.dynamic_widgets['communication'] = {
            'competency_name': comm_comp_name_var,
            'communication_method': self.communication_method_var,
            'communication_audience': self.communication_audience_var,
            'level': self.comm_level_var,
            'proficiency': self.comm_proficiency_var
        }

    def create_leadership_section(self):
        """Create leadership-specific form fields."""

        # Competency Name
        lead_comp_name_var = tk.StringVar()
        ttk.Label(self.dynamic_frame, text="Competency Name:").grid(row=0, column=0, sticky='e', pady=(0, 2))
        ttk.Entry(self.dynamic_frame, textvariable=lead_comp_name_var, width=40).grid(
            row=0, column=1, columnspan=3, sticky='w', padx=(0, 10), pady=(0, 2)
        )

        # --- Level and Proficiency fields side by side ---
        level_prof_frame = ttk.Frame(self.dynamic_frame)
        level_prof_frame.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(0, 8))

        # Level field
        ttk.Label(level_prof_frame, text="Level:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        self.lead_level_var = tk.StringVar()
        self.lead_level_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.lead_level_var,
            values=["Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"], width=15
        )
        self.lead_level_combo.grid(row=0, column=1, sticky='w', padx=(0, 20))
        self.lead_level_combo.set("Level 1")

        # Proficiency field
        ttk.Label(level_prof_frame, text="Proficiency:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        self.lead_proficiency_var = tk.StringVar()
        self.lead_proficiency_combo = ttk.Combobox(
            level_prof_frame, textvariable=self.lead_proficiency_var,
            values=["A", "B", "C"], width=15
        )
        self.lead_proficiency_combo.grid(row=0, column=3, sticky='w')
        self.lead_proficiency_combo.set("A")

        # Leadership Type
        ttk.Label(self.dynamic_frame, text="Leadership Type:").grid(row=2, column=0, sticky='e', padx=(0, 5))
        self.leadership_type_var = tk.StringVar()
        self.leadership_type_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.leadership_type_var,
            values=["Team Direction", "Conflict Resolution", "Decision Making"], width=20
        )
        self.leadership_type_combo.grid(row=2, column=1, sticky='w', padx=(0, 20))

        # Scope
        ttk.Label(self.dynamic_frame, text="Scope:").grid(row=2, column=2, sticky='e', padx=(0, 5))
        self.leadership_scope_var = tk.StringVar()
        self.leadership_scope_combo = ttk.Combobox(
            self.dynamic_frame, textvariable=self.leadership_scope_var,
            values=["Individual", "Team", "Department", "Organization"], width=20
        )
        self.leadership_scope_combo.grid(row=2, column=3, sticky='w')

        # Examples
        examples_label = ttk.Label(self.dynamic_frame, text="Examples:", font=('TkDefaultFont', 9, 'bold'))
        examples_label.grid(row=3, column=0, sticky='w', pady=(10, 5))
        examples_text = tk.Text(self.dynamic_frame, height=3, width=80, font=('TkDefaultFont', 8))
        examples_text.grid(row=4, column=0, columnspan=4, sticky='w')
        examples_text.insert('1.0',
                             "• Team Direction - Team (Leading daily shift meetings)\n"
                             "• Conflict Resolution - Individual (Resolving disputes among technicians)\n"
                             "• Decision Making - Organization (Making staffing decisions for site)")
        examples_text.config(state='disabled')

        self.dynamic_widgets['leadership'] = {
            'competency_name': lead_comp_name_var,
            'leadership_type': self.leadership_type_var,
            'leadership_scope': self.leadership_scope_var,
            'level': self.lead_level_var,
            'proficiency': self.lead_proficiency_var
        }

    def create_training_assignment(self, editing_existing=False):
        widgets = self.dynamic_widgets['training']
        custom_name = widgets['competency_name'].get().strip()

        # Get both level and proficiency values
        level_value = widgets.get('level', tk.StringVar()).get().strip() or None
        proficiency_value = widgets.get('proficiency', tk.StringVar()).get().strip() or None

        training_type = widgets['training_type'].get().strip()
        training_method = widgets['training_method'].get().strip()

        try:
            skill_data = {
                'competency_name': custom_name,
                'description': f"{training_type} - {training_method}",
                'competency_type': 'training',
                'training_type': training_type,
                'training_method': training_method,
                'level': level_value,
                'proficiency_level': proficiency_value
            }

            existing_skill = self.session.query(TrainingCompetency).filter_by(
                training_type=training_type,
                training_method=training_method,
                level=level_value,
                proficiency_level=proficiency_value
            ).first()

            if existing_skill:
                skill = existing_skill
                skill.competency_name = custom_name
                skill.description = skill_data['description']
                skill.level = level_value
                skill.proficiency_level = proficiency_value
            else:
                skill = TrainingCompetency(**skill_data)
                self.session.add(skill)
                self.session.flush()

            existing_competency_link = self.session.query(ChecklistTaskCompetency).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                competency_id=skill.id
            ).first()
            if not existing_competency_link:
                competency_assignment = ChecklistTaskCompetency(
                    checklist_task_id=self.current_checklist_task.id,
                    competency_id=skill.id
                )
                self.session.add(competency_assignment)

            self.session.commit()
            print(f"✅ Created training competency assignment: {skill.competency_name} (ID: {skill.id})")
            print(f"   - Level: {skill.level}")
            print(f"   - Proficiency Level: {skill.proficiency_level}")

        except Exception as e:
            self.session.rollback()
            raise e

    def create_communication_assignment(self, editing_existing=False):
        widgets = self.dynamic_widgets['communication']
        custom_name = widgets['competency_name'].get().strip()

        # Get both level and proficiency values
        level_value = widgets.get('level', tk.StringVar()).get().strip() or None
        proficiency_value = widgets.get('proficiency', tk.StringVar()).get().strip() or None

        method = widgets['communication_method'].get().strip()
        audience = widgets['communication_audience'].get().strip()

        try:
            skill_data = {
                'competency_name': custom_name,
                'description': f"{method} to {audience}",
                'competency_type': 'communication',
                'communication_method': method,
                'communication_audience': audience,
                'level': level_value,
                'proficiency_level': proficiency_value
            }

            existing_skill = self.session.query(CommunicationCompetency).filter_by(
                communication_method=method,
                communication_audience=audience,
                level=level_value,
                proficiency_level=proficiency_value
            ).first()

            if existing_skill:
                skill = existing_skill
                skill.competency_name = custom_name
                skill.description = skill_data['description']
                skill.level = level_value
                skill.proficiency_level = proficiency_value
            else:
                skill = CommunicationCompetency(**skill_data)
                self.session.add(skill)
                self.session.flush()

            existing_competency_link = self.session.query(ChecklistTaskCompetency).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                competency_id=skill.id
            ).first()
            if not existing_competency_link:
                competency_assignment = ChecklistTaskCompetency(
                    checklist_task_id=self.current_checklist_task.id,
                    competency_id=skill.id
                )
                self.session.add(competency_assignment)

            self.session.commit()
            print(f"✅ Created communication competency assignment: {skill.competency_name} (ID: {skill.id})")
            print(f"   - Level: {skill.level}")
            print(f"   - Proficiency Level: {skill.proficiency_level}")

        except Exception as e:
            self.session.rollback()
            raise e

    def create_leadership_assignment(self, editing_existing=False):
        widgets = self.dynamic_widgets['leadership']
        custom_name = widgets['competency_name'].get().strip()

        # Get both level and proficiency values
        level_value = widgets.get('level', tk.StringVar()).get().strip() or None
        proficiency_value = widgets.get('proficiency', tk.StringVar()).get().strip() or None

        lead_type = widgets['leadership_type'].get().strip()
        scope = widgets['leadership_scope'].get().strip()

        try:
            skill_data = {
                'competency_name': custom_name,
                'description': f"{lead_type} for {scope}",
                'competency_type': 'leadership',
                'leadership_type': lead_type,
                'leadership_scope': scope,
                'level': level_value,
                'proficiency_level': proficiency_value
            }

            existing_skill = self.session.query(LeadershipCompetency).filter_by(
                leadership_type=lead_type,
                leadership_scope=scope,
                level=level_value,
                proficiency_level=proficiency_value
            ).first()

            if existing_skill:
                skill = existing_skill
                skill.competency_name = custom_name
                skill.description = skill_data['description']
                skill.level = level_value
                skill.proficiency_level = proficiency_value
            else:
                skill = LeadershipCompetency(**skill_data)
                self.session.add(skill)
                self.session.flush()

            existing_competency_link = self.session.query(ChecklistTaskCompetency).filter_by(
                checklist_task_id=self.current_checklist_task.id,
                competency_id=skill.id
            ).first()
            if not existing_competency_link:
                competency_assignment = ChecklistTaskCompetency(
                    checklist_task_id=self.current_checklist_task.id,
                    competency_id=skill.id
                )
                self.session.add(competency_assignment)

            self.session.commit()
            print(f"✅ Created leadership competency assignment: {skill.competency_name} (ID: {skill.id})")
            print(f"   - Level: {skill.level}")
            print(f"   - Proficiency Level: {skill.proficiency_level}")

        except Exception as e:
            self.session.rollback()
            raise e

    def save_task_table_edit(self, item_id, field, new_value):
        """
        Save an edit from the task details table directly to the DB.
        Adjust this logic to match your schema!
        """
        # Retrieve your model object using item_id (could be TaskSkillAssignment or MechanicalTask, etc.)
        # Example for MechanicalTask:
        task = self.session.query(MechanicalTask).get(int(item_id))
        if not task:
            return
        try:
            if field == 'competency':
                task.competency_name = new_value
            elif field == 'level':
                task.level = new_value
            elif field == 'proficiency':
                task.proficiency_level = new_value
            elif field == 'details':
                task.description = new_value  # Or another appropriate attribute
            self.session.commit()
            # Optionally: refresh table or display a message
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to save edit: {e}")

    def on_task_details_tree_double_click(self, event):
        """Handle double-click editing of treeview cells with updated column mapping."""
        item_id = self.task_details_tree.identify_row(event.y)
        column = self.task_details_tree.identify_column(event.x)

        if not item_id or column == '#0':
            return

        # Updated column mapping to match your new structure
        editable_columns = {
            '#1': ('Type', False),  # Column 1 - Not editable
            '#2': ('Competency/Task Name', True),  # Column 2 - Editable
            '#3': ('Level', True),  # Column 3 - Editable
            '#4': ('Proficiency', True),  # Column 4 - Editable
            '#5': ('Task Action', True),  # Column 5 - Editable (NEW)
            '#6': ('Task Object', True),  # Column 6 - Editable (NEW)
            '#7': ('Verification Method', True)  # Column 7 - Editable (NEW)
        }

        if column not in editable_columns:
            return

        column_name, is_editable = editable_columns[column]

        if not is_editable:
            messagebox.showinfo("Column Not Editable",
                                f"The '{column_name}' column cannot be edited.")
            return

        # Check if this is a competency row and prevent editing task-specific fields
        tags = self.task_details_tree.item(item_id, 'tags')
        if 'competency' in tags and column_name in ['Task Action', 'Task Object', 'Verification Method']:
            messagebox.showinfo("Not Applicable",
                                f"'{column_name}' does not apply to base competencies.\n"
                                f"This field is only editable for specific task implementations.")
            return

        # Use the correct method name: start_cell_edit (which you already have)
        self.start_cell_edit(item_id, column, column_name)

    def edit_name_column(self, item_id, column):
        """Edit the competency/task name column."""
        try:
            current_values = self.task_details_tree.item(item_id, 'values')
            current_name = current_values[1] if len(current_values) > 1 else ""

            bbox = self.task_details_tree.bbox(item_id, column)
            if not bbox:
                return

            x, y, width, height = bbox

            # Create text entry
            editor = tk.Entry(self.task_details_tree, font=('TkDefaultFont', 9))
            editor.insert(0, current_name)
            editor.place(x=x, y=y, width=width, height=height)
            editor.select_range(0, tk.END)
            editor.focus_set()

            def save_edit(event=None):
                new_value = editor.get().strip()
                editor.destroy()
                if new_value and new_value != current_name:
                    self.save_column_edit(item_id, 'name', new_value, current_name)

            def cancel_edit(event=None):
                editor.destroy()

            editor.bind('<Return>', save_edit)
            editor.bind('<Escape>', cancel_edit)
            editor.bind('<FocusOut>', save_edit)

        except Exception as e:
            messagebox.showerror("Edit Error", f"Could not edit name: {e}")

    def edit_level_column(self, item_id, column):
        """Edit the level column with dropdown."""
        try:
            current_values = self.task_details_tree.item(item_id, 'values')
            current_level = current_values[2] if len(current_values) > 2 else ""

            bbox = self.task_details_tree.bbox(item_id, column)
            if not bbox:
                return

            x, y, width, height = bbox

            # Level options
            level_options = ["", "Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"]

            # Create combobox
            level_var = tk.StringVar(value=current_level)
            editor = ttk.Combobox(self.task_details_tree, textvariable=level_var,
                                  values=level_options, state="normal", font=('TkDefaultFont', 9))
            editor.place(x=x, y=y, width=width, height=height)
            editor.set(current_level)
            editor.focus_set()

            def save_edit(event=None):
                new_value = level_var.get().strip()
                editor.destroy()
                if new_value != current_level:
                    self.save_column_edit(item_id, 'level', new_value, current_level)

            def cancel_edit(event=None):
                editor.destroy()

            editor.bind('<Return>', save_edit)
            editor.bind('<Escape>', cancel_edit)
            editor.bind('<FocusOut>', save_edit)
            editor.bind('<<ComboboxSelected>>', save_edit)

        except Exception as e:
            messagebox.showerror("Edit Error", f"Could not edit level: {e}")

    def edit_proficiency_column(self, item_id, column):
        """Edit the proficiency column with dropdown."""
        try:
            current_values = self.task_details_tree.item(item_id, 'values')
            current_proficiency = current_values[3] if len(current_values) > 3 else ""

            bbox = self.task_details_tree.bbox(item_id, column)
            if not bbox:
                return

            x, y, width, height = bbox

            # Proficiency options
            proficiency_options = ["", "A", "B", "C"]

            # Create combobox
            prof_var = tk.StringVar(value=current_proficiency)
            editor = ttk.Combobox(self.task_details_tree, textvariable=prof_var,
                                  values=proficiency_options, state="normal", font=('TkDefaultFont', 9))
            editor.place(x=x, y=y, width=width, height=height)
            editor.set(current_proficiency)
            editor.focus_set()

            def save_edit(event=None):
                new_value = prof_var.get().strip()
                editor.destroy()
                if new_value != current_proficiency:
                    self.save_column_edit(item_id, 'proficiency', new_value, current_proficiency)

            def cancel_edit(event=None):
                editor.destroy()

            editor.bind('<Return>', save_edit)
            editor.bind('<Escape>', cancel_edit)
            editor.bind('<FocusOut>', save_edit)
            editor.bind('<<ComboboxSelected>>', save_edit)

        except Exception as e:
            messagebox.showerror("Edit Error", f"Could not edit proficiency: {e}")

    def save_column_edit(self, item_id, column_type, new_value, old_value):
        """Save the edited column value to the database."""
        if new_value == old_value:
            return

        try:
            # Update the tree display first
            current_values = list(self.task_details_tree.item(item_id, 'values'))

            # Update the appropriate column
            if column_type == 'name':
                current_values[1] = new_value
            elif column_type == 'level':
                current_values[2] = new_value
            elif column_type == 'proficiency':
                current_values[3] = new_value

            self.task_details_tree.item(item_id, values=current_values)

            # Determine record type and update database
            tags = self.task_details_tree.item(item_id, 'tags')
            updated_object = None

            if 'competency' in tags:
                # Editing a core competency
                comp_id = int(item_id.split('_')[1])
                competency = self.session.query(CoreCompetency).get(comp_id)

                if competency:
                    if column_type == 'name':
                        competency.competency_name = new_value
                    elif column_type == 'level':
                        competency.level = new_value if new_value else None
                    elif column_type == 'proficiency':
                        competency.proficiency_level = new_value if new_value else None

                    updated_object = f"Competency (ID: {comp_id})"

            elif 'task' in tags:
                # Editing a specific task
                parts = item_id.split('_')
                task_type = parts[1]
                task_id = int(parts[2])

                # Get the appropriate task object
                task_obj = None
                if task_type == "mechanical":
                    task_obj = self.session.query(MechanicalTask).get(task_id)
                elif task_type == "electrical":
                    task_obj = self.session.query(ElectricalTask).get(task_id)
                elif task_type == "tool":
                    task_obj = self.session.query(ToolTask).get(task_id)
                elif task_type == "operational":
                    task_obj = self.session.query(OperationalTask).get(task_id)

                if task_obj:
                    if column_type == 'name':
                        task_obj.competency_name = new_value
                    elif column_type == 'level':
                        if hasattr(task_obj, 'level'):
                            task_obj.level = new_value if new_value else None
                    elif column_type == 'proficiency':
                        if hasattr(task_obj, 'proficiency_level'):
                            task_obj.proficiency_level = new_value if new_value else None

                    updated_object = f"{task_type.title()} Task (ID: {task_id})"

            if updated_object:
                # Commit changes
                self.session.commit()

                # Show brief success message
                print(f"✅ Updated {column_type} for {updated_object}: '{old_value}' → '{new_value}'")

                # Update status if available
                if hasattr(self, 'task_details_status'):
                    self.task_details_status.config(text=f"✅ Updated {column_type}: {new_value}")
                    self.after(3000, lambda: self.task_details_status.config(text=""))
            else:
                messagebox.showerror("Update Error", "Could not identify the record type to update.")

        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Save Error", f"Failed to save {column_type} change: {e}")
            # Refresh table to restore original values
            self.refresh_current_task_details()

    def save_task_details_edit(self, item_id, field, new_value):
        """
        Save an edit from the Current Task Details table directly to the DB.
        You may need to adjust this logic to match your actual models.
        """
        # item_id should be the primary key (id) of the corresponding DB record (e.g., MechanicalTask, ElectricalTask, etc.)
        # You may need logic to determine which table/model to use based on assignment type
        assignment_type = self.task_details_tree.set(item_id, "type")
        try:
            if assignment_type == "Mechanical":
                task = self.session.query(MechanicalTask).get(int(item_id))
                if task:
                    if field == 'competency':
                        task.competency_name = new_value
                    elif field == 'level':
                        task.level = new_value
                    elif field == 'proficiency':
                        task.proficiency_level = new_value
                    elif field == 'details':
                        task.description = new_value
                    self.session.commit()
            # Repeat for other assignment types if needed
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to save edit: {e}")

    def setup_editing_indicators(self):
        """Setup visual indicators for editable columns."""
        if hasattr(self, 'task_details_frame'):
            # Add instruction label if not already present
            if not hasattr(self, 'editing_instructions_added'):
                instruction_frame = ttk.Frame(self.task_details_frame)
                instruction_frame.pack(fill='x', pady=(0, 5))

                instruction_label = ttk.Label(instruction_frame,
                                              text="💡 Double-click on Name ✏️, Level ✏️, or Proficiency ✏️ columns to edit",
                                              font=('TkDefaultFont', 9), foreground='blue')
                instruction_label.pack(side='left')

                self.editing_instructions_added = True

    def start_dropdown_edit(self, item_id, column, column_name):
        """Start dropdown editing for Level and Proficiency columns."""
        try:
            # Get current value
            current_values = self.task_details_tree.item(item_id, 'values')
            col_index = int(column.replace('#', '')) - 1
            current_value = current_values[col_index] if col_index < len(current_values) else ""

            # Get cell bounding box
            bbox = self.task_details_tree.bbox(item_id, column)
            if not bbox:
                return

            x, y, width, height = bbox
            self.create_dropdown_cell_editor(item_id, column, column_name, current_value, x, y, width, height)

        except Exception as e:
            messagebox.showerror("Edit Error", f"Could not start editing: {e}")

    def create_text_cell_editor(self, item_id, column, column_name, current_value, x, y, width, height):
        """Create a text editor for text-based columns."""
        # Skip if value is "N/A"
        if current_value == "N/A":
            messagebox.showinfo("Not Applicable", f"This field is not applicable for this type of record.")
            return

        # Create text entry
        editor = tk.Entry(self.task_details_tree, font=('TkDefaultFont', 9))
        editor.insert(0, current_value)
        editor.place(x=x, y=y, width=width, height=height)
        editor.select_range(0, tk.END)
        editor.focus_set()

        def save_edit(event=None):
            new_value = editor.get().strip()
            editor.destroy()
            if new_value != current_value:
                self.save_cell_edit(item_id, column, column_name, new_value, current_value)

        def cancel_edit(event=None):
            editor.destroy()

        editor.bind('<Return>', save_edit)
        editor.bind('<Escape>', cancel_edit)
        editor.bind('<FocusOut>', save_edit)

    def start_text_edit(self, item_id, column, column_name):
        """Start text editing for text-based columns."""
        try:
            # Get current value
            current_values = self.task_details_tree.item(item_id, 'values')
            col_index = int(column.replace('#', '')) - 1
            current_value = current_values[col_index] if col_index < len(current_values) else ""

            # Skip if value is "N/A"
            if current_value == "N/A":
                messagebox.showinfo("Not Applicable", f"This field is not applicable for this type of record.")
                return

            # Get cell bounding box
            bbox = self.task_details_tree.bbox(item_id, column)
            if not bbox:
                return

            x, y, width, height = bbox

            # For Verification Method, create a larger text editor
            if column_name == 'Verification Method':
                self.create_verification_editor(item_id, column_name, current_value, x, y, width, height)
            else:
                # Regular text entry for other fields
                self.create_text_cell_editor(item_id, column, column_name, current_value, x, y, width, height)

        except Exception as e:
            messagebox.showerror("Edit Error", f"Could not start editing: {e}")

    def create_verification_editor(self, item_id, column_name, current_value, x, y, width, height):
        """Create a larger editor for verification method field."""
        # Create toplevel window for verification editing
        verify_window = tk.Toplevel(self.task_details_tree)
        verify_window.title("Edit Verification Method")
        verify_window.geometry("500x250")
        verify_window.transient(self.task_details_tree.winfo_toplevel())
        verify_window.grab_set()

        # Center the window
        verify_window.update_idletasks()
        x_pos = (verify_window.winfo_screenwidth() // 2) - (verify_window.winfo_width() // 2)
        y_pos = (verify_window.winfo_screenheight() // 2) - (verify_window.winfo_height() // 2)
        verify_window.geometry(f"+{x_pos}+{y_pos}")

        # Create text widget with scrollbar
        text_frame = ttk.Frame(verify_window)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)

        verify_text = tk.Text(text_frame, wrap='word', height=8, width=60)
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=verify_text.yview)
        verify_text.configure(yscrollcommand=scrollbar.set)

        verify_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Insert current value
        verify_text.insert('1.0', current_value)
        verify_text.focus_set()

        # Button frame
        button_frame = ttk.Frame(verify_window)
        button_frame.pack(fill='x', padx=10, pady=(0, 10))

        def save_verification():
            new_value = verify_text.get('1.0', tk.END).strip()
            verify_window.destroy()
            self.save_cell_edit(item_id, None, column_name, new_value, current_value)

        def cancel_verification():
            verify_window.destroy()

        ttk.Button(button_frame, text="Save", command=save_verification).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=cancel_verification).pack(side='right')

        # Bind Ctrl+Enter to save
        verify_text.bind('<Control-Return>', lambda e: save_verification())

    def edit_competency_popup(self, competency_id):
        """Create an enhanced popup editor for competency details based on competency type."""
        try:
            # Get the competency record
            competency = self.session.query(CoreCompetency).get(competency_id)
            if not competency:
                messagebox.showerror("Error", "Competency not found.")
                return

            comp_type = competency.competency_type

            # Create the popup window
            popup = tk.Toplevel(self.task_details_tree)
            popup.title(f"Edit {comp_type.title()} Competency")
            popup.geometry("600x500")
            popup.transient(self.task_details_tree.winfo_toplevel())
            popup.grab_set()

            # Center the window
            popup.update_idletasks()
            x_pos = (popup.winfo_screenwidth() // 2) - (popup.winfo_width() // 2)
            y_pos = (popup.winfo_screenheight() // 2) - (popup.winfo_height() // 2)
            popup.geometry(f"+{x_pos}+{y_pos}")

            # Create scrollable frame
            main_frame = ttk.Frame(popup)
            main_frame.pack(fill='both', expand=True, padx=10, pady=10)

            canvas = tk.Canvas(main_frame)
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # Title
            title_label = ttk.Label(scrollable_frame,
                                    text=f"Edit {comp_type.title()} Competency",
                                    font=('TkDefaultFont', 14, 'bold'))
            title_label.grid(row=0, column=0, columnspan=4, pady=(0, 20), sticky='w')

            # Store all form variables
            form_vars = {}
            current_row = 1

            # === COMMON FIELDS (All Competency Types) ===
            common_frame = ttk.LabelFrame(scrollable_frame, text="Basic Information", padding=10)
            common_frame.grid(row=current_row, column=0, columnspan=4, sticky='ew', pady=(0, 15))
            current_row += 1

            # Competency Name
            ttk.Label(common_frame, text="Competency Name:").grid(row=0, column=0, sticky='e', padx=(0, 5))
            form_vars['competency_name'] = tk.StringVar(value=competency.competency_name or "")
            ttk.Entry(common_frame, textvariable=form_vars['competency_name'], width=40).grid(
                row=0, column=1, columnspan=3, sticky='w', padx=(0, 10), pady=2)

            # Level and Proficiency side by side
            ttk.Label(common_frame, text="Level:").grid(row=1, column=0, sticky='e', padx=(0, 5), pady=(5, 0))
            form_vars['level'] = tk.StringVar(value=getattr(competency, 'level', '') or "")
            level_combo = ttk.Combobox(common_frame, textvariable=form_vars['level'],
                                       values=["", "Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"],
                                       width=15)
            level_combo.grid(row=1, column=1, sticky='w', padx=(0, 20), pady=(5, 0))

            ttk.Label(common_frame, text="Proficiency:").grid(row=1, column=2, sticky='e', padx=(0, 5), pady=(5, 0))
            form_vars['proficiency_level'] = tk.StringVar(value=getattr(competency, 'proficiency_level', '') or "")
            prof_combo = ttk.Combobox(common_frame, textvariable=form_vars['proficiency_level'],
                                      values=["", "A", "B", "C"], width=15)
            prof_combo.grid(row=1, column=3, sticky='w', pady=(5, 0))

            # Description
            ttk.Label(common_frame, text="Description:").grid(row=2, column=0, sticky='ne', padx=(0, 5), pady=(5, 0))
            form_vars['description'] = tk.StringVar(value=competency.description or "")
            desc_entry = ttk.Entry(common_frame, textvariable=form_vars['description'], width=50)
            desc_entry.grid(row=2, column=1, columnspan=3, sticky='w', pady=(5, 0))

            # === TYPE-SPECIFIC FIELDS ===
            type_frame = ttk.LabelFrame(scrollable_frame, text=f"{comp_type.title()}-Specific Details", padding=10)
            type_frame.grid(row=current_row, column=0, columnspan=4, sticky='ew', pady=(0, 15))
            current_row += 1

            # Create type-specific fields based on competency type
            if comp_type == 'mechanical':
                self.create_mechanical_popup_fields(type_frame, form_vars, competency)
            elif comp_type == 'electrical':
                self.create_electrical_popup_fields(type_frame, form_vars, competency)
            elif comp_type == 'tools':
                self.create_tools_popup_fields(type_frame, form_vars, competency)
            elif comp_type == 'operational':
                self.create_operational_popup_fields(type_frame, form_vars, competency)
            elif comp_type == 'safety':
                self.create_safety_popup_fields(type_frame, form_vars, competency)
            elif comp_type == 'training':
                self.create_training_popup_fields(type_frame, form_vars, competency)
            elif comp_type == 'communication':
                self.create_communication_popup_fields(type_frame, form_vars, competency)
            elif comp_type == 'leadership':
                self.create_leadership_popup_fields(type_frame, form_vars, competency)

            # === ACTION BUTTONS ===
            button_frame = ttk.Frame(scrollable_frame)
            button_frame.grid(row=current_row, column=0, columnspan=4, pady=(20, 0))

            def save_competency():
                """Save the edited competency data."""
                try:
                    # Update basic fields
                    competency.competency_name = form_vars['competency_name'].get().strip()
                    competency.level = form_vars['level'].get().strip() or None
                    competency.proficiency_level = form_vars['proficiency_level'].get().strip() or None
                    competency.description = form_vars['description'].get().strip()

                    # Update type-specific fields
                    if comp_type == 'mechanical':
                        competency.sub_category = form_vars.get('sub_category', tk.StringVar()).get().strip() or None
                        competency.equipment_category = form_vars.get('equipment_category',
                                                                      tk.StringVar()).get().strip() or None
                    elif comp_type == 'electrical':
                        competency.sub_category = form_vars.get('sub_category', tk.StringVar()).get().strip() or None
                        competency.voltage_level = form_vars.get('voltage_level', tk.StringVar()).get().strip() or None
                    elif comp_type == 'tools':
                        competency.tool_type = form_vars.get('tool_type', tk.StringVar()).get().strip() or None
                        competency.primary_application = form_vars.get('primary_application',
                                                                       tk.StringVar()).get().strip() or None
                    elif comp_type == 'operational':
                        competency.operation_type = form_vars.get('operation_type',
                                                                  tk.StringVar()).get().strip() or None
                        competency.machine_type = form_vars.get('machine_type', tk.StringVar()).get().strip() or None
                    # Add other types as needed...

                    self.session.commit()
                    popup.destroy()
                    self.refresh_current_task_details()
                    messagebox.showinfo("Success", "Competency updated successfully!")

                except Exception as e:
                    self.session.rollback()
                    messagebox.showerror("Error", f"Failed to save competency: {e}")

            def cancel_edit():
                popup.destroy()

            ttk.Button(button_frame, text="Save Changes", command=save_competency).pack(side='left', padx=(0, 10))
            ttk.Button(button_frame, text="Cancel", command=cancel_edit).pack(side='left')

            # Configure grid weights
            scrollable_frame.grid_columnconfigure(0, weight=1)
            common_frame.grid_columnconfigure(1, weight=1)
            type_frame.grid_columnconfigure(1, weight=1)

            # Bind mousewheel scrolling
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            popup.protocol("WM_DELETE_WINDOW", lambda: (canvas.unbind_all("<MouseWheel>"), cancel_edit()))

        except Exception as e:
            messagebox.showerror("Error", f"Failed to open competency editor: {e}")

    def create_mechanical_popup_fields(self, parent, form_vars, competency):
        """Create mechanical-specific fields in the popup."""
        # Mechanical System (sub_category)
        ttk.Label(parent, text="Mechanical System:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        form_vars['sub_category'] = tk.StringVar(value=getattr(competency, 'sub_category', '') or "")
        subcats = self.get_mechanical_subcategories()
        sub_combo = ttk.Combobox(parent, textvariable=form_vars['sub_category'], values=subcats, width=25)
        sub_combo.grid(row=0, column=1, sticky='w', padx=(0, 20))

        # Equipment Category
        ttk.Label(parent, text="Equipment Category:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        form_vars['equipment_category'] = tk.StringVar(value=getattr(competency, 'equipment_category', '') or "")
        equip_combo = ttk.Combobox(parent, textvariable=form_vars['equipment_category'], width=25)
        equip_combo.grid(row=0, column=3, sticky='w')

        # Update equipment when subcategory changes
        def update_equipment(event=None):
            subcategory = form_vars['sub_category'].get()
            equipment_options = self.get_equipment_categories_for_subcategory(subcategory)
            equip_combo['values'] = equipment_options

        sub_combo.bind("<<ComboboxSelected>>", update_equipment)
        # Initial population
        update_equipment()

    def create_electrical_popup_fields(self, parent, form_vars, competency):
        """Create electrical-specific fields in the popup."""
        # Electrical System (sub_category)
        ttk.Label(parent, text="Electrical System:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        form_vars['sub_category'] = tk.StringVar(value=getattr(competency, 'sub_category', '') or "")
        subcats = self.get_electrical_subcategories()
        ttk.Combobox(parent, textvariable=form_vars['sub_category'], values=subcats, width=25).grid(
            row=0, column=1, sticky='w', padx=(0, 20))

        # Voltage Level
        ttk.Label(parent, text="Voltage Level:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        form_vars['voltage_level'] = tk.StringVar(value=getattr(competency, 'voltage_level', '') or "")
        voltage_levels = self.get_electrical_voltage_levels()
        ttk.Combobox(parent, textvariable=form_vars['voltage_level'], values=voltage_levels, width=15).grid(
            row=0, column=3, sticky='w')

    def create_tools_popup_fields(self, parent, form_vars, competency):
        """Create tools-specific fields in the popup."""
        # Tool Type
        ttk.Label(parent, text="Tool Type:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        form_vars['tool_type'] = tk.StringVar(value=getattr(competency, 'tool_type', '') or "")
        tool_types = self.get_tool_types()
        ttk.Combobox(parent, textvariable=form_vars['tool_type'], values=tool_types, width=20).grid(
            row=0, column=1, sticky='w', padx=(0, 20))

        # Primary Application
        ttk.Label(parent, text="Primary Application:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        form_vars['primary_application'] = tk.StringVar(value=getattr(competency, 'primary_application', '') or "")
        applications = self.get_tool_applications()
        ttk.Combobox(parent, textvariable=form_vars['primary_application'], values=applications, width=15).grid(
            row=0, column=3, sticky='w')

    def create_operational_popup_fields(self, parent, form_vars, competency):
        """Create operational-specific fields in the popup."""
        # Operation Type
        ttk.Label(parent, text="Operation Type:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        form_vars['operation_type'] = tk.StringVar(value=getattr(competency, 'operation_type', '') or "")
        oper_types = self.get_operational_types()
        ttk.Combobox(parent, textvariable=form_vars['operation_type'], values=oper_types, width=20).grid(
            row=0, column=1, sticky='w', padx=(0, 20))

        # Machine Type
        ttk.Label(parent, text="Machine Type:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        form_vars['machine_type'] = tk.StringVar(value=getattr(competency, 'machine_type', '') or "")
        machine_types = self.get_operational_machine_types()
        ttk.Combobox(parent, textvariable=form_vars['machine_type'], values=machine_types, width=20).grid(
            row=0, column=3, sticky='w')

    def create_safety_popup_fields(self, parent, form_vars, competency):
        """Create safety-specific fields in the popup."""
        # For safety competencies, we might not have specific subcategory fields
        # But we can add any safety-specific attributes if they exist
        ttk.Label(parent, text="Safety Type:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        form_vars['safety_type'] = tk.StringVar(value=getattr(competency, 'safety_category', '') or "")
        safety_types = ["LOTO", "PPE", "Fire Safety", "HazCom", "Confined Space", "Ergonomics", "Chemical Safety"]
        ttk.Combobox(parent, textvariable=form_vars['safety_type'], values=safety_types, width=25).grid(
            row=0, column=1, sticky='w')

    def create_training_popup_fields(self, parent, form_vars, competency):
        """Create training-specific fields in the popup."""
        # Training Type
        ttk.Label(parent, text="Training Type:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        form_vars['training_type'] = tk.StringVar(value=getattr(competency, 'training_type', '') or "")
        training_types = ["Mentoring", "Knowledge Transfer", "Skill Development"]
        ttk.Combobox(parent, textvariable=form_vars['training_type'], values=training_types, width=20).grid(
            row=0, column=1, sticky='w', padx=(0, 20))

        # Training Method
        ttk.Label(parent, text="Training Method:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        form_vars['training_method'] = tk.StringVar(value=getattr(competency, 'training_method', '') or "")
        training_methods = ["One-on-one", "Group", "Hands-on", "Classroom"]
        ttk.Combobox(parent, textvariable=form_vars['training_method'], values=training_methods, width=20).grid(
            row=0, column=3, sticky='w')

    def create_communication_popup_fields(self, parent, form_vars, competency):
        """Create communication-specific fields in the popup."""
        # Communication Method
        ttk.Label(parent, text="Communication Method:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        form_vars['communication_method'] = tk.StringVar(value=getattr(competency, 'communication_method', '') or "")
        comm_methods = ["Verbal", "Written", "Technical", "Presentation"]
        ttk.Combobox(parent, textvariable=form_vars['communication_method'], values=comm_methods, width=20).grid(
            row=0, column=1, sticky='w', padx=(0, 20))

        # Communication Audience
        ttk.Label(parent, text="Audience:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        form_vars['communication_audience'] = tk.StringVar(
            value=getattr(competency, 'communication_audience', '') or "")
        audiences = ["Peer", "Supervisor", "Team", "Customer", "Executive"]
        ttk.Combobox(parent, textvariable=form_vars['communication_audience'], values=audiences, width=20).grid(
            row=0, column=3, sticky='w')

    def create_leadership_popup_fields(self, parent, form_vars, competency):
        """Create leadership-specific fields in the popup."""
        # Leadership Type
        ttk.Label(parent, text="Leadership Type:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        form_vars['leadership_type'] = tk.StringVar(value=getattr(competency, 'leadership_type', '') or "")
        lead_types = ["Team Direction", "Conflict Resolution", "Decision Making"]
        ttk.Combobox(parent, textvariable=form_vars['leadership_type'], values=lead_types, width=20).grid(
            row=0, column=1, sticky='w', padx=(0, 20))

        # Leadership Scope
        ttk.Label(parent, text="Scope:").grid(row=0, column=2, sticky='e', padx=(0, 5))
        form_vars['leadership_scope'] = tk.StringVar(value=getattr(competency, 'leadership_scope', '') or "")
        scopes = ["Individual", "Team", "Department", "Organization"]
        ttk.Combobox(parent, textvariable=form_vars['leadership_scope'], values=scopes, width=20).grid(
            row=0, column=3, sticky='w')

    # UPDATED: Modify your existing edit_selected_assignment method
    def edit_selected_assignment(self):
        """Edit the selected assignment by populating the form fields or opening popup editor."""
        selected = self.task_details_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an entry to edit.")
            return

        item_id = selected[0]
        tags = self.task_details_tree.item(item_id, 'tags')

        try:
            if 'competency' in tags:
                # For competencies, use the new popup editor
                comp_id = int(item_id.split('_')[1])
                self.edit_competency_popup(comp_id)

            elif 'task' in tags:
                # For tasks, use the existing form population method
                parts = item_id.split('_')
                task_type = parts[1]
                task_id = int(parts[2])

                if task_type == "mechanical":
                    task = self.session.query(MechanicalTask).get(task_id)
                    if task:
                        self.populate_form_for_mechanical_edit(task)
                elif task_type == "electrical":
                    task = self.session.query(ElectricalTask).get(task_id)
                    if task:
                        self.populate_form_for_electrical_edit(task)
                elif task_type == "tool":
                    task = self.session.query(ToolTask).get(task_id)
                    if task:
                        self.populate_form_for_tool_edit(task)
                elif task_type == "operational":
                    task = self.session.query(OperationalTask).get(task_id)
                    if task:
                        self.populate_form_for_operational_edit(task)

                # Store edit context for tasks
                self.selected_assignment_id = item_id
                self.selected_assignment_type = tags[1] if len(tags) > 1 else tags[0]

                messagebox.showinfo("Edit Mode",
                                    "Form populated for editing. Make your changes and click 'Save Assignment'.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load assignment for editing: {e}")

class StepUpEvalTab(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session

        # 1) Apply color scheme before creating widgets
        self.apply_stepup_theme()

        # Configure the main frame to expand
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create main canvas and scrollbar for vertical scrolling
        self.canvas = tk.Canvas(self)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        # Configure scrolling
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack canvas and scrollbar
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        # Configure the scrollable frame to expand
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        self.scrollable_frame.grid_columnconfigure(1, weight=1)

        # Create the form in the scrollable frame
        self.create_form()

        # Bind mousewheel to canvas for scrolling
        self.bind_mousewheel()

    def bind_mousewheel(self):
        """Bind mousewheel events for scrolling"""

        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_to_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_from_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")

        self.canvas.bind('<Enter>', _bind_to_mousewheel)
        self.canvas.bind('<Leave>', _unbind_from_mousewheel)

    def create_form(self):
        # Make sure results_var exists before any refresh calls
        self.results_var = getattr(self, "results_var", tk.StringVar(value=""))

        # Two top-aligned columns inside scrollable_frame
        self.scrollable_frame.grid_columnconfigure(0, weight=0)  # left column (fixed)
        self.scrollable_frame.grid_columnconfigure(1, weight=1)  # right column (expands)
        self.scrollable_frame.grid_rowconfigure(0, weight=1)  # allow right table to grow

        # ---------------- LEFT COLUMN CONTAINER (top-aligned) ----------------
        left_col = ttk.Frame(self.scrollable_frame)
        left_col.grid(row=0, column=0, sticky="nw", padx=5, pady=5)
        # Let sections inside left_col stretch horizontally
        for i in range(2):
            left_col.grid_columnconfigure(i, weight=1)

        # --- Employee (LEFT, top) ---
        ttk.Label(left_col, text="Employee").grid(row=0, column=0, sticky="w", padx=0, pady=(0, 2))
        self.employee_var = tk.StringVar()
        self.employee_combo = ttk.Combobox(left_col, textvariable=self.employee_var, state="readonly")
        self.employee_combo.grid(row=1, column=0, columnspan=2, padx=0, pady=(0, 6), sticky="ew")
        self.load_employees()
        self.employee_combo.bind("<<ComboboxSelected>>", self.on_employee_selected)

        # --- Employee Information Display (LEFT) ---
        self.employee_info_frame = ttk.LabelFrame(left_col, text="Employee Information", padding="10")
        self.employee_info_frame.grid(row=2, column=0, columnspan=2, padx=0, pady=(0, 10), sticky="ew")
        self.employee_info_frame.grid_columnconfigure(1, weight=1)
        self.employee_info_frame.grid_columnconfigure(3, weight=1)

        # Progress Bars Section - TOP PRIORITY
        self.create_progress_bars_section()

        # Employee info labels - arranged in 2 columns (below progress bars)
        ttk.Label(self.employee_info_frame, text="Employee ID:").grid(row=2, column=0, sticky="w", padx=(0, 5))
        self.emp_id_label = ttk.Label(self.employee_info_frame, text="", foreground="blue")
        self.emp_id_label.grid(row=2, column=1, sticky="w", padx=(0, 20))

        ttk.Label(self.employee_info_frame, text="Name:").grid(row=2, column=2, sticky="w", padx=(0, 5))
        self.emp_name_label = ttk.Label(self.employee_info_frame, text="", foreground="blue")
        self.emp_name_label.grid(row=2, column=3, sticky="w")

        ttk.Label(self.employee_info_frame, text="Hire Date:").grid(row=3, column=0, sticky="w", padx=(0, 5),
                                                                    pady=(5, 0))
        self.emp_hire_label = ttk.Label(self.employee_info_frame, text="", foreground="blue")
        self.emp_hire_label.grid(row=3, column=1, sticky="w", padx=(0, 20), pady=(5, 0))

        ttk.Label(self.employee_info_frame, text="Status:").grid(row=3, column=2, sticky="w", padx=(0, 5), pady=(5, 0))
        self.emp_status_label = ttk.Label(self.employee_info_frame, text="", foreground="blue")
        self.emp_status_label.grid(row=3, column=3, sticky="w", pady=(5, 0))

        ttk.Label(self.employee_info_frame, text="Employee Type:").grid(row=4, column=0, sticky="w", padx=(0, 5),
                                                                        pady=(5, 0))
        self.emp_type_label = ttk.Label(self.employee_info_frame, text="", foreground="blue")
        self.emp_type_label.grid(row=4, column=1, sticky="w", padx=(0, 20), pady=(5, 0))

        ttk.Label(self.employee_info_frame, text="Reports To:").grid(row=4, column=2, sticky="w", padx=(0, 5),
                                                                     pady=(5, 0))
        self.emp_reports_label = ttk.Label(self.employee_info_frame, text="", foreground="blue")
        self.emp_reports_label.grid(row=4, column=3, sticky="w", pady=(5, 0))

        # Shift info (LEFT)
        self.create_shift_info_section()

        # Attendance (LEFT)
        self.create_attendance_section()

        # --- Supervisor Evaluation (LEFT) ---
        supervisor_frame = ttk.LabelFrame(left_col, text="🔧 Supervisor Evaluation Tools", padding="15")
        supervisor_frame.grid(row=3, column=0, columnspan=2, padx=0, pady=(10, 10), sticky="ew")
        supervisor_frame.grid_columnconfigure(0, weight=1)
        supervisor_frame.grid_columnconfigure(1, weight=1)

        # Description (triple-quoted to avoid unterminated-string errors)
        description_text = """Use this section to record competency evaluations and assign maintenance tasks to employees.
    Complete all fields when documenting successful competency demonstrations or skill assessments."""
        ttk.Label(
            supervisor_frame, text=description_text,
            font=('TkDefaultFont', 9), foreground='#555555', wraplength=700, justify='left'
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))

        # Two-column layout inside supervisor_frame
        form_left = ttk.Frame(supervisor_frame)
        form_left.grid(row=1, column=0, sticky="nsew", padx=(0, 15))
        form_right = ttk.Frame(supervisor_frame)
        form_right.grid(row=1, column=1, sticky="nsew", padx=(15, 0))
        supervisor_frame.grid_columnconfigure(0, weight=1)
        supervisor_frame.grid_columnconfigure(1, weight=1)

        # LEFT in supervisor: Level + Status + Date
        level_frame = ttk.Frame(form_left)
        level_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        level_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(level_frame, text="Maintenance Level",
                  font=('TkDefaultFont', 10, 'bold'), foreground='#2E7D32').grid(row=0, column=0, sticky="w")

        ttk.Label(level_frame,
                  text="Select the maintenance level being evaluated (Level 1 = Basic, Level 3 = Advanced)",
                  font=('TkDefaultFont', 8), foreground='#666666', wraplength=300
                  ).grid(row=1, column=0, sticky="w", pady=(2, 8))

        level_controls_frame = ttk.Frame(level_frame)
        level_controls_frame.grid(row=2, column=0, sticky="ew")
        level_controls_frame.grid_columnconfigure(0, weight=1)

        self.level_var = tk.StringVar()
        self.level_combo = ttk.Combobox(
            level_controls_frame, textvariable=self.level_var,
            values=["Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"],
            state="readonly", width=20
        )
        self.level_combo.grid(row=0, column=0, sticky="w")
        self.level_combo.set("Level 1")

        ttk.Button(level_controls_frame, text="Assign All Tasks For This Level",
                   command=self.assign_all_level_tasks).grid(row=0, column=1, padx=(15, 0), sticky="w")

        status_frame = ttk.Frame(form_left)
        status_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        status_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(status_frame, text="Competency Status",
                  font=('TkDefaultFont', 10, 'bold'), foreground='#2E7D32').grid(row=0, column=0, sticky="w")

        ttk.Label(status_frame,
                  text="• Active = Currently valid certification\n• Expired = Needs recertification\n• Needs Renewal = Approaching expiration",
                  font=('TkDefaultFont', 8), foreground='#666666', justify='left'
                  ).grid(row=1, column=0, sticky="w", pady=(2, 8))

        self.status_var = tk.StringVar()
        self.status_combo = ttk.Combobox(
            status_frame, textvariable=self.status_var,
            values=["Active", "Expired", "Needs Renewal"],
            state="readonly", width=20
        )
        self.status_combo.grid(row=2, column=0, sticky="w")
        self.status_combo.set("Active")

        date_frame = ttk.Frame(form_left)
        date_frame.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        date_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(date_frame, text="Date Achieved",
                  font=('TkDefaultFont', 10, 'bold'), foreground='#2E7D32').grid(row=0, column=0, sticky="w")

        ttk.Label(date_frame,
                  text="Enter the date when the employee successfully demonstrated the competency (YYYY-MM-DD format)",
                  font=('TkDefaultFont', 8), foreground='#666666', wraplength=300
                  ).grid(row=1, column=0, sticky="w", pady=(2, 8))

        self.date_entry = ttk.Entry(date_frame, width=25)
        self.date_entry.grid(row=2, column=0, sticky="w")

        # RIGHT in supervisor: Assessor + Notes + Tips
        assessor_frame = ttk.Frame(form_right)
        assessor_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        assessor_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(assessor_frame, text="Assessed By (Supervisor)",
                  font=('TkDefaultFont', 10, 'bold'), foreground='#1976D2').grid(row=0, column=0, sticky="w")

        ttk.Label(assessor_frame,
                  text="Select the supervisor or qualified person who conducted the evaluation",
                  font=('TkDefaultFont', 8), foreground='#666666', wraplength=300
                  ).grid(row=1, column=0, sticky="w", pady=(2, 8))

        self.assessor_var = tk.StringVar()
        self.assessor_combo = ttk.Combobox(assessor_frame, textvariable=self.assessor_var, state="readonly", width=35)
        self.assessor_combo.grid(row=2, column=0, sticky="ew")
        self.load_assessors()

        notes_frame = ttk.Frame(form_right)
        notes_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 15))
        notes_frame.grid_columnconfigure(0, weight=1)
        notes_frame.grid_rowconfigure(2, weight=1)

        ttk.Label(notes_frame, text="Evaluation Notes",
                  font=('TkDefaultFont', 10, 'bold'), foreground='#1976D2').grid(row=0, column=0, sticky="w")

        ttk.Label(notes_frame,
                  text="Record specific details about the evaluation, any areas for improvement, or special circumstances",
                  font=('TkDefaultFont', 8), foreground='#666666', wraplength=300
                  ).grid(row=1, column=0, sticky="w", pady=(2, 8))

        self.notes_text = tk.Text(notes_frame, height=4, width=40, wrap='word', font=('TkDefaultFont', 9))
        self.notes_text.grid(row=2, column=0, sticky="nsew")

        notes_scrollbar = ttk.Scrollbar(notes_frame, orient='vertical', command=self.notes_text.yview)
        self.notes_text.configure(yscrollcommand=notes_scrollbar.set)
        notes_scrollbar.grid(row=2, column=1, sticky="ns")

        tips_frame = ttk.Frame(form_right)
        tips_frame.grid(row=2, column=0, sticky="ew", pady=(15, 0))
        ttk.Label(tips_frame, text="💡 Quick Tips",
                  font=('TkDefaultFont', 9, 'bold'), foreground='#F57F17').grid(row=0, column=0, sticky="w")
        ttk.Label(tips_frame,
                  text=("• Use 'Assign All Tasks' to quickly set up all competencies for a level\n"
                        "• Double-click any record in the table below to edit it\n"
                        "• Use filters to find specific competencies or employees\n"
                        "• Export filtered results for reporting purposes"),
                  font=('TkDefaultFont', 8), foreground='#666666', justify='left', wraplength=300
                  ).grid(row=1, column=0, sticky="w", pady=(5, 0))

        # Action Buttons (LEFT, under supervisor)
        self.create_action_buttons()

        # ---------------- RIGHT COLUMN CONTAINER ----------------
        right_col = ttk.Frame(self.scrollable_frame)
        right_col.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_col.grid_columnconfigure(0, weight=1)
        # Let the table row expand
        right_col.grid_rowconfigure(1, weight=1)

        # Filters (RIGHT, top)
        filter_main_frame = ttk.LabelFrame(right_col, text="Filtering & Search Options", padding="10")
        filter_main_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        for i in range(3):
            filter_main_frame.grid_columnconfigure(i, weight=1)

        filter_configs = [
            # Row 0
            ("Completion Status", "completed_filter_var", "completed_filter_combo",
             ["All", "Completed", "Not Completed"], "All"),
            ("Level Filter", "level_filter_var", "level_filter_combo",
             ["All", "Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"], "All"),
            ("Competency Type", "type_filter_var", "type_filter_combo",
             ["All", "mechanical", "electrical", "tools", "operational", "safety", "training", "communication",
              "leadership"], "All"),
            # Row 1
            ("Status Filter", "status_filter_var", "status_filter_combo",
             ["All", "Active", "Expired", "Needs Renewal"], "All"),
            ("Tier Filter", "tier_column_var", "tier_column_entry", None, ""),
            ("Proficiency Filter", "proficiency_column_var", "proficiency_column_entry", None, ""),
            # Row 2
            ("Search Task", "task_search_var", "task_search_entry", None, ""),
            ("Date Filter", "date_column_var", "date_column_entry", None, ""),
            ("Notes Filter", "notes_column_var", "notes_column_entry", None, "")
        ]

        for idx, (label, var_name, widget_name, values, default) in enumerate(filter_configs):
            row = idx // 3
            col = idx % 3
            one = ttk.Frame(filter_main_frame)
            one.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            one.grid_columnconfigure(0, weight=1)
            ttk.Label(one, text=label, font=('TkDefaultFont', 8, 'bold')).grid(row=0, column=0, sticky="w", pady=(0, 2))
            var = tk.StringVar()
            setattr(self, var_name, var)
            var.set(default)
            if values:  # dropdown
                widget = ttk.Combobox(one, textvariable=var, values=values, state="readonly", width=15,
                                      font=('TkDefaultFont', 8))
                widget.bind("<<ComboboxSelected>>", self.apply_filters)
            else:  # entry
                widget = ttk.Entry(one, textvariable=var, width=15, font=('TkDefaultFont', 8))
                var.trace("w", self.apply_filters)
            widget.grid(row=1, column=0, sticky="ew")
            setattr(self, widget_name, widget)

        # column-specific filters used by passes_filters()
        self.column_filters = {
            'tier': self.tier_column_var,
            'proficiency': self.proficiency_column_var,
            'date': self.date_column_var,
            'notes': self.notes_column_var
        }

        # Table (RIGHT, middle)
        ttk.Label(right_col, text="Employee Competency Records",
                  font=('TkDefaultFont', 10, 'bold')).grid(row=1, column=0, sticky="w", pady=(0, 4))

        tree_frame = ttk.Frame(right_col)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columns = ["type", "task", "tier", "proficiency", "level", "status", "date", "assessor", "notes", "completed"]
        self.eval_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=18)
        for col in columns:
            self.eval_tree.heading(col, text=col.title(), command=lambda c=col: self.sort_treeview(c, False))
            if col == "notes":
                self.eval_tree.column(col, width=180, minwidth=120)
            else:
                self.eval_tree.column(col, width=100, minwidth=80)

        tree_v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.eval_tree.yview)
        tree_h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.eval_tree.xview)
        self.eval_tree.configure(yscrollcommand=tree_v_scrollbar.set, xscrollcommand=tree_h_scrollbar.set)

        self.eval_tree.grid(row=0, column=0, sticky="nsew")
        tree_v_scrollbar.grid(row=0, column=1, sticky="ns")
        tree_h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.eval_tree.bind('<Double-1>', self.on_treeview_double_click)

        # Breakdown (RIGHT, bottom)
        self.breakdown_var = tk.StringVar()
        ttk.Label(right_col, textvariable=self.breakdown_var,
                  font=('TkDefaultFont', 9, 'bold'), foreground='blue', wraplength=400
                  ).grid(row=2, column=0, sticky='ew', pady=(6, 0))

        # First population
        self.refresh_eval_list()

    def apply_stepup_theme(self):
        """Dark theme with soft-grey form fields; works with ttk (no bg config on ttk widgets)."""
        import tkinter as tk
        from tkinter import ttk

        PALETTE = {
            'bg': '#0f172a',  # window / tab background
            'panel': '#0b1223',
            'panel2': '#0c1327',
            'text': '#d1d5db',  # soft light grey (not white)
            'muted': '#9ca3af',
            'accent': '#60a5fa',
            'accent2': '#a5b4fc',
            'line': '#1f2a44',
            'hover': '#1e293b',
            'entry': '#1e293b',  # <-- soft grey for inputs
            'trough': '#1f2937',
        }
        self._PALETTE = PALETTE  # (optional) so you can reuse it elsewhere

        style = ttk.Style()
        try:
            style.theme_use('clam')  # must be before most style.configure calls
        except tk.TclError:
            pass

        # ----- Base containers -----
        # Give THIS tab/frame a dark background via a custom style (ttk requires styles, not bg=)
        style.configure('StepUpEval.TFrame', background=PALETTE['bg'])
        self.configure(style='StepUpEval.TFrame')

        # Default backgrounds for nested frames/labels/labelframes
        style.configure('.', background=PALETTE['panel'], foreground=PALETTE['text'])
        style.configure('TFrame', background=PALETTE['panel'])
        style.configure('TLabelframe', background=PALETTE['panel'], bordercolor=PALETTE['line'])
        style.configure('TLabelframe.Label', background=PALETTE['panel'], foreground=PALETTE['accent2'])
        style.configure('TLabel', background=PALETTE['panel'], foreground=PALETTE['text'])
        style.configure('Separator', background=PALETTE['line'])

        # Notebook (since we cannot set bg directly on ttk.Notebook)
        style.configure('TNotebook', background=PALETTE['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=PALETTE['panel2'], foreground=PALETTE['muted'], padding=[10, 5])
        style.map('TNotebook.Tab',
                  background=[('selected', PALETTE['panel'])],
                  foreground=[('selected', PALETTE['accent2'])])

        # ----- Inputs: Entry / Combobox (soft grey fields) -----
        base_field_opts = dict(
            fieldbackground=PALETTE['entry'],
            background=PALETTE['entry'],
            foreground=PALETTE['text'],
            bordercolor=PALETTE['line'],
            lightcolor=PALETTE['line'],
            darkcolor=PALETTE['line']
        )
        style.configure('TEntry', **base_field_opts)
        style.map('TEntry',
                  fieldbackground=[('disabled', '#18212f')],
                  foreground=[('disabled', PALETTE['muted'])])

        style.configure('TCombobox', **base_field_opts, arrowcolor=PALETTE['accent'])
        # Ensure readonly Combobox uses the same soft grey in most themes
        style.map('TCombobox',
                  fieldbackground=[('readonly', PALETTE['entry']), ('disabled', '#18212f')],
                  foreground=[('readonly', PALETTE['text']), ('disabled', PALETTE['muted'])])

        # Classic tk widgets (used by your inline edit popup and Text widgets)
        top = self.winfo_toplevel()
        # tk.Entry (inline editor on double-click)
        top.option_add('*Entry.background', PALETTE['entry'])
        top.option_add('*Entry.foreground', PALETTE['text'])
        top.option_add('*Entry.insertBackground', PALETTE['accent'])
        # tk.Text (notes, schedule, etc.)
        top.option_add('*Text.background', PALETTE['entry'])
        top.option_add('*Text.foreground', PALETTE['text'])
        top.option_add('*Text.insertBackground', PALETTE['accent'])
        # tk.Listbox (Combobox dropdown on some platforms)
        top.option_add('*Listbox.background', PALETTE['entry'])
        top.option_add('*Listbox.foreground', PALETTE['text'])

        # ----- Treeview (table) soft grey bg -----

    def create_shift_info_section(self):
        """Create a dedicated shift information section (same layout as before, themed)."""
        import tkinter as tk
        from tkinter import ttk

        PALETTE = getattr(self, "_PALETTE", {
            'entry': '#1e293b', 'text': '#d1d5db', 'accent': '#60a5fa'
        })

        # Shift information frame
        shift_frame = ttk.LabelFrame(self.employee_info_frame, text="Current Shift Assignment", padding="10")
        shift_frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(15, 10))
        shift_frame.grid_columnconfigure(1, weight=1)
        shift_frame.grid_columnconfigure(3, weight=1)

        # Shift Name and Description
        ttk.Label(shift_frame, text="Shift:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.shift_name_label = ttk.Label(shift_frame, text="No shift assigned",
                                          font=('TkDefaultFont', 9, 'bold'), foreground="blue")
        self.shift_name_label.grid(row=0, column=1, sticky="w", padx=(0, 20))

        ttk.Label(shift_frame, text="Pattern:").grid(row=0, column=2, sticky="w", padx=(0, 5))
        self.shift_pattern_label = ttk.Label(shift_frame, text="", foreground="blue")
        self.shift_pattern_label.grid(row=0, column=3, sticky="w")

        # Assignment dates
        ttk.Label(shift_frame, text="Start Date:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=(5, 0))
        self.shift_start_label = ttk.Label(shift_frame, text="", foreground="blue")
        self.shift_start_label.grid(row=1, column=1, sticky="w", padx=(0, 20), pady=(5, 0))

        ttk.Label(shift_frame, text="Status:").grid(row=1, column=2, sticky="w", padx=(0, 5), pady=(5, 0))
        self.shift_status_label = ttk.Label(shift_frame, text="", foreground="blue")
        self.shift_status_label.grid(row=1, column=3, sticky="w", pady=(5, 0))

        # Schedule details
        ttk.Label(shift_frame, text="Schedule:").grid(row=2, column=0, sticky="nw", padx=(0, 5), pady=(10, 0))

        # Frame for schedule text with scrollbar
        schedule_text_frame = ttk.Frame(shift_frame)
        schedule_text_frame.grid(row=2, column=1, columnspan=3, sticky="ew", pady=(10, 0))
        schedule_text_frame.grid_columnconfigure(0, weight=1)

        self.schedule_text_widget = tk.Text(schedule_text_frame, height=4, width=50,
                                            wrap='word', state='disabled',
                                            font=('TkDefaultFont', 9),
                                            bg=PALETTE['entry'], fg=PALETTE['text'],
                                            insertbackground=PALETTE['accent'],
                                            relief='flat')
        schedule_scrollbar = ttk.Scrollbar(schedule_text_frame, orient='vertical',
                                           command=self.schedule_text_widget.yview)
        self.schedule_text_widget.configure(yscrollcommand=schedule_scrollbar.set)

        self.schedule_text_widget.grid(row=0, column=0, sticky="ew")
        schedule_scrollbar.grid(row=0, column=1, sticky="ns")

    def apply_stepup_theme(self):
        """Dark theme with soft-grey form fields; works with ttk (no bg config on ttk widgets)."""
        import tkinter as tk
        from tkinter import ttk

        PALETTE = {
            'bg': '#0f172a',  # window / tab background
            'panel': '#0b1223',
            'panel2': '#0c1327',
            'text': '#d1d5db',  # soft light grey (not white)
            'muted': '#9ca3af',
            'accent': '#60a5fa',
            'accent2': '#a5b4fc',
            'line': '#1f2a44',
            'hover': '#1e293b',
            'entry': '#1e293b',  # <-- soft grey for inputs
            'trough': '#1f2937',
        }
        self._PALETTE = PALETTE  # (optional) so you can reuse it elsewhere

        style = ttk.Style()
        try:
            style.theme_use('clam')  # must be before most style.configure calls
        except tk.TclError:
            pass

        # ----- Base containers -----
        # Give THIS tab/frame a dark background via a custom style (ttk requires styles, not bg=)
        style.configure('StepUpEval.TFrame', background=PALETTE['bg'])
        self.configure(style='StepUpEval.TFrame')

        # Default backgrounds for nested frames/labels/labelframes
        style.configure('.', background=PALETTE['panel'], foreground=PALETTE['text'])
        style.configure('TFrame', background=PALETTE['panel'])
        style.configure('TLabelframe', background=PALETTE['panel'], bordercolor=PALETTE['line'])
        style.configure('TLabelframe.Label', background=PALETTE['panel'], foreground=PALETTE['accent2'])
        style.configure('TLabel', background=PALETTE['panel'], foreground=PALETTE['text'])
        style.configure('Separator', background=PALETTE['line'])

        # Notebook (since we cannot set bg directly on ttk.Notebook)
        style.configure('TNotebook', background=PALETTE['bg'], borderwidth=0)
        style.configure('TNotebook.Tab', background=PALETTE['panel2'], foreground=PALETTE['muted'], padding=[10, 5])
        style.map('TNotebook.Tab',
                  background=[('selected', PALETTE['panel'])],
                  foreground=[('selected', PALETTE['accent2'])])

        # ----- Inputs: Entry / Combobox (soft grey fields) -----
        base_field_opts = dict(
            fieldbackground=PALETTE['entry'],
            background=PALETTE['entry'],
            foreground=PALETTE['text'],
            bordercolor=PALETTE['line'],
            lightcolor=PALETTE['line'],
            darkcolor=PALETTE['line']
        )
        style.configure('TEntry', **base_field_opts)
        style.map('TEntry',
                  fieldbackground=[('disabled', '#18212f')],
                  foreground=[('disabled', PALETTE['muted'])])

        style.configure('TCombobox', **base_field_opts, arrowcolor=PALETTE['accent'])
        # Ensure readonly Combobox uses the same soft grey in most themes
        style.map('TCombobox',
                  fieldbackground=[('readonly', PALETTE['entry']), ('disabled', '#18212f')],
                  foreground=[('readonly', PALETTE['text']), ('disabled', PALETTE['muted'])])

        # Classic tk widgets (used by your inline edit popup and Text widgets)
        top = self.winfo_toplevel()
        # tk.Entry (inline editor on double-click)
        top.option_add('*Entry.background', PALETTE['entry'])
        top.option_add('*Entry.foreground', PALETTE['text'])
        top.option_add('*Entry.insertBackground', PALETTE['accent'])
        # tk.Text (notes, schedule, etc.)
        top.option_add('*Text.background', PALETTE['entry'])
        top.option_add('*Text.foreground', PALETTE['text'])
        top.option_add('*Text.insertBackground', PALETTE['accent'])
        # tk.Listbox (Combobox dropdown on some platforms)
        top.option_add('*Listbox.background', PALETTE['entry'])
        top.option_add('*Listbox.foreground', PALETTE['text'])

        # ----- Treeview (table) soft grey bg -----
        style.configure('Treeview',
                        background=PALETTE['entry'],
                        fieldbackground=PALETTE['entry'],
                        foreground=PALETTE['text'],
                        bordercolor=PALETTE['line'],
                        rowheight=24)
        style.configure('Treeview.Heading',
                        background=PALETTE['panel2'],
                        foreground=PALETTE['accent2'],
                        bordercolor=PALETTE['line'])
        style.map('Treeview',
                  background=[('selected', PALETTE['hover'])],
                  foreground=[('selected', PALETTE['text'])])

        # ----- Progressbars -----
        style.configure('Horizontal.TProgressbar',
                        background=PALETTE['accent'],
                        troughcolor=PALETTE['trough'],
                        bordercolor=PALETTE['line'])

        # Keep your per-level bar colors but match the dark trough
        for lvl in ["Level1", "Level2", "Level3", "MaintenanceTech"]:
            style.configure(f'{lvl}.Horizontal.TProgressbar', troughcolor=PALETTE['trough'])

        # ----- Scrollbars (optional) -----
        style.configure('Vertical.TScrollbar', background=PALETTE['trough'], troughcolor=PALETTE['trough'])
        style.configure('Horizontal.TScrollbar', background=PALETTE['trough'], troughcolor=PALETTE['trough'])

        # ----- Canvas bg (tk widget — bg can be set safely AFTER you create it) -----
        # If you want the canvas itself to be dark, set in __init__ right after creating it:
        # self.canvas.configure(bg=PALETTE['bg'])

        # ----- Ensure any already-created Text widgets get recolored (if theme called later) -----
        def _recolor_texts(root):
            for w in root.winfo_children():
                try:
                    if isinstance(w, tk.Text):
                        w.configure(bg=PALETTE['entry'], fg=PALETTE['text'], insertbackground=PALETTE['accent'])
                except Exception:
                    pass
                _recolor_texts(w)

        self.after(0, lambda: _recolor_texts(self))

    def update_shift_info(self, employee_id=None):
        """Update the shift information section"""
        if not employee_id:
            # Clear shift info
            self.shift_name_label.config(text="No shift assigned")
            self.shift_pattern_label.config(text="")
            self.shift_start_label.config(text="")
            self.shift_status_label.config(text="")
            self.clear_schedule_text()
            return

        try:
            from db_main import EmployeeSchedule, Shift, ShiftDay
            from datetime import date

            # Get current active schedule
            current_schedule = self.session.query(EmployeeSchedule).filter_by(
                employee_id=employee_id,
                is_active=True
            ).filter(
                (EmployeeSchedule.effective_end_date.is_(None)) |
                (EmployeeSchedule.effective_end_date >= date.today())
            ).first()

            if not current_schedule:
                self.shift_name_label.config(text="No active shift")
                self.shift_pattern_label.config(text="")
                self.shift_start_label.config(text="")
                self.shift_status_label.config(text="Unassigned", foreground="red")
                self.clear_schedule_text()
                return

            shift = current_schedule.shift
            if not shift:
                self.shift_name_label.config(text="Schedule found but no shift details")
                self.shift_pattern_label.config(text="")
                self.shift_start_label.config(text="")
                self.shift_status_label.config(text="Error", foreground="red")
                self.clear_schedule_text()
                return

            # Update shift information
            shift_display = shift.shift_name
            if shift.description:
                shift_display += f" - {shift.description}"
            self.shift_name_label.config(text=shift_display)

            self.shift_pattern_label.config(text=shift.shift_pattern.title())
            self.shift_start_label.config(text=current_schedule.effective_start_date.strftime('%Y-%m-%d'))

            # Determine status
            if current_schedule.effective_end_date:
                if current_schedule.effective_end_date < date.today():
                    status_text = "Expired"
                    status_color = "red"
                else:
                    status_text = f"Active (until {current_schedule.effective_end_date})"
                    status_color = "green"
            else:
                status_text = "Active (ongoing)"
                status_color = "green"

            self.shift_status_label.config(text=status_text, foreground=status_color)

            # Update schedule details
            self.update_schedule_text(shift)

        except Exception as e:
            print(f"Error updating shift info: {e}")
            self.shift_name_label.config(text="Error loading shift")
            self.shift_pattern_label.config(text="")
            self.shift_start_label.config(text="")
            self.shift_status_label.config(text="Error", foreground="red")
            self.clear_schedule_text()

    def update_schedule_text(self, shift):
        """Update the schedule text widget with detailed shift information"""
        if not shift or not shift.shift_days:
            self.clear_schedule_text()
            self.set_schedule_text("No schedule details available")
            return

        # Build detailed schedule text
        schedule_lines = []

        if shift.shift_pattern == 'biweekly':
            # Group by week
            week1_days = [sd for sd in shift.shift_days if getattr(sd, 'week_number', 1) == 1]
            week2_days = [sd for sd in shift.shift_days if getattr(sd, 'week_number', 1) == 2]

            if week1_days:
                schedule_lines.append("Week 1:")
                for shift_day in sorted(week1_days, key=lambda x: x.day_of_week):
                    day_name = self.get_day_name(shift_day.day_of_week)
                    time_str = f"{shift_day.scheduled_start_time.strftime('%H:%M')} - {shift_day.scheduled_end_time.strftime('%H:%M')}"
                    duration = self.calculate_shift_duration(shift_day.scheduled_start_time,
                                                             shift_day.scheduled_end_time)
                    schedule_lines.append(f"  {day_name}: {time_str} ({duration} hours)")

            if week2_days:
                schedule_lines.append("\nWeek 2:")
                for shift_day in sorted(week2_days, key=lambda x: x.day_of_week):
                    day_name = self.get_day_name(shift_day.day_of_week)
                    time_str = f"{shift_day.scheduled_start_time.strftime('%H:%M')} - {shift_day.scheduled_end_time.strftime('%H:%M')}"
                    duration = self.calculate_shift_duration(shift_day.scheduled_start_time,
                                                             shift_day.scheduled_end_time)
                    schedule_lines.append(f"  {day_name}: {time_str} ({duration} hours)")
        else:
            # Weekly schedule
            total_hours_per_week = 0
            for shift_day in sorted(shift.shift_days, key=lambda x: x.day_of_week):
                day_name = self.get_day_name(shift_day.day_of_week)
                time_str = f"{shift_day.scheduled_start_time.strftime('%H:%M')} - {shift_day.scheduled_end_time.strftime('%H:%M')}"
                duration = self.calculate_shift_duration(shift_day.scheduled_start_time, shift_day.scheduled_end_time)
                total_hours_per_week += duration
                schedule_lines.append(f"{day_name}: {time_str} ({duration} hours)")

            schedule_lines.append(f"\nTotal weekly hours: {total_hours_per_week}")

        self.set_schedule_text("\n".join(schedule_lines))

    def calculate_shift_duration(self, start_time, end_time):
        """Calculate shift duration in hours"""
        from datetime import datetime, timedelta

        # Convert time objects to datetime for calculation
        start_dt = datetime.combine(datetime.today(), start_time)
        end_dt = datetime.combine(datetime.today(), end_time)

        # Handle overnight shifts
        if end_dt <= start_dt:
            end_dt += timedelta(days=1)

        duration = end_dt - start_dt
        return round(duration.total_seconds() / 3600, 1)  # Convert to hours

    def clear_schedule_text(self):
        """Clear the schedule text widget"""
        self.schedule_text_widget.config(state='normal')
        self.schedule_text_widget.delete('1.0', tk.END)
        self.schedule_text_widget.config(state='disabled')

    def set_schedule_text(self, text):
        """Set text in the schedule text widget"""
        self.schedule_text_widget.config(state='normal')
        self.schedule_text_widget.delete('1.0', tk.END)
        self.schedule_text_widget.insert('1.0', text)
        self.schedule_text_widget.config(state='disabled')

    def get_day_name(self, day_of_week):
        """Convert day of week number to name"""
        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        return days[day_of_week] if 0 <= day_of_week <= 6 else "Unknown"

    # Updated display_employee_info method
    def display_employee_info(self, employee_id):
        """Display detailed employee information, update progress bars, and show shift/attendance info"""
        if not employee_id:
            # Clear all employee info labels
            self.emp_id_label.config(text="")
            self.emp_name_label.config(text="")
            self.emp_hire_label.config(text="")
            self.emp_status_label.config(text="")
            self.emp_type_label.config(text="")
            self.emp_reports_label.config(text="")

            # Clear progress bars
            self.update_progress_bars(None)

            # Clear shift info
            self.update_shift_info(None)

            # Clear attendance info
            self.update_attendance_info(None)
            return

        employee = self.session.query(Employee).get(employee_id)
        if not employee:
            return

        # Update employee info labels
        self.emp_id_label.config(text=employee.employee_id or "N/A")
        self.emp_name_label.config(text=f"{employee.name_first or ''} {employee.name_last or ''}".strip() or "N/A")
        self.emp_hire_label.config(text=employee.hire_date or "N/A")
        self.emp_status_label.config(text=employee.status or "N/A")
        self.emp_type_label.config(text=employee.employee_type or "N/A")

        # Handle reports to
        if employee.reports_to:
            reports_to_text = f"{employee.reports_to.employee_id} - {employee.reports_to.name_first} {employee.reports_to.name_last}"
        else:
            reports_to_text = "N/A"
        self.emp_reports_label.config(text=reports_to_text)

        # Update progress bars
        self.update_progress_bars(employee_id)

        # Update shift info
        self.update_shift_info(employee_id)

        # Update attendance info
        self.update_attendance_info(employee_id)

    # Updated create_attendance_section method to adjust for shift info section
    def create_attendance_section(self):
        """Create attendance overview section showing current schedule and recent occurrences"""
        # Attendance section frame - moved down to row 6 to make room for shift info
        attendance_frame = ttk.LabelFrame(self.employee_info_frame, text="Attendance Overview", padding="10")
        attendance_frame.grid(row=6, column=0, columnspan=4, sticky="ew", pady=(15, 0))
        attendance_frame.grid_columnconfigure(1, weight=1)

        # Attendance Summary (last 12 months) - removed current schedule section since we have dedicated shift info
        summary_frame = ttk.Frame(attendance_frame)
        summary_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Label(summary_frame, text="Last 12 Months Summary:",
                  font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Create summary statistics frame
        stats_frame = ttk.Frame(summary_frame)
        stats_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

        # Statistics labels
        stat_labels = [
            ("Total Days Scheduled:", "total_scheduled_label"),
            ("Days Present:", "days_present_label"),
            ("Days Late:", "days_late_label"),
            ("Days Early Out:", "days_early_label"),
            ("Days Absent:", "days_absent_label"),
            ("Attendance Rate:", "attendance_rate_label")
        ]

        for i, (label_text, attr_name) in enumerate(stat_labels):
            row = i // 2
            col = (i % 2) * 2

            ttk.Label(stats_frame, text=label_text).grid(row=row, column=col, sticky="w", padx=(0, 5), pady=2)
            label = ttk.Label(stats_frame, text="0", foreground="blue")
            label.grid(row=row, column=col + 1, sticky="w", padx=(0, 20), pady=2)
            setattr(self, attr_name, label)

        # Recent Issues section
        issues_frame = ttk.Frame(attendance_frame)
        issues_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        issues_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(issues_frame, text="Recent Attendance Issues:",
                  font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Create treeview for recent issues
        issues_columns = ("Date", "Type", "Description", "Status")
        self.issues_tree = ttk.Treeview(issues_frame, columns=issues_columns, show="headings", height=4)

        for col in issues_columns:
            self.issues_tree.heading(col, text=col)
            if col == "Description":
                self.issues_tree.column(col, width=200)
            else:
                self.issues_tree.column(col, width=80)

        # Scrollbar for issues tree
        issues_scrollbar = ttk.Scrollbar(issues_frame, orient="vertical", command=self.issues_tree.yview)
        self.issues_tree.configure(yscrollcommand=issues_scrollbar.set)

        self.issues_tree.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        issues_scrollbar.grid(row=1, column=1, sticky="ns")

    def create_progress_bars_section(self):
        """Create progress bars for each maintenance level"""
        # Progress bars container frame
        progress_frame = ttk.Frame(self.employee_info_frame)
        progress_frame.grid(row=0, column=0, columnspan=4, sticky="ew", pady=(0, 15))
        progress_frame.grid_columnconfigure(0, weight=1)
        progress_frame.grid_columnconfigure(1, weight=1)
        progress_frame.grid_columnconfigure(2, weight=1)
        progress_frame.grid_columnconfigure(3, weight=1)

        # Title for progress section
        ttk.Label(progress_frame, text="Competency Progress by Level",
                  font=('TkDefaultFont', 10, 'bold')).grid(row=0, column=0, columnspan=4, pady=(0, 10))

        # Define levels and colors
        self.levels = ["Level 1", "Level 2", "Level 3", "Maintenance Tech"]
        self.level_colors = {
            "Level 1": "#4CAF50",  # Green
            "Level 2": "#2196F3",  # Blue
            "Level 3": "#FF9800",  # Orange
            "Maintenance Tech": "#9C27B0"  # Purple
        }

        # Create progress widgets for each level
        self.progress_widgets = {}

        for idx, level in enumerate(self.levels):
            # Level frame
            level_frame = ttk.Frame(progress_frame)
            level_frame.grid(row=1, column=idx, padx=5, pady=5, sticky="ew")
            level_frame.grid_columnconfigure(0, weight=1)

            # Level label
            level_label = ttk.Label(level_frame, text=level,
                                    font=('TkDefaultFont', 9, 'bold'))
            level_label.grid(row=0, column=0, pady=(0, 5))

            # Progress bar
            progress_bar = ttk.Progressbar(level_frame, mode='determinate',
                                           length=120, style=f"{level.replace(' ', '')}.Horizontal.TProgressbar")
            progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 2))

            # Progress text (e.g., "5/10")
            progress_text = ttk.Label(level_frame, text="0/0",
                                      font=('TkDefaultFont', 8))
            progress_text.grid(row=2, column=0)

            # Percentage text
            percentage_text = ttk.Label(level_frame, text="0%",
                                        font=('TkDefaultFont', 8, 'bold'),
                                        foreground=self.level_colors[level])
            percentage_text.grid(row=3, column=0)

            # Store references
            self.progress_widgets[level] = {
                'bar': progress_bar,
                'text': progress_text,
                'percentage': percentage_text
            }

        # Configure custom styles for progress bars
        self.configure_progress_bar_styles()

    def configure_progress_bar_styles(self):
        """Configure custom styles for progress bars with different colors"""
        style = ttk.Style()

        for level, color in self.level_colors.items():
            style_name = f"{level.replace(' ', '')}.Horizontal.TProgressbar"
            style.configure(style_name, background=color, troughcolor='#E0E0E0')

    def create_attendance_section(self):
        """Create attendance overview section showing current schedule and recent occurrences"""
        # Attendance section frame
        attendance_frame = ttk.LabelFrame(self.employee_info_frame, text="Attendance Overview", padding="10")
        attendance_frame.grid(row=5, column=0, columnspan=4, sticky="ew", pady=(15, 0))
        attendance_frame.grid_columnconfigure(1, weight=1)

        # Current Schedule section
        schedule_frame = ttk.Frame(attendance_frame)
        schedule_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        schedule_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(schedule_frame, text="Current Schedule:",
                  font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=0, sticky="w")

        self.schedule_text = ttk.Label(schedule_frame, text="No active schedule",
                                       foreground="gray", wraplength=400)
        self.schedule_text.grid(row=0, column=1, sticky="w", padx=(10, 0))

        # Attendance Summary (last 12 months)
        summary_frame = ttk.Frame(attendance_frame)
        summary_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 10))

        ttk.Label(summary_frame, text="Last 12 Months Summary:",
                  font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Create summary statistics frame
        stats_frame = ttk.Frame(summary_frame)
        stats_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

        # Statistics labels
        stat_labels = [
            ("Total Days Scheduled:", "total_scheduled_label"),
            ("Days Present:", "days_present_label"),
            ("Days Late:", "days_late_label"),
            ("Days Early Out:", "days_early_label"),
            ("Days Absent:", "days_absent_label"),
            ("Attendance Rate:", "attendance_rate_label")
        ]

        for i, (label_text, attr_name) in enumerate(stat_labels):
            row = i // 2
            col = (i % 2) * 2

            ttk.Label(stats_frame, text=label_text).grid(row=row, column=col, sticky="w", padx=(0, 5), pady=2)
            label = ttk.Label(stats_frame, text="0", foreground="blue")
            label.grid(row=row, column=col + 1, sticky="w", padx=(0, 20), pady=2)
            setattr(self, attr_name, label)

        # Recent Issues section
        issues_frame = ttk.Frame(attendance_frame)
        issues_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        issues_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(issues_frame, text="Recent Attendance Issues:",
                  font=('TkDefaultFont', 9, 'bold')).grid(row=0, column=0, sticky="w", pady=(0, 5))

        # Create treeview for recent issues
        issues_columns = ("Date", "Type", "Description", "Status")
        self.issues_tree = ttk.Treeview(issues_frame, columns=issues_columns, show="headings", height=4)

        for col in issues_columns:
            self.issues_tree.heading(col, text=col)
            if col == "Description":
                self.issues_tree.column(col, width=200)
            else:
                self.issues_tree.column(col, width=80)

        # Scrollbar for issues tree
        issues_scrollbar = ttk.Scrollbar(issues_frame, orient="vertical", command=self.issues_tree.yview)
        self.issues_tree.configure(yscrollcommand=issues_scrollbar.set)

        self.issues_tree.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        issues_scrollbar.grid(row=1, column=1, sticky="ns")

    def update_progress_bars(self, employee_id=None):
        """Update progress bars based on employee's competency completion"""
        if not employee_id:
            # Clear all progress bars
            for level in self.levels:
                widgets = self.progress_widgets[level]
                widgets['bar']['value'] = 0
                widgets['text'].config(text="0/0")
                widgets['percentage'].config(text="0%")
            return

        # Get competency data for this employee
        level_data = self.get_level_completion_data(employee_id)

        for level in self.levels:
            widgets = self.progress_widgets[level]

            if level in level_data:
                total, completed = level_data[level]
                percentage = int((completed / total * 100)) if total > 0 else 0

                # Update progress bar
                widgets['bar']['value'] = percentage
                widgets['text'].config(text=f"{completed}/{total}")
                widgets['percentage'].config(text=f"{percentage}%")

                # Change color based on completion
                if percentage == 100:
                    widgets['percentage'].config(foreground="green")
                elif percentage >= 75:
                    widgets['percentage'].config(foreground="orange")
                elif percentage >= 50:
                    widgets['percentage'].config(foreground="blue")
                else:
                    widgets['percentage'].config(foreground="red")
            else:
                # No data for this level
                widgets['bar']['value'] = 0
                widgets['text'].config(text="0/0")
                widgets['percentage'].config(text="0%")
                widgets['percentage'].config(foreground="gray")

    def update_attendance_info(self, employee_id=None):
        """Update attendance information for the selected employee"""
        if not employee_id:
            # Clear attendance info
            self.schedule_text.config(text="No active schedule")
            self.clear_attendance_stats()
            self.clear_attendance_issues()
            return

        # Update current schedule
        self.update_current_schedule(employee_id)

        # Update attendance statistics
        self.update_attendance_stats(employee_id)

        # Update recent issues
        self.update_recent_issues(employee_id)

    def update_current_schedule(self, employee_id):
        """Update the current schedule display"""
        try:
            from db_main import EmployeeSchedule, Shift, ShiftDay
            from datetime import date

            # Get current active schedule
            current_schedule = self.session.query(EmployeeSchedule).filter_by(
                employee_id=employee_id,
                is_active=True
            ).filter(
                (EmployeeSchedule.effective_end_date.is_(None)) |
                (EmployeeSchedule.effective_end_date >= date.today())
            ).first()

            if not current_schedule:
                self.schedule_text.config(text="No active schedule assigned")
                return

            shift = current_schedule.shift
            if not shift:
                self.schedule_text.config(text="Schedule found but no shift details")
                return

            # Format schedule display
            if shift.shift_pattern == "biweekly":
                week1_days = []
                week2_days = []

                for shift_day in sorted(shift.shift_days, key=lambda x: (x.week_number, x.day_of_week)):
                    day_name = self.get_day_name(shift_day.day_of_week)
                    time_str = f"{shift_day.scheduled_start_time.strftime('%H:%M')}-{shift_day.scheduled_end_time.strftime('%H:%M')}"

                    if getattr(shift_day, 'week_number', 1) == 1:
                        week1_days.append(f"{day_name} {time_str}")
                    else:
                        week2_days.append(f"{day_name} {time_str}")

                schedule_text = f"Bi-weekly: {shift.shift_name}\n"
                schedule_text += f"Week 1: {', '.join(week1_days) if week1_days else 'None'}\n"
                schedule_text += f"Week 2: {', '.join(week2_days) if week2_days else 'None'}"
            else:
                # Weekly schedule
                schedule_days = []
                for shift_day in sorted(shift.shift_days, key=lambda x: x.day_of_week):
                    day_name = self.get_day_name(shift_day.day_of_week)
                    time_str = f"{shift_day.scheduled_start_time.strftime('%H:%M')}-{shift_day.scheduled_end_time.strftime('%H:%M')}"
                    schedule_days.append(f"{day_name} {time_str}")

                schedule_text = f"Weekly: {shift.shift_name}\n{', '.join(schedule_days)}"

            self.schedule_text.config(text=schedule_text)

        except Exception as e:
            self.schedule_text.config(text=f"Error loading schedule: {str(e)}")

    def update_attendance_stats(self, employee_id):
        """Update attendance statistics for the last 12 months"""
        try:
            from db_main import AttendanceRecord, EmployeeSchedule
            from datetime import date, timedelta

            # Calculate date range (last 12 months)
            end_date = date.today()
            start_date = end_date - timedelta(days=365)

            # Get all attendance records for this employee in the date range
            attendance_records = self.session.query(AttendanceRecord).join(
                EmployeeSchedule, AttendanceRecord.schedule_id == EmployeeSchedule.id
            ).filter(
                EmployeeSchedule.employee_id == employee_id,
                AttendanceRecord.work_date >= start_date,
                AttendanceRecord.work_date <= end_date
            ).all()

            if not attendance_records:
                self.clear_attendance_stats()
                return

            # Calculate statistics
            total_scheduled = len(attendance_records)
            days_present = sum(1 for r in attendance_records if r.attendance_status in ['Present', 'Late', 'Early Out'])
            days_late = sum(1 for r in attendance_records if
                            r.attendance_status == 'Late' or (r.minutes_late and r.minutes_late > 0))
            days_early = sum(1 for r in attendance_records if
                             r.attendance_status == 'Early Out' or (r.minutes_early_out and r.minutes_early_out > 0))
            days_absent = sum(1 for r in attendance_records if r.attendance_status == 'Absent')

            attendance_rate = (days_present / total_scheduled * 100) if total_scheduled > 0 else 0

            # Update labels
            self.total_scheduled_label.config(text=str(total_scheduled))
            self.days_present_label.config(text=str(days_present))
            self.days_late_label.config(text=str(days_late))
            self.days_early_label.config(text=str(days_early))
            self.days_absent_label.config(text=str(days_absent))
            self.attendance_rate_label.config(text=f"{attendance_rate:.1f}%")

            # Color code attendance rate
            if attendance_rate >= 95:
                color = "green"
            elif attendance_rate >= 90:
                color = "orange"
            else:
                color = "red"
            self.attendance_rate_label.config(foreground=color)

        except Exception as e:
            print(f"Error updating attendance stats: {e}")
            self.clear_attendance_stats()

    def update_recent_issues(self, employee_id):
        """Update recent attendance issues"""
        try:
            from db_main import AttendanceIssue
            from datetime import date, timedelta

            # Clear existing issues
            self.clear_attendance_issues()

            # Get recent issues (last 6 months)
            end_date = date.today()
            start_date = end_date - timedelta(days=180)

            recent_issues = self.session.query(AttendanceIssue).filter(
                AttendanceIssue.employee_id == employee_id,
                AttendanceIssue.issue_date >= start_date,
                AttendanceIssue.issue_date <= end_date
            ).order_by(AttendanceIssue.issue_date.desc()).limit(10).all()

            for issue in recent_issues:
                status_text = "Resolved" if issue.resolved else "Open"
                description = f"{issue.issue_type}"
                if issue.severity:
                    description += f" ({issue.severity})"
                if issue.action_taken:
                    description += f" - {issue.action_taken}"

                self.issues_tree.insert('', 'end', values=(
                    issue.issue_date.strftime('%Y-%m-%d') if issue.issue_date else "",
                    issue.issue_type or "",
                    description,
                    status_text
                ))

        except Exception as e:
            print(f"Error updating attendance issues: {e}")

    def clear_attendance_stats(self):
        """Clear all attendance statistics"""
        self.total_scheduled_label.config(text="0")
        self.days_present_label.config(text="0")
        self.days_late_label.config(text="0")
        self.days_early_label.config(text="0")
        self.days_absent_label.config(text="0")
        self.attendance_rate_label.config(text="0%", foreground="gray")

    def clear_attendance_issues(self):
        """Clear attendance issues tree"""
        for item in self.issues_tree.get_children():
            self.issues_tree.delete(item)

    def get_day_name(self, day_of_week):
        """Convert day of week number to name"""
        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        return days[day_of_week] if 0 <= day_of_week <= 6 else "Unknown"

    def get_level_completion_data(self, employee_id):
        """Get completion data organized by level based on your schema"""
        level_data = {}

        # Get all competencies for this employee
        evals = self.session.query(EmployeeCompetency).filter_by(employee_id=employee_id).all()

        print(f"DEBUG: Found {len(evals)} EmployeeCompetency records for employee {employee_id}")

        for rec in evals:
            # Use level_achieved from EmployeeCompetency table - this is the primary source
            level = rec.level_achieved

            if not level:
                print(f"DEBUG: No level_achieved for record {rec.id}, skipping")
                continue

            if level not in level_data:
                level_data[level] = [0, 0]  # [total, completed]

            level_data[level][0] += 1  # increment total

            # Check if completed - a record is completed if:
            # 1. Status is "Active"
            # 2. date_achieved is not empty
            is_completed = (
                    rec.status == "Active"
                    and rec.date_achieved
                    and rec.date_achieved.strip() != ""
            )

            print(
                f"DEBUG: Record {rec.id} - Level: {level}, Status: '{rec.status}', Date: '{rec.date_achieved}', Completed: {is_completed}")

            if is_completed:
                level_data[level][1] += 1  # increment completed

        print(f"DEBUG: Final level_data: {level_data}")
        return level_data

    def create_filtering_section(self):
        """Create comprehensive filtering controls in a compact 3x3 grid"""
        # Main filtering frame
        filter_main_frame = ttk.LabelFrame(self.scrollable_frame, text="Filtering & Search Options", padding="10")
        filter_main_frame.grid(row=13, column=0, columnspan=2, padx=5, pady=(10, 5), sticky="ew")

        # Configure grid weights for even spacing
        for i in range(3):
            filter_main_frame.grid_columnconfigure(i, weight=1)

        # Create 3x3 grid of filters - REMOVED REDUNDANT FILTERS
        filter_configs = [
            # Row 0 - Main categorical filters
            ("Completion Status", "completed_filter_var", "completed_filter_combo",
             ["All", "Completed", "Not Completed"], "All"),
            ("Level Filter", "level_filter_var", "level_filter_combo",
             ["All", "Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"], "All"),
            ("Competency Type", "type_filter_var", "type_filter_combo",
             ["All", "mechanical", "electrical", "tools", "operational", "safety", "training", "communication",
              "leadership"], "All"),

            # Row 1 - Status filter + unique column filters
            ("Status Filter", "status_filter_var", "status_filter_combo",
             ["All", "Active", "Expired", "Needs Renewal"], "All"),
            ("Tier Filter", "tier_column_var", "tier_column_entry", None, ""),
            ("Proficiency Filter", "proficiency_column_var", "proficiency_column_entry", None, ""),

            # Row 2 - Search + more unique filters
            ("Search Task", "task_search_var", "task_search_entry", None, ""),
            ("Date Filter", "date_column_var", "date_column_entry", None, ""),
            ("Notes Filter", "notes_column_var", "notes_column_entry", None, "")
        ]

        # Create the grid
        for idx, (label, var_name, widget_name, values, default) in enumerate(filter_configs):
            row = idx // 3
            col = idx % 3

            # Create frame for each filter
            filter_frame = ttk.Frame(filter_main_frame)
            filter_frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            filter_frame.grid_columnconfigure(0, weight=1)

            # Label
            ttk.Label(filter_frame, text=label, font=('TkDefaultFont', 8, 'bold')).grid(
                row=0, column=0, sticky="w", pady=(0, 2)
            )

            # Create variable
            var = tk.StringVar()
            setattr(self, var_name, var)
            var.set(default)

            # Create widget (combo or entry)
            if values:  # Dropdown filter
                widget = ttk.Combobox(filter_frame, textvariable=var, values=values,
                                      state="readonly", width=15, font=('TkDefaultFont', 8))
                widget.bind("<<ComboboxSelected>>", self.apply_filters)
            else:  # Text entry filter
                widget = ttk.Entry(filter_frame, textvariable=var, width=15, font=('TkDefaultFont', 8))
                var.trace("w", self.apply_filters)

            widget.grid(row=1, column=0, sticky="ew")
            setattr(self, widget_name, widget)

        # Store column filters for easy access (now includes notes)
        self.column_filters = {
            'tier': self.tier_column_var,
            'proficiency': self.proficiency_column_var,
            'date': self.date_column_var,
            'notes': self.notes_column_var
        }

    def create_action_buttons(self):
        """Create action buttons for filters and export"""
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.grid(row=18, column=0, columnspan=2, sticky="w", padx=5, pady=(5, 10))

        # Filter action buttons
        ttk.Button(button_frame, text="Clear All Filters", command=self.clear_all_filters).pack(side="left",
                                                                                                padx=(0, 10))
        ttk.Button(button_frame, text="Export Filtered Results", command=self.export_filtered_to_csv).pack(side="left",
                                                                                                           padx=(0, 10))

        # Results summary
        self.results_var = tk.StringVar()
        self.results_label = ttk.Label(button_frame, textvariable=self.results_var,
                                       font=('TkDefaultFont', 9), foreground='green')
        self.results_label.pack(side="left", padx=(20, 0))

    def apply_filters(self, *args):
        """Apply all active filters to the treeview"""
        self.refresh_eval_list()

    def passes_filters(self, record_data):
        """Check if a record passes all active filters"""
        # record_data is a tuple: (type, task, tier, proficiency, level, status, date, assessor, notes, completed)

        # Quick filters
        if self.completed_filter_var.get() != "All":
            completed_status = record_data[9]  # completed column
            if self.completed_filter_var.get() == "Completed" and completed_status != "Yes":
                return False
            if self.completed_filter_var.get() == "Not Completed" and completed_status != "No":
                return False

        if self.level_filter_var.get() != "All":
            if record_data[4] != self.level_filter_var.get():  # level column
                return False

        if self.type_filter_var.get() != "All":
            if record_data[0] != self.type_filter_var.get():  # type column
                return False

        if self.status_filter_var.get() != "All":
            if record_data[5] != self.status_filter_var.get():  # status column
                return False

        # Text search in task description
        task_search = self.task_search_var.get().lower()
        if task_search:
            if task_search not in record_data[1].lower():  # task column
                return False

        # Column-specific filters
        column_names = ["type", "task", "tier", "proficiency", "level", "status", "date", "assessor", "notes",
                        "completed"]
        for idx, col_name in enumerate(column_names):
            if col_name in self.column_filters:
                filter_text = self.column_filters[col_name].get().lower()
                if filter_text and filter_text not in str(record_data[idx]).lower():
                    return False

        return True

    def refresh_eval_list(self):
        """Refresh the evaluation list with applied filters"""
        # Clear all rows
        for row in self.eval_tree.get_children():
            self.eval_tree.delete(row)

        emp_id = self.get_selected(self.employee_combo, self.employee_choices)
        if not emp_id:
            self.breakdown_var.set("")
            self.results_var.set("No employee selected")
            return

        evals = self.session.query(EmployeeCompetency).filter_by(employee_id=emp_id).all()
        total_records = len(evals)
        filtered_count = 0

        for rec in evals:
            comp = self.session.query(CoreCompetency).get(rec.competency_id)
            assessor = self.session.query(Employee).get(rec.assessed_by) if rec.assessed_by else None

            # ===== Get correct task details =====
            task_action = ""
            task_object = ""
            verification_method = ""
            task_desc = ""
            ctype = (comp.competency_type or "").lower() if comp else ""

            # Always use `.get(comp.id)` for all 3!
            if ctype in ("mechanical_task", "mechanical"):
                task_row = self.session.query(MechanicalTask).get(comp.id)
            elif ctype in ("electrical_task", "electrical"):
                task_row = self.session.query(ElectricalTask).get(comp.id)
            elif ctype in ("operational_task", "operational"):
                task_row = self.session.query(OperationalTask).get(comp.id)
            else:
                task_row = None

            if task_row:
                task_action = getattr(task_row, "task_action", "") or ""
                task_object = getattr(task_row, "task_object", "") or ""
                verification_method = getattr(task_row, "verification_method", "") or ""
                task_desc = f"{task_action} {task_object}".strip()
            else:
                # Fallback: Show the competency name if not a known type or if no detail record exists
                task_desc = getattr(comp, "competency_name", "") if comp else ""

            is_completed = (
                    rec.status == "Active"
                    and rec.date_achieved
                    and rec.date_achieved.strip() != ""
            )
            completed_text = "Yes" if is_completed else "No"

            record_data = (
                comp.competency_type if comp else "",
                task_desc,
                (comp.proficiency_level.split('_')[-1] if comp and comp.proficiency_level else ""),
                rec.proficiency_achieved or "",
                rec.level_achieved or "",
                rec.status or "",
                rec.date_achieved or "",
                f"{assessor.employee_id}" if assessor else "",
                rec.notes or "",
                completed_text
            )

            # Apply filters
            if self.passes_filters(record_data):
                print(f"ADDING: {record_data}")
                self.eval_tree.insert(
                    '', 'end',
                    iid=str(rec.id),
                    values=record_data
                )
                filtered_count += 1

        # Update results summary
        self.results_var.set(f"Showing {filtered_count} of {total_records} records")

        # Update completion breakdown
        breakdown = self.get_completion_breakdown()
        if breakdown:
            summary_lines = [f"{ctype}: {completed}/{total} completed"
                             for ctype, (total, completed) in breakdown.items()]
            self.breakdown_var.set(" | ".join(summary_lines))
        else:
            self.breakdown_var.set("No records for this employee.")

    def clear_all_filters(self):
        """Clear all filter settings"""
        # Clear quick filters
        self.completed_filter_var.set("All")
        self.level_filter_var.set("All")
        self.type_filter_var.set("All")
        self.status_filter_var.set("All")

        # Clear text search
        self.task_search_var.set("")

        # Clear column filters
        for var in self.column_filters.values():
            var.set("")

        # Refresh the list
        self.refresh_eval_list()

    def export_filtered_to_csv(self):
        """Export currently filtered results to CSV"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Save Filtered Data As"
        )
        if not file_path:
            return

        columns = ["Type", "Task", "Tier", "Proficiency", "Level", "Status", "Date", "Assessor", "Notes", "Completed"]
        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(columns)

                # Export only visible (filtered) items
                for item_id in self.eval_tree.get_children():
                    writer.writerow(self.eval_tree.item(item_id)['values'])

            messagebox.showinfo("Export Complete",
                                f"Filtered data exported to:\n{file_path}\n"
                                f"Records exported: {len(self.eval_tree.get_children())}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Error: {e}")

    def display_employee_info(self, employee_id):
        """Display detailed employee information, update progress bars, and show attendance info"""
        if not employee_id:
            # Clear all employee info labels
            self.emp_id_label.config(text="")
            self.emp_name_label.config(text="")
            self.emp_hire_label.config(text="")
            self.emp_status_label.config(text="")
            self.emp_type_label.config(text="")
            self.emp_reports_label.config(text="")

            # Clear progress bars
            self.update_progress_bars(None)

            # Clear attendance info
            self.update_attendance_info(None)
            return

        employee = self.session.query(Employee).get(employee_id)
        if not employee:
            return

        # Update employee info labels
        self.emp_id_label.config(text=employee.employee_id or "N/A")
        self.emp_name_label.config(text=f"{employee.name_first or ''} {employee.name_last or ''}".strip() or "N/A")
        self.emp_hire_label.config(text=employee.hire_date or "N/A")
        self.emp_status_label.config(text=employee.status or "N/A")
        self.emp_type_label.config(text=employee.employee_type or "N/A")

        # Handle reports to
        if employee.reports_to:
            reports_to_text = f"{employee.reports_to.employee_id} - {employee.reports_to.name_first} {employee.reports_to.name_last}"
        else:
            reports_to_text = "N/A"
        self.emp_reports_label.config(text=reports_to_text)

        # Update progress bars
        self.update_progress_bars(employee_id)

        # Update attendance info
        self.update_attendance_info(employee_id)

    def get_completion_breakdown(self):
        emp_id = self.get_selected(self.employee_combo, self.employee_choices)
        if not emp_id:
            return {}

        evals = self.session.query(EmployeeCompetency).filter_by(employee_id=emp_id).all()
        summary = {}
        for rec in evals:
            comp = self.session.query(CoreCompetency).get(rec.competency_id)
            if not comp:
                continue
            ctype = comp.competency_type or "Unknown"
            total, completed = summary.get(ctype, (0, 0))
            total += 1
            if rec.status == "Active" and rec.date_achieved and rec.date_achieved.strip() != "":
                completed += 1
            summary[ctype] = (total, completed)
        return summary

    def load_employees(self):
        employees = self.session.query(Employee).all()
        self.employee_choices = [(e.id, f"{e.employee_id} - {e.name_first} {e.name_last}") for e in employees]
        self.employee_combo['values'] = [desc for _, desc in self.employee_choices]
        self.employee_var.set('')

    def load_assessors(self):
        assessors = self.session.query(Employee).all()
        self.assessor_choices = [(e.id, f"{e.employee_id} - {e.name_first} {e.name_last}") for e in assessors]
        self.assessor_combo['values'] = [desc for _, desc in self.assessor_choices]
        self.assessor_var.set('')

    def get_selected(self, combo, choices):
        idx = combo.current()
        if idx == -1:
            return None
        return choices[idx][0]

    def on_employee_selected(self, event=None):
        """Handle employee selection - display info and refresh eval list"""
        emp_id = self.get_selected(self.employee_combo, self.employee_choices)
        self.display_employee_info(emp_id)
        self.refresh_eval_list()

    def assign_all_level_tasks(self):
        emp_id = self.get_selected(self.employee_combo, self.employee_choices)
        selected_level = self.level_var.get()
        assessor_id = self.get_selected(self.assessor_combo, self.assessor_choices)
        status = self.status_var.get()
        date = self.date_entry.get()
        notes = self.notes_text.get("1.0", "end").strip()

        if not emp_id or not selected_level:
            messagebox.showwarning("Missing Info", "Please select both an employee and a level.")
            return

        competencies = self.session.query(CoreCompetency).filter_by(level=selected_level).all()
        if not competencies:
            messagebox.showinfo("No Tasks", f"No competencies found for level: {selected_level}")
            return

        assigned_count = 0
        for comp in competencies:
            existing = self.session.query(EmployeeCompetency).filter_by(
                employee_id=emp_id, competency_id=comp.id
            ).first()
            if existing:
                continue
            record = EmployeeCompetency(
                employee_id=emp_id,
                competency_id=comp.id,
                proficiency_achieved=None,
                level_achieved=selected_level,
                date_achieved=date,
                assessed_by=assessor_id,
                status=status,
                notes=notes
            )
            self.session.add(record)
            assigned_count += 1

        try:
            self.session.commit()
            messagebox.showinfo("Assigned",
                                f"Assigned {assigned_count} competencies for level '{selected_level}' to employee.")
            self.refresh_eval_list()
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to assign competencies: {e}")

    def save_treeview_edit(self, item_id, field, new_value):
        # Lookup the record by PK (iid), not by order!
        record = self.session.query(EmployeeCompetency).get(int(item_id))
        if not record:
            return
        try:
            if field == 'proficiency':
                record.proficiency_achieved = new_value
            elif field == 'level':
                record.level_achieved = new_value
            elif field == 'status':
                record.status = new_value
            elif field == 'date':
                record.date_achieved = new_value
            elif field == 'notes':
                record.notes = new_value
            self.session.commit()
            self.refresh_eval_list()  # Always refresh so "Completed" column is recalculated
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to save edit: {e}")

    def sort_treeview(self, col, reverse):
        """Sort treeview by column"""
        data_list = [(self.eval_tree.set(k, col), k) for k in self.eval_tree.get_children("")]
        try:
            # Try to sort numerically if possible
            data_list.sort(key=lambda t: float(t[0]) if t[0].replace('.', '', 1).isdigit() else t[0], reverse=reverse)
        except Exception:
            # Fall back to string sorting
            data_list.sort(reverse=reverse)

        for idx, (val, k) in enumerate(data_list):
            self.eval_tree.move(k, '', idx)

        # Update the heading command for next click
        self.eval_tree.heading(col, command=lambda: self.sort_treeview(col, not reverse))

    def on_treeview_double_click(self, event):
        """Handle double-click editing of treeview cells"""
        item_id = self.eval_tree.identify_row(event.y)
        column = self.eval_tree.identify_column(event.x)
        if not item_id or column == '#0':
            return

        col_index = int(column.replace('#', '')) - 1
        columns = ["type", "task", "tier", "proficiency", "level", "status", "date", "assessor", "notes", "completed"]

        field = columns[col_index]
        if field in ['completed', 'type', 'task', 'tier']:  # Non-editable columns
            return

        cur_value = self.eval_tree.set(item_id, field)
        x, y, width, height = self.eval_tree.bbox(item_id, column)

        # For notes field, create a larger text widget
        if field == 'notes':
            self.create_notes_editor(item_id, x, y, width, height, cur_value)
        else:
            # Create regular edit popup for other fields
            entry_popup = tk.Entry(self.eval_tree)
            entry_popup.insert(0, cur_value)
            entry_popup.place(x=x, y=y, width=width, height=height)

            def save_edit(event):
                new_value = entry_popup.get()
                self.eval_tree.set(item_id, field, new_value)
                entry_popup.destroy()
                self.save_treeview_edit(item_id, field, new_value)

            def cancel_edit(event):
                entry_popup.destroy()

            entry_popup.bind('<Return>', save_edit)
            entry_popup.bind('<Escape>', cancel_edit)
            entry_popup.bind('<FocusOut>', lambda e: entry_popup.destroy())
            entry_popup.focus_set()
            entry_popup.select_range(0, tk.END)

    def create_notes_editor(self, item_id, x, y, width, height, current_value):
        """Create a larger text editor for notes"""
        # Create a toplevel window for notes editing
        notes_window = tk.Toplevel(self.eval_tree)
        notes_window.title("Edit Notes")
        notes_window.geometry("400x200")
        notes_window.transient(self.eval_tree.winfo_toplevel())
        notes_window.grab_set()

        # Center the window
        notes_window.update_idletasks()
        x_pos = (notes_window.winfo_screenwidth() // 2) - (notes_window.winfo_width() // 2)
        y_pos = (notes_window.winfo_screenheight() // 2) - (notes_window.winfo_height() // 2)
        notes_window.geometry(f"+{x_pos}+{y_pos}")

        # Create text widget with scrollbar
        text_frame = ttk.Frame(notes_window)
        text_frame.pack(fill='both', expand=True, padx=10, pady=10)

        notes_text = tk.Text(text_frame, wrap='word', height=8, width=50)
        scrollbar = ttk.Scrollbar(text_frame, orient='vertical', command=notes_text.yview)
        notes_text.configure(yscrollcommand=scrollbar.set)

        notes_text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Insert current value
        notes_text.insert('1.0', current_value)
        notes_text.focus_set()

        # Button frame
        button_frame = ttk.Frame(notes_window)
        button_frame.pack(fill='x', padx=10, pady=(0, 10))

        def save_notes():
            new_value = notes_text.get('1.0', tk.END).strip()
            self.eval_tree.set(item_id, 'notes',
                               new_value[:50] + "..." if len(new_value) > 50 else new_value)  # Truncate display
            notes_window.destroy()
            self.save_treeview_edit(item_id, 'notes', new_value)

        def cancel_notes():
            notes_window.destroy()

        ttk.Button(button_frame, text="Save", command=save_notes).pack(side='right', padx=(5, 0))
        ttk.Button(button_frame, text="Cancel", command=cancel_notes).pack(side='right')

        # Bind Enter with Ctrl to save
        notes_text.bind('<Control-Return>', lambda e: save_notes())

# Additional utility methods for enhanced functionality

def create_filter_summary_widget(self):
    """Create a widget that shows active filters summary"""
    summary_frame = ttk.LabelFrame(self.scrollable_frame, text="Active Filters", padding="5")
    summary_frame.grid(row=14, column=0, columnspan=2, padx=5, pady=(5, 0), sticky="ew")

    self.filter_summary_var = tk.StringVar()
    self.filter_summary_label = ttk.Label(summary_frame, textvariable=self.filter_summary_var,
                                          font=('TkDefaultFont', 8), foreground='darkblue')
    self.filter_summary_label.pack(anchor='w')

    return summary_frame


def update_filter_summary(self):
    """Update the active filters summary"""
    active_filters = []

    if self.completed_filter_var.get() != "All":
        active_filters.append(f"Completion: {self.completed_filter_var.get()}")

    if self.level_filter_var.get() != "All":
        active_filters.append(f"Level: {self.level_filter_var.get()}")

    if self.type_filter_var.get() != "All":
        active_filters.append(f"Type: {self.type_filter_var.get()}")

    if self.status_filter_var.get() != "All":
        active_filters.append(f"Status: {self.status_filter_var.get()}")

    if self.task_search_var.get():
        active_filters.append(f"Task Search: '{self.task_search_var.get()}'")

    # Check column filters
    for col, var in self.column_filters.items():
        if var.get():
            active_filters.append(f"{col.title()}: '{var.get()}'")

    if active_filters:
        self.filter_summary_var.set("Active Filters: " + " | ".join(active_filters))
    else:
        self.filter_summary_var.set("No filters active - showing all records")

class AttendanceShiftTab:
    def __init__(self, parent_notebook, session):
        # Create the main frame for this tab
        self.frame = ttk.Frame(parent_notebook)
        parent_notebook.add(self.frame, text="Attendance - Shifts")

        # Store database session
        self.session = session

        self.days_of_week = [
            {'value': 0, 'name': 'Sunday', 'short': 'Sun'},
            {'value': 1, 'name': 'Monday', 'short': 'Mon'},
            {'value': 2, 'name': 'Tuesday', 'short': 'Tue'},
            {'value': 3, 'name': 'Wednesday', 'short': 'Wed'},
            {'value': 4, 'name': 'Thursday', 'short': 'Thu'},
            {'value': 5, 'name': 'Friday', 'short': 'Fri'},
            {'value': 6, 'name': 'Saturday', 'short': 'Sat'}
        ]

        self.is_creating = False
        self.editing_shift_id = None
        self.day_vars = {}  # Checkbox variables for days
        self.time_vars = {}  # Time entry variables

        self.setup_ui()
        self.refresh_shift_list()

    def setup_ui(self):
        # Main container with scrollbar
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Header
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label = ttk.Label(header_frame, text="Shift Management", font=('Arial', 16, 'bold'))
        title_label.pack(side=tk.LEFT)

        self.create_btn = ttk.Button(header_frame, text="Create New Shift", command=self.start_create)
        self.create_btn.pack(side=tk.RIGHT)

        # Create/Edit Form Frame (initially hidden)
        self.form_frame = ttk.LabelFrame(main_container, text="Shift Details", padding=10)

        # Shift basic info
        info_frame = ttk.Frame(self.form_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # Row 0: Shift name and Description
        ttk.Label(info_frame, text="Shift Name:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.name_var = tk.StringVar()
        name_entry = ttk.Entry(info_frame, textvariable=self.name_var, width=25)
        name_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        ttk.Label(info_frame, text="Description:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.desc_var = tk.StringVar()
        desc_entry = ttk.Entry(info_frame, textvariable=self.desc_var, width=25)
        desc_entry.grid(row=0, column=3, sticky=tk.W)

        # Row 1: Shift Pattern and Active checkbox
        ttk.Label(info_frame, text="Shift Pattern:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(10, 0))
        self.pattern_var = tk.StringVar(value="weekly")
        pattern_combo = ttk.Combobox(info_frame, textvariable=self.pattern_var,
                                     values=["weekly", "biweekly"], state="readonly", width=12)
        pattern_combo.grid(row=1, column=1, sticky=tk.W, padx=(0, 20), pady=(10, 0))
        pattern_combo.bind("<<ComboboxSelected>>", self.on_pattern_changed)

        self.active_var = tk.BooleanVar(value=True)
        active_check = ttk.Checkbutton(info_frame, text="Active Shift", variable=self.active_var)
        active_check.grid(row=1, column=2, columnspan=2, sticky=tk.W, pady=(10, 0))

        # Pattern explanation label
        self.pattern_help = ttk.Label(info_frame, text="Weekly: Same schedule every week",
                                      font=('TkDefaultFont', 8), foreground='blue')
        self.pattern_help.grid(row=2, column=0, columnspan=4, sticky=tk.W, pady=(5, 0))

        # Days and times frame
        self.days_frame = ttk.LabelFrame(self.form_frame, text="Schedule Days & Times", padding=5)
        self.days_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # This will be populated by create_schedule_ui()
        self.create_schedule_ui()

        # Form buttons
        button_frame = ttk.Frame(self.form_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        self.save_btn = ttk.Button(button_frame, text="Save Shift", command=self.save_shift)
        self.save_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.cancel_btn = ttk.Button(button_frame, text="Cancel", command=self.cancel_form)
        self.cancel_btn.pack(side=tk.LEFT)

        # Shift list frame
        self.list_frame = ttk.LabelFrame(main_container, text="Existing Shifts", padding=5)
        self.list_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Create treeview for shift list
        columns = ('ID', 'Name', 'Description', 'Pattern', 'Days', 'Status')
        self.shift_tree = ttk.Treeview(self.list_frame, columns=columns, show='headings', height=8)

        # Configure columns
        self.shift_tree.heading('ID', text='ID')
        self.shift_tree.heading('Name', text='Shift Name')
        self.shift_tree.heading('Description', text='Description')
        self.shift_tree.heading('Pattern', text='Pattern')
        self.shift_tree.heading('Days', text='Days Worked')
        self.shift_tree.heading('Status', text='Status')

        self.shift_tree.column('ID', width=50)
        self.shift_tree.column('Name', width=180)
        self.shift_tree.column('Description', width=200)
        self.shift_tree.column('Pattern', width=80)
        self.shift_tree.column('Days', width=200)
        self.shift_tree.column('Status', width=80)

        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.shift_tree.yview)
        self.shift_tree.configure(yscrollcommand=scrollbar.set)

        self.shift_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Action buttons for selected shift
        action_frame = ttk.Frame(self.list_frame)
        action_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

        ttk.Button(action_frame, text="Edit Selected", command=self.edit_selected).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT)

    def on_pattern_changed(self, event=None):
        """Handle shift pattern change"""
        pattern = self.pattern_var.get()
        if pattern == "weekly":
            self.pattern_help.config(text="Weekly: Same schedule every week")
        elif pattern == "biweekly":
            self.pattern_help.config(text="Bi-weekly: Alternating 2-week pattern (Week 1 and Week 2)")

        # Recreate the schedule UI
        self.create_schedule_ui()

    def create_schedule_ui(self):
        """Create the schedule UI based on selected pattern"""
        # Clear existing schedule widgets
        for widget in self.days_frame.winfo_children():
            widget.destroy()

        self.day_vars.clear()
        self.time_vars.clear()

        pattern = self.pattern_var.get()

        if pattern == "weekly":
            self.create_weekly_schedule_ui()
        elif pattern == "biweekly":
            self.create_biweekly_schedule_ui()

    def create_weekly_schedule_ui(self):
        """Create UI for weekly schedule pattern"""
        for i, day in enumerate(self.days_of_week):
            day_frame = ttk.Frame(self.days_frame)
            day_frame.pack(fill=tk.X, pady=2)

            # Day checkbox
            day_var = tk.BooleanVar()
            self.day_vars[f"{day['value']}_1"] = day_var  # Week 1 (only week for weekly pattern)

            day_check = ttk.Checkbutton(day_frame, text=day['name'], variable=day_var,
                                        command=lambda d=day['value']: self.on_day_toggle(f"{d}_1"))
            day_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))

            # Time frame
            time_frame = ttk.Frame(day_frame)
            time_frame.pack(side=tk.LEFT)

            ttk.Label(time_frame, text="Start:").pack(side=tk.LEFT, padx=(0, 5))

            start_var = tk.StringVar(value="07:00")
            self.time_vars[f"{day['value']}_1_start"] = start_var
            start_entry = ttk.Entry(time_frame, textvariable=start_var, width=8)
            start_entry.pack(side=tk.LEFT, padx=(0, 10))

            ttk.Label(time_frame, text="End:").pack(side=tk.LEFT, padx=(0, 5))

            end_var = tk.StringVar(value="15:00")
            self.time_vars[f"{day['value']}_1_end"] = end_var
            end_entry = ttk.Entry(time_frame, textvariable=end_var, width=8)
            end_entry.pack(side=tk.LEFT)

            # Store references
            self.time_vars[f"{day['value']}_1_start_entry"] = start_entry
            self.time_vars[f"{day['value']}_1_end_entry"] = end_entry

            # Initially disable
            self.toggle_day_times(f"{day['value']}_1", False)

    def create_biweekly_schedule_ui(self):
        """Create UI for bi-weekly schedule pattern"""
        # Create notebook for Week 1 and Week 2
        week_notebook = ttk.Notebook(self.days_frame)
        week_notebook.pack(fill=tk.BOTH, expand=True)

        # Week 1 tab
        week1_frame = ttk.Frame(week_notebook)
        week_notebook.add(week1_frame, text="Week 1")

        # Week 2 tab
        week2_frame = ttk.Frame(week_notebook)
        week_notebook.add(week2_frame, text="Week 2")

        # Create schedule for each week
        for week_num, week_frame in [(1, week1_frame), (2, week2_frame)]:
            for i, day in enumerate(self.days_of_week):
                day_frame = ttk.Frame(week_frame)
                day_frame.pack(fill=tk.X, pady=2)

                # Day checkbox
                day_var = tk.BooleanVar()
                self.day_vars[f"{day['value']}_{week_num}"] = day_var

                day_check = ttk.Checkbutton(day_frame, text=day['name'], variable=day_var,
                                            command=lambda d=day['value'], w=week_num: self.on_day_toggle(f"{d}_{w}"))
                day_check.pack(side=tk.LEFT, anchor=tk.W, padx=(0, 20))

                # Time frame
                time_frame = ttk.Frame(day_frame)
                time_frame.pack(side=tk.LEFT)

                ttk.Label(time_frame, text="Start:").pack(side=tk.LEFT, padx=(0, 5))

                start_var = tk.StringVar(value="07:00")
                self.time_vars[f"{day['value']}_{week_num}_start"] = start_var
                start_entry = ttk.Entry(time_frame, textvariable=start_var, width=8)
                start_entry.pack(side=tk.LEFT, padx=(0, 10))

                ttk.Label(time_frame, text="End:").pack(side=tk.LEFT, padx=(0, 5))

                end_var = tk.StringVar(value="15:00")
                self.time_vars[f"{day['value']}_{week_num}_end"] = end_var
                end_entry = ttk.Entry(time_frame, textvariable=end_var, width=8)
                end_entry.pack(side=tk.LEFT)

                # Store references
                self.time_vars[f"{day['value']}_{week_num}_start_entry"] = start_entry
                self.time_vars[f"{day['value']}_{week_num}_end_entry"] = end_entry

                # Initially disable
                self.toggle_day_times(f"{day['value']}_{week_num}", False)

    def on_day_toggle(self, day_key):
        """Handle day checkbox toggle"""
        is_checked = self.day_vars[day_key].get()
        self.toggle_day_times(day_key, is_checked)

    def toggle_day_times(self, day_key, enabled):
        """Enable/disable time entries for a day"""
        state = tk.NORMAL if enabled else tk.DISABLED
        start_entry = self.time_vars.get(f"{day_key}_start_entry")
        end_entry = self.time_vars.get(f"{day_key}_end_entry")

        if start_entry:
            start_entry.config(state=state)
        if end_entry:
            end_entry.config(state=state)

    def start_create(self):
        """Show create form"""
        self.is_creating = True
        self.editing_shift_id = None
        self.clear_form()
        self.form_frame.pack(fill=tk.X, pady=(0, 10))
        self.create_btn.config(state=tk.DISABLED)

    def edit_selected(self):
        """Edit selected shift"""
        selection = self.shift_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a shift to edit.")
            return

        shift_id = int(self.shift_tree.item(selection[0])['values'][0])
        shift = self.session.query(Shift).get(shift_id)
        if not shift:
            messagebox.showerror("Error", "Shift not found.")
            return

        self.is_creating = True
        self.editing_shift_id = shift_id
        self.load_shift_to_form(shift)
        self.form_frame.pack(fill=tk.X, pady=(0, 10))
        self.create_btn.config(state=tk.DISABLED)

    def load_shift_to_form(self, shift):
        """Load shift data into form"""
        self.name_var.set(shift.shift_name)
        self.desc_var.set(shift.description or "")
        self.active_var.set(shift.is_active)
        self.pattern_var.set(shift.shift_pattern or "weekly")

        # Recreate UI for the pattern
        self.create_schedule_ui()

        # Load shift days
        for shift_day in shift.shift_days:
            day_value = shift_day.day_of_week
            week_num = getattr(shift_day, 'week_number', 1)
            day_key = f"{day_value}_{week_num}"

            if day_key in self.day_vars:
                self.day_vars[day_key].set(True)

                # Convert time objects to string format
                start_time = shift_day.scheduled_start_time.strftime('%H:%M')
                end_time = shift_day.scheduled_end_time.strftime('%H:%M')

                self.time_vars[f"{day_key}_start"].set(start_time)
                self.time_vars[f"{day_key}_end"].set(end_time)
                self.toggle_day_times(day_key, True)

    def clear_form(self):
        """Clear form fields"""
        self.name_var.set("")
        self.desc_var.set("")
        self.active_var.set(True)
        self.pattern_var.set("weekly")

        # Recreate UI
        self.create_schedule_ui()

    def save_shift(self):
        """Save shift data to database"""
        # Validate
        if not self.name_var.get().strip():
            messagebox.showerror("Validation Error", "Shift name is required.")
            return

        # Get selected days
        selected_days = []
        pattern = self.pattern_var.get()

        # Determine which weeks to check
        weeks_to_check = [1] if pattern == "weekly" else [1, 2]

        for week_num in weeks_to_check:
            for day_value in range(7):
                day_key = f"{day_value}_{week_num}"

                if day_key in self.day_vars and self.day_vars[day_key].get():
                    start_time_str = self.time_vars[f"{day_key}_start"].get()
                    end_time_str = self.time_vars[f"{day_key}_end"].get()

                    # Basic time validation
                    if not self.validate_time(start_time_str) or not self.validate_time(end_time_str):
                        day_name = next(d['name'] for d in self.days_of_week if d['value'] == day_value)
                        week_text = f"Week {week_num}" if pattern == "biweekly" else ""
                        messagebox.showerror("Validation Error",
                                             f"Invalid time format for {day_name} {week_text}. Use HH:MM format.")
                        return

                    # Convert string to time object
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()

                    selected_days.append({
                        'day_of_week': day_value,
                        'week_number': week_num,
                        'start_time': start_time,
                        'end_time': end_time
                    })

        if not selected_days:
            messagebox.showerror("Validation Error", "At least one day must be selected.")
            return

        try:
            if self.editing_shift_id:
                # Update existing shift
                shift = self.session.query(Shift).get(self.editing_shift_id)
                shift.shift_name = self.name_var.get().strip()
                shift.description = self.desc_var.get().strip()
                shift.is_active = self.active_var.get()
                shift.shift_pattern = self.pattern_var.get()

                # Delete existing shift days
                for shift_day in shift.shift_days:
                    self.session.delete(shift_day)

                # Add new shift days
                for day_data in selected_days:
                    shift_day = ShiftDay(
                        shift_id=shift.id,
                        day_of_week=day_data['day_of_week'],
                        week_number=day_data['week_number'],
                        scheduled_start_time=day_data['start_time'],
                        scheduled_end_time=day_data['end_time']
                    )
                    self.session.add(shift_day)
            else:
                # Create new shift
                shift = Shift(
                    shift_name=self.name_var.get().strip(),
                    description=self.desc_var.get().strip(),
                    is_active=self.active_var.get(),
                    shift_pattern=self.pattern_var.get()
                )
                self.session.add(shift)
                self.session.flush()  # Get the ID

                # Add shift days
                for day_data in selected_days:
                    shift_day = ShiftDay(
                        shift_id=shift.id,
                        day_of_week=day_data['day_of_week'],
                        week_number=day_data['week_number'],
                        scheduled_start_time=day_data['start_time'],
                        scheduled_end_time=day_data['end_time']
                    )
                    self.session.add(shift_day)

            self.session.commit()
            self.cancel_form()
            self.refresh_shift_list()
            messagebox.showinfo("Success", "Shift saved successfully!")

        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to save shift: {e}")

    def validate_time(self, time_str):
        """Validate time format HH:MM"""
        try:
            datetime.strptime(time_str, '%H:%M')
            return True
        except ValueError:
            return False

    def cancel_form(self):
        """Cancel form and hide it"""
        self.is_creating = False
        self.editing_shift_id = None
        self.form_frame.pack_forget()
        self.create_btn.config(state=tk.NORMAL)

    def delete_selected(self):
        """Delete selected shift"""
        selection = self.shift_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a shift to delete.")
            return

        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this shift?"):
            try:
                shift_id = int(self.shift_tree.item(selection[0])['values'][0])
                shift = self.session.query(Shift).get(shift_id)

                if shift:
                    self.session.delete(shift)
                    self.session.commit()
                    self.refresh_shift_list()
                    messagebox.showinfo("Success", "Shift deleted successfully!")

            except Exception as e:
                self.session.rollback()
                messagebox.showerror("Error", f"Failed to delete shift: {e}")

    def refresh_shift_list(self):
        """Refresh the shift list display from database"""
        # Clear existing items
        for item in self.shift_tree.get_children():
            self.shift_tree.delete(item)

        # Get shifts from database
        shifts = self.session.query(Shift).all()

        for shift in shifts:
            # Get days worked (organized by week for bi-weekly shifts)
            if shift.shift_pattern == "biweekly":
                week1_days = []
                week2_days = []

                for shift_day in sorted(shift.shift_days, key=lambda x: (x.week_number, x.day_of_week)):
                    day_name = next(d['short'] for d in self.days_of_week if d['value'] == shift_day.day_of_week)
                    if getattr(shift_day, 'week_number', 1) == 1:
                        week1_days.append(day_name)
                    else:
                        week2_days.append(day_name)

                days_str = f"W1: {', '.join(week1_days) if week1_days else 'None'} | W2: {', '.join(week2_days) if week2_days else 'None'}"
            else:
                # Weekly pattern
                days_worked = []
                for shift_day in sorted(shift.shift_days, key=lambda x: x.day_of_week):
                    day_name = next(d['short'] for d in self.days_of_week if d['value'] == shift_day.day_of_week)
                    days_worked.append(day_name)
                days_str = ', '.join(days_worked)

            status = "Active" if shift.is_active else "Inactive"
            pattern = shift.shift_pattern or "weekly"

            self.shift_tree.insert('', 'end', values=(
                shift.id,
                shift.shift_name,
                shift.description or "",
                pattern.title(),
                days_str,
                status
            ))



if __name__ == "__main__":
    bootstrap = tk.Tk()
    bootstrap.withdraw()

    dlg = MultiUserLoginDialog(bootstrap, "Login", session)
    user = dlg.current_user
    bootstrap.destroy()

    if not user:
        sys.exit(0)

    root = tk.Tk()
    app = EmployeeViewerApp(root, current_user=user)
    root.mainloop()
