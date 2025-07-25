import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_main import Employee, MaintenancePerson, Supervisor, TechnicalSkill, MechanicalSkill, ElectricalSkill, ToolSkill
from db_main import( CoreCompetency,  AreaChecklist, ChecklistSection, ChecklistTask, OperationalTask,OperationalSkill,MechanicalTask,
                     ElectricalTask, ToolTask, TaskSkillAssignment, ChecklistTaskCompetency, EmployeeCompetency)
import tkinter as tk
from tkinter import ttk, messagebox



DATABASE_FILE = 'maintenance_skills.db'
engine = create_engine(f'sqlite:///{DATABASE_FILE}')
Session = sessionmaker(bind=engine)
session = Session()


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
            ttk.Label(master, text=label).grid(row=idx, column=0, sticky='e')
            if label == "Status":
                self.status_var = tk.StringVar()
                combo = ttk.Combobox(master, textvariable=self.status_var, values=["Active", "Not Active"],
                                     state="readonly")
                combo.grid(row=idx, column=1)
                if self.employee and self.employee.status:
                    self.status_var.set(self.employee.status)
                else:
                    self.status_var.set("Active")
                self.entries[label] = combo
            elif label == "Employee Type":
                self.emp_type_var = tk.StringVar()
                combo = ttk.Combobox(master, textvariable=self.emp_type_var,
                                     values=["Employee", "Supervisor", "MaintenancePerson"], state="readonly")
                combo.grid(row=idx, column=1)
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
                combo.grid(row=idx, column=1)
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
                entry.grid(row=idx, column=1)
                self.entries[label] = entry

        # Subclass-specific fields
        self.subfield_frame = ttk.Frame(master)
        self.subfield_frame.grid(row=len(labels), column=0, columnspan=2)
        self.subfields = {}
        self.update_subfields()
        self.emp_type_var.trace_add("write", lambda *a: self.update_subfields())

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

    def update_subfields(self):
        for child in self.subfield_frame.winfo_children():
            child.destroy()
        self.subfields = {}
        etype = self.emp_type_var.get() if hasattr(self, "emp_type_var") else "Employee"
        row = 0
        if etype == "Supervisor":
            ttk.Label(self.subfield_frame, text="Management Level").grid(row=row, column=0, sticky='e')
            entry = ttk.Entry(self.subfield_frame)
            entry.grid(row=row, column=1)
            self.subfields["management_level"] = entry
        elif etype == "MaintenancePerson":
            ttk.Label(self.subfield_frame, text="Maintenance Level").grid(row=row, column=0, sticky='e')
            maint_level_var = tk.StringVar()
            combo = ttk.Combobox(self.subfield_frame, textvariable=maint_level_var, values=self.MAINTENANCE_LEVELS, state="readonly")
            combo.grid(row=row, column=1)
            self.subfields["maintenance_level"] = maint_level_var  # Save StringVar, not widget

            row += 1
            ttk.Label(self.subfield_frame, text="Qualified Area").grid(row=row, column=0, sticky='e')
            entry2 = ttk.Entry(self.subfield_frame)
            entry2.grid(row=row, column=1)
            self.subfields["qualified_area"] = entry2

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

class EmployeeViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Maintenance Skills Database")
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)

        # First tab: Employees
        self.employee_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.employee_tab, text="Employees")
        self.setup_employee_table(parent=self.employee_tab)
        self.setup_buttons(parent=self.employee_tab)
        self.refresh_employee_list()

        self.step_up_eval_tab = StepUpEvalTab(self.notebook, session)
        self.notebook.add(self.step_up_eval_tab, text="Step-Up Eval")

        # Second tab: Skills Matrix Assignment
        #self.skills_matrix_tab = SkillsMatrixAssignmentTab(self.notebook, session)
        #self.notebook.add(self.skills_matrix_tab, text="Skills Matrix Assignment")

        # NEW: Competency Assignment Form tab
        self.competency_assignment_tab = CompetencyAssignmentFormTab(self.notebook, session)
        self.notebook.add(self.competency_assignment_tab, text="Competency Assignment Form")

        # Pass the skills matrix tab reference to the task CRUD tabs!
        #self.mechanical_task_tab = SkillTaskCrudTab(self.notebook, session, "Mechanical", self.skills_matrix_tab)
        #self.notebook.add(self.mechanical_task_tab, text="Mechanical Tasks")

        #self.electrical_task_tab = SkillTaskCrudTab(self.notebook, session, "Electrical", self.skills_matrix_tab)
        #self.notebook.add(self.electrical_task_tab, text="Electrical Tasks")

        #self.tool_task_tab = SkillTaskCrudTab(self.notebook, session, "Tool", self.skills_matrix_tab)
        #self.notebook.add(self.tool_task_tab, text="Tool Tasks")

        #self.operational_task_tab = SkillTaskCrudTab(self.notebook, session, "Operational", self.skills_matrix_tab)
        #self.notebook.add(self.operational_task_tab, text="Operational Tasks")

        # Skill Category CRUD tabs (after other tabs)
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

        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        selected_tab = event.widget.select()
        tab_text = event.widget.tab(selected_tab, "text")
        if tab_text == "Competency Assignment Form":
            self.competency_assignment_tab.refresh_dropdowns()
        elif tab_text == "Skills Matrix Assignment":
            self.skills_matrix_tab.populate_skill_combos()
            self.skills_matrix_tab.refresh_tasks()

    def setup_employee_table(self,parent):
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
        for row in self.tree.get_children():
            self.tree.delete(row)
        employees = session.query(Employee).all()
        for emp in employees:
            self.tree.insert('', 'end', values=(
                emp.id, emp.employee_id, emp.name_first, emp.name_last,
                emp.hire_date, emp.birthdate, emp.status,
                emp.employee_type, emp.reports_to_id
            ))

    def add_employee(self):
        dlg = EmployeeForm(self.root, "Add Employee")
        if dlg.result:
            data = dlg.result
            etype = data.get("emp_type", "Employee")
            if not data['Employee ID']:
                messagebox.showerror("Error", "Employee ID is required.")
                return
            if etype == "Supervisor":
                new_emp = Supervisor(
                    employee_id=data['Employee ID'],
                    name_first=data['First Name'],
                    name_last=data['Last Name'],
                    hire_date=data['Hire Date'],
                    birthdate=data['Birthdate'],
                    status=data['Status'],
                    employee_type=etype,
                    reports_to_id=int(data['Reports To ID']) if data['Reports To ID'] else None,
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
                    reports_to_id=int(data['Reports To ID']) if data['Reports To ID'] else None,
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
                    reports_to_id=int(data['Reports To ID']) if data['Reports To ID'] else None
                )
            session.add(new_emp)
            try:
                session.commit()
                self.refresh_employee_list()
            except Exception as e:
                session.rollback()
                messagebox.showerror("Error", f"Could not add employee: {e}")

    def edit_employee(self):
        emp_id = self.get_selected_employee_id()
        if emp_id is None:
            messagebox.showwarning("Select Employee", "Please select an employee to edit.")
            return
        emp = session.get(Employee, emp_id)
        dlg = EmployeeForm(self.root, "Edit Employee", employee=emp)
        if dlg.result:
            data = dlg.result
            # For simplicity, do not change the class/subclass on edit
            emp.employee_id = data['Employee ID']
            emp.name_first = data['First Name']
            emp.name_last = data['Last Name']
            emp.hire_date = data['Hire Date']
            emp.birthdate = data['Birthdate']
            emp.status = data['Status']
            emp.employee_type = data['emp_type']
            emp.reports_to_id = int(data['Reports To ID']) if data['Reports To ID'] else None
            if isinstance(emp, Supervisor):
                emp.management_level = int(data.get("management_level") or 0)
            elif isinstance(emp, MaintenancePerson):
                emp.maintenance_level = data.get("maintenance_level")
                emp.qualified_area = data.get("qualified_area")
            try:
                session.commit()
                self.refresh_employee_list()
            except Exception as e:
                session.rollback()
                messagebox.showerror("Error", f"Could not update employee: {e}")

    def delete_employee(self):
        emp_id = self.get_selected_employee_id()
        if emp_id is None:
            messagebox.showwarning("Select Employee", "Please select an employee to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected employee?"):
            return
        emp = session.get(Employee, emp_id)
        session.delete(emp)
        try:
            session.commit()
            self.refresh_employee_list()
        except Exception as e:
            session.rollback()
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
        Initialize the Competency Assignment Form Tab.

        This form supports both 'Proficiency' (Basic, Intermediate, Advanced)
        and 'Level' (Level 1, Level 2, etc.) fields as optional values.
        """
        super().__init__(parent)
        self.session = session
        self.current_checklist_task = None

        # Optionally initialize the dynamic vars (for later assignment in each section)
        self.proficiency_var = None  # Will be created per-section in dynamic form
        self.level_var = None  # Will be created per-section in dynamic form

        # Main container with scrollable frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Title
        title_label = ttk.Label(main_frame, text="Competency Assignment Form",
                                font=('TkDefaultFont', 14, 'bold'))
        title_label.pack(anchor='w', pady=(0, 15))

        # Section 1: Checklist Task Selection
        self.create_checklist_section(main_frame)

        # Section 2: Competency Type Selection
        self.create_competency_type_section(main_frame)

        # Section 3: Dynamic competency details (will be populated based on selection)
        self.create_dynamic_section(main_frame)

        # Section 4: Task Definition
        self.create_task_section(main_frame)

        # Section 5: Action buttons
        self.create_action_buttons(main_frame)

        # Initialize form fields and dropdowns
        self.reset_form()
        self.populate_checklist_dropdowns()

    def create_checklist_section(self, parent):
        # Checklist Task Selection
        checklist_frame = ttk.LabelFrame(parent, text="1. Select or Create Checklist Task", padding=10)
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

        # Task Action
        ttk.Label(task_frame, text="Task Action:").grid(row=1, column=0, sticky='e', padx=(0, 5))
        self.task_action_var = tk.StringVar()
        self.task_action_combo = ttk.Combobox(task_frame, textvariable=self.task_action_var,
                                              values=["Rebuild", "Install", "Remove", "Inspect",
                                                      "Repair", "Test", "Calibrate", "Operate",
                                                      "Maintain", "Clean", "Lubricate"],
                                              width=20)
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
        """Handle task selection and auto-fill task object"""
        task_index = self.task_combo.current()
        if task_index == -1:
            self.current_checklist_task = None
            return

        try:
            task_id = self.task_choices[task_index][0]
            self.current_checklist_task = self.session.query(ChecklistTask).get(task_id)

            # Auto-populate task object from checklist task description
            # This is a simple heuristic - you might want to make this smarter
            task_desc = self.current_checklist_task.task_description
            # Try to extract object from task description
            # e.g., "Rebuild Solution Pump" -> "Solution Pump"
            words = task_desc.split()
            if len(words) >= 2:
                potential_object = " ".join(words[1:])  # Everything after first word
                self.task_object_var.set(potential_object)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to load task details: {e}")

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
        self.proficiency_combo.set("Tier")

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
        self.elec_proficiency_combo.set("Tier")

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
        self.tool_proficiency_combo.set("Tier")

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
        self.oper_proficiency_combo.set("Tier")

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
        """Save the competency assignment"""
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

        try:
            comp_type = self.competency_type_var.get()

            # Create the appropriate skill and task based on competency type
            if comp_type == "mechanical":
                self.create_mechanical_assignment()
            elif comp_type == "electrical":
                self.create_electrical_assignment()
            elif comp_type == "tools":
                self.create_tools_assignment()
            elif comp_type == "operational":
                self.create_operational_assignment()
            elif comp_type == "safety":
                self.create_safety_assignment()
            elif comp_type == "training":
                self.create_training_assignment()
            elif comp_type == "communication":
                self.create_communication_assignment()
            elif comp_type == "leadership":
                self.create_leadership_assignment()
            else:
                messagebox.showinfo("Not Implemented", f"{comp_type} competency type not yet implemented.")
                return

            messagebox.showinfo("Success", "Competency assignment saved successfully!")
            self.reset_form()

        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to save assignment: {e}")

    def create_mechanical_assignment(self):
        """Create mechanical skill and task assignment with proper linking"""
        widgets = self.dynamic_widgets['mechanical']
        custom_name = self.get_current_competency_name()

        # Normalize all fields
        sub_category = normalize_str(widgets['subcategory'].get())
        equipment_category = normalize_str(widgets['equipment'].get())
        level_value = normalize_str(widgets.get('level', tk.StringVar()).get())
        proficiency_value = normalize_str(widgets.get('proficiency', tk.StringVar()).get())
        custom_name = normalize_str(custom_name)

        try:
            skill_data = {
                'competency_name': custom_name,
                'description': f"{sub_category} maintenance and repair",
                'skill_category': 'Mechanical',
                'competency_type': 'mechanical',
                'sub_category': sub_category,
                # REMOVED: 'mechanical_type': sub_category.split()[0] if sub_category else None,
                'equipment_category': equipment_category,
                'level': level_value,
                'proficiency_level': proficiency_value
            }

            # Use all fields for uniqueness
            existing_skill = self.session.query(MechanicalSkill).filter_by(
                sub_category=sub_category,
                equipment_category=equipment_category,
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
                skill = MechanicalSkill(**skill_data)
                self.session.add(skill)
                self.session.flush()

            # Step 2: Create the specific MechanicalTask
            task_data = {
                'competency_name': custom_name,
                'description': f"{self.task_action_var.get()} {self.task_object_var.get()}",
                'skill_category': 'Mechanical',
                'competency_type': 'mechanical_task',
                'sub_category': skill.sub_category,
                # REMOVED: 'mechanical_type': skill.mechanical_type,
                'equipment_category': skill.equipment_category,
                'task_action': self.task_action_var.get(),
                'task_object': self.task_object_var.get(),
                'verification_method': self.verification_text.get('1.0', tk.END).strip()
            }

            task = MechanicalTask(**task_data)
            self.session.add(task)
            self.session.flush()

            # Step 3: Link checklist task to base competency
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

            # Step 4: Link to specific task implementation
            task_assignment = TaskSkillAssignment(
                checklist_task_id=self.current_checklist_task.id,
                mechanical_task_id=task.id
            )
            self.session.add(task_assignment)

            self.session.commit()

            print(f"✅ Created mechanical competency assignment:")
            print(f"   - Base Competency: {skill.competency_name} (ID: {skill.id})")
            print(f"   - Level: {skill.level}")
            print(f"   - Proficiency Level: {skill.proficiency_level}")
            print(f"   - Specific Task: {task.task_action} {task.task_object} (ID: {task.id})")
            print(f"   - Linked to Checklist Task: {self.current_checklist_task.task_description}")

        except Exception as e:
            self.session.rollback()
            raise e

    def create_electrical_assignment(self):
        """Create electrical skill and task assignment with proper linking"""
        widgets = self.dynamic_widgets['electrical']
        custom_name = self.get_current_competency_name()

        try:
            skill_data = {
                'competency_name': custom_name,
                'description': f"{widgets['subcategory'].get()} installation and maintenance",
                'skill_category': 'Electrical',
                'competency_type': 'electrical',
                'sub_category': widgets['subcategory'].get(),
                'voltage_level': widgets['voltage'].get(),
                # REMOVED: 'electrical_type': widgets['subcategory'].get().split()[0],
                'level': widgets['level'].get() or None,
                'proficiency_level': widgets.get('proficiency', tk.StringVar()).get() or None
            }

            # Find by ALL unique fields (removed electrical_type from filter)
            existing_skill = self.session.query(ElectricalSkill).filter_by(
                sub_category=skill_data['sub_category'],
                voltage_level=skill_data['voltage_level'],
                # REMOVED: electrical_type=skill_data['electrical_type'],
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

            # Step 2: Create the specific ElectricalTask
            task_data = {
                'competency_name': custom_name,
                'description': f"{self.task_action_var.get()} {self.task_object_var.get()}",
                'skill_category': 'Electrical',
                'competency_type': 'electrical_task',
                'sub_category': skill.sub_category,
                'voltage_level': skill.voltage_level,
                # REMOVED: 'electrical_type': skill.electrical_type,
                'task_action': self.task_action_var.get(),
                'task_object': self.task_object_var.get(),
                'verification_method': self.verification_text.get('1.0', tk.END).strip()
            }
            task = ElectricalTask(**task_data)
            self.session.add(task)
            self.session.flush()

            # Step 3: Link checklist task to base competency
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

            # Step 4: Link to specific task implementation
            task_assignment = TaskSkillAssignment(
                checklist_task_id=self.current_checklist_task.id,
                electrical_task_id=task.id
            )
            self.session.add(task_assignment)
            self.session.commit()

            print(f"✅ Created electrical competency assignment:")
            print(f"   - Base Competency: {skill.competency_name} (ID: {skill.id})")
            print(f"   - Level: {skill.level}")
            print(f"   - Proficiency Level: {skill.proficiency_level}")
            print(f"   - Specific Task: {task.task_action} {task.task_object} (ID: {task.id})")
            print(f"   - Linked to Checklist Task: {self.current_checklist_task.task_description}")

        except Exception as e:
            self.session.rollback()
            raise e

    def create_tools_assignment(self):
        """Create tools skill and task assignment with proper linking"""
        widgets = self.dynamic_widgets['tools']
        custom_name = self.get_current_competency_name()

        # Get both level and proficiency values
        level_value = widgets.get('level', tk.StringVar()).get().strip() or None
        proficiency_value = widgets.get('proficiency', tk.StringVar()).get().strip() or None

        try:
            skill_data = {
                'competency_name': custom_name,
                'description': f"{widgets['tool_type'].get()} usage and maintenance",
                'skill_category': 'Tools',
                'competency_type': 'tools',
                'tool_type': widgets['tool_type'].get(),
                'primary_application': widgets['application'].get(),
                'level': level_value,
                'proficiency_level': proficiency_value
            }

            # Find by ALL unique fields
            existing_skill = self.session.query(ToolSkill).filter_by(
                tool_type=skill_data['tool_type'],
                primary_application=skill_data['primary_application'],
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
                skill = ToolSkill(**skill_data)
                self.session.add(skill)
                self.session.flush()

            # Step 2: Create the specific ToolTask
            task_data = {
                'competency_name': custom_name,
                'description': f"{self.task_action_var.get()} {self.task_object_var.get()}",
                'skill_category': 'Tools',
                'competency_type': 'tool_task',
                'tool_type': skill.tool_type,
                'primary_application': skill.primary_application,
                'task_action': self.task_action_var.get(),
                'task_object': self.task_object_var.get(),
                'verification_method': self.verification_text.get('1.0', tk.END).strip()
            }
            task = ToolTask(**task_data)
            self.session.add(task)
            self.session.flush()

            # Step 3: Link checklist task to base competency
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

            # Step 4: Link to specific task implementation
            task_assignment = TaskSkillAssignment(
                checklist_task_id=self.current_checklist_task.id,
                tool_task_id=task.id
            )
            self.session.add(task_assignment)
            self.session.commit()

            print(f"✅ Created tools competency assignment:")
            print(f"   - Base Competency: {skill.competency_name} (ID: {skill.id})")
            print(f"   - Level: {skill.level}")
            print(f"   - Proficiency Level: {skill.proficiency_level}")
            print(f"   - Specific Task: {task.task_action} {task.task_object} (ID: {task.id})")
            print(f"   - Linked to Checklist Task: {self.current_checklist_task.task_description}")

        except Exception as e:
            self.session.rollback()
            raise e

    def create_operational_assignment(self):
        """Create operational skill and task assignment with proper linking"""
        widgets = self.dynamic_widgets['operational']
        custom_name = widgets['competency_name'].get().strip()

        # Get both level and proficiency values
        level_value = widgets.get('level', tk.StringVar()).get().strip() or None
        proficiency_value = widgets.get('proficiency', tk.StringVar()).get().strip() or None

        try:
            # Step 1: Create or find the base OperationalSkill (competency)
            skill_data = {
                'competency_name': custom_name,
                'description': f"{widgets['operation_type'].get()} operation of {widgets['machine_type'].get()}",
                'competency_type': 'operational',
                'operation_type': widgets['operation_type'].get().strip(),
                'machine_type': widgets['machine_type'].get().strip(),
                'level': level_value,
                'proficiency_level': proficiency_value
            }
            print("SAVING SKILL DATA:", skill_data)  # Debug output

            # DUPLICATE CHECK: All attributes that make a skill unique
            existing_skill = self.session.query(OperationalSkill).filter_by(
                operation_type=skill_data['operation_type'],
                machine_type=skill_data['machine_type'],
                level=skill_data['level'],
                proficiency_level=skill_data['proficiency_level']
            ).first()

            if existing_skill:
                skill = existing_skill
                skill.competency_name = custom_name
                skill.description = skill_data['description']
                skill.level = level_value
                skill.proficiency_level = proficiency_value
            else:
                skill = OperationalSkill(**skill_data)
                self.session.add(skill)
                self.session.flush()  # Get the ID

            # Step 2: Create the specific OperationalTask (does NOT have level/proficiency)
            task_data = {
                'competency_name': custom_name,
                'description': f"{self.task_action_var.get()} {self.task_object_var.get()}",
                'competency_type': 'operational_task',
                'operation_type': skill.operation_type,
                'machine_type': skill.machine_type,
                'task_action': self.task_action_var.get(),
                'task_object': self.task_object_var.get(),
                'verification_method': self.verification_text.get('1.0', tk.END).strip()
            }
            task = OperationalTask(**task_data)
            self.session.add(task)
            self.session.flush()  # Get the ID

            # Step 3: Link checklist task to the base competency (ChecklistTaskCompetency)
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

            # Step 4: Link to specific task implementation (TaskSkillAssignment)
            task_assignment = TaskSkillAssignment(
                checklist_task_id=self.current_checklist_task.id,
                operational_task_id=task.id
            )
            self.session.add(task_assignment)

            # Commit all changes
            self.session.commit()

            print(f"✅ Created operational competency assignment:")
            print(f"   - Base Competency: {skill.competency_name} (ID: {skill.id})")
            print(f"   - Level: {skill.level}")
            print(f"   - Proficiency Level: {skill.proficiency_level}")
            print(f"   - Specific Task: {task.task_action} {task.task_object} (ID: {task.id})")
            print(f"   - Linked to Checklist Task: {self.current_checklist_task.task_description}")

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

        # Clear dynamic section
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()
        self.dynamic_widgets.clear()

        # Clear preview
        self.preview_text.config(state='normal')
        self.preview_text.delete('1.0', tk.END)
        self.preview_text.config(state='disabled')

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
        self.safety_proficiency_combo.set("Tier")

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

    def create_safety_assignment(self):
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
        self.training_proficiency_combo.set("Tier")

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
        self.comm_proficiency_combo.set("Tier")

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
        self.lead_proficiency_combo.set("Tier")

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

    def create_training_assignment(self):
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

    def create_communication_assignment(self):
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

    def create_leadership_assignment(self):
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

class StepUpEvalTab(ttk.Frame):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session

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

    def create_form(self):
        # --- Employee ---
        ttk.Label(self.scrollable_frame, text="Employee").grid(row=0, column=0, sticky="w", padx=5, pady=(5, 0))
        self.employee_var = tk.StringVar()
        self.employee_combo = ttk.Combobox(self.scrollable_frame, textvariable=self.employee_var, state="readonly")
        self.employee_combo.grid(row=1, column=0, padx=5, pady=(0, 5), sticky="ew")
        self.load_employees()
        self.employee_combo.bind("<<ComboboxSelected>>", self.on_employee_selected)

        # --- Level ---
        ttk.Label(self.scrollable_frame, text="Level").grid(row=2, column=0, sticky="w", padx=5, pady=(5, 0))
        self.level_var = tk.StringVar()
        self.level_combo = ttk.Combobox(
            self.scrollable_frame, textvariable=self.level_var,
            values=["Level 1", "Level 2", "Level 3", "Maintenance Tech", "Operator"], state="readonly"
        )
        self.level_combo.grid(row=3, column=0, padx=5, pady=(0, 5), sticky="ew")
        self.level_combo.set("Level 1")

        # --- Assign All Tasks for Level Button ---
        ttk.Button(self.scrollable_frame, text="Assign All Tasks For This Level", command=self.assign_all_level_tasks) \
            .grid(row=3, column=1, padx=20, pady=(0, 5), sticky="w")

        # --- Status ---
        ttk.Label(self.scrollable_frame, text="Status").grid(row=4, column=0, sticky="w", padx=5, pady=(5, 0))
        self.status_var = tk.StringVar()
        self.status_combo = ttk.Combobox(self.scrollable_frame, textvariable=self.status_var,
                                         values=["Active", "Expired", "Needs Renewal"], state="readonly")
        self.status_combo.grid(row=5, column=0, padx=5, pady=(0, 5), sticky="ew")
        self.status_combo.set("Active")

        # --- Date Achieved ---
        ttk.Label(self.scrollable_frame, text="Date Achieved").grid(row=6, column=0, sticky="w", padx=5, pady=(5, 0))
        self.date_entry = ttk.Entry(self.scrollable_frame)
        self.date_entry.grid(row=7, column=0, padx=5, pady=(0, 5), sticky="ew")

        # --- Assessed By (Assessor) ---
        ttk.Label(self.scrollable_frame, text="Assessed By").grid(row=8, column=0, sticky="w", padx=5, pady=(5, 0))
        self.assessor_var = tk.StringVar()
        self.assessor_combo = ttk.Combobox(self.scrollable_frame, textvariable=self.assessor_var, state="readonly")
        self.assessor_combo.grid(row=9, column=0, padx=5, pady=(0, 5), sticky="ew")
        self.load_assessors()

        # --- Notes ---
        ttk.Label(self.scrollable_frame, text="Notes").grid(row=10, column=0, sticky="w", padx=5, pady=(5, 0))
        self.notes_text = tk.Text(self.scrollable_frame, height=3)
        self.notes_text.grid(row=11, column=0, columnspan=2, padx=5, pady=(0, 15), sticky="ew")

        # --- Saved Evals Display ---
        ttk.Label(self.scrollable_frame, text="Employee Competency Records", font=('TkDefaultFont', 10, 'bold')).grid(
            row=12, column=0, sticky="w", padx=5, pady=(10, 5)
        )

        # Create frame for treeview and its scrollbar
        tree_frame = ttk.Frame(self.scrollable_frame)
        tree_frame.grid(row=13, column=0, columnspan=2, padx=5, pady=(0, 10), sticky="nsew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        columns = ["type", "task", "tier", "level", "proficiency","status", "date", "assessor", "completed"]
        self.eval_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)
        for col in columns:
            self.eval_tree.heading(col, text=col.title(), command=lambda c=col: self.sort_treeview(c, False))
            self.eval_tree.column(col, width=100, minwidth=80)

        # Add horizontal and vertical scrollbars for treeview
        tree_v_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.eval_tree.yview)
        tree_h_scrollbar = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.eval_tree.xview)
        self.eval_tree.configure(yscrollcommand=tree_v_scrollbar.set, xscrollcommand=tree_h_scrollbar.set)

        # Grid the treeview and scrollbars
        self.eval_tree.grid(row=0, column=0, sticky="nsew")
        tree_v_scrollbar.grid(row=0, column=1, sticky="ns")
        tree_h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.eval_tree.bind('<Double-1>', self.on_treeview_double_click)

        # --- Completion Breakdown Display ---
        self.breakdown_var = tk.StringVar()
        self.breakdown_label = ttk.Label(self.scrollable_frame, textvariable=self.breakdown_var,
                                         font=('TkDefaultFont', 9, 'bold'), foreground='blue', wraplength=800)
        self.breakdown_label.grid(row=14, column=0, columnspan=2, sticky='ew', padx=10, pady=5)

        # Configure row weights for proper expansion
        self.scrollable_frame.grid_rowconfigure(13, weight=1)  # Make treeview row expandable

        self.refresh_eval_list()

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
                proficiency_achieved=None,  # Remove proficiency reference
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

    def refresh_eval_list(self):
        # Clear all rows
        for row in self.eval_tree.get_children():
            self.eval_tree.delete(row)
        emp_id = self.get_selected(self.employee_combo, self.employee_choices)
        if not emp_id:
            self.breakdown_var.set("")
            return
        # Show only this employee's records, and set the DB id as iid
        evals = self.session.query(EmployeeCompetency).filter_by(employee_id=emp_id).all()
        for rec in evals:
            comp = self.session.query(CoreCompetency).get(rec.competency_id)
            assessor = self.session.query(Employee).get(rec.assessed_by) if rec.assessed_by else None
            checklist_task = self.session.query(ChecklistTask).filter(
                ChecklistTask.required_competencies.any(id=rec.competency_id)
            ).first()
            is_completed = (
                    rec.status == "Active"
                    and rec.date_achieved
                    and rec.date_achieved.strip() != ""
            )
            completed_text = "Yes" if is_completed else "No"
            self.eval_tree.insert(
                '', 'end',
                iid=str(rec.id),  # Store DB PK as iid
                values=(
                    comp.competency_type if comp else "",
                    checklist_task.task_description if checklist_task else "",
                    (comp.proficiency_level.split('_')[-1] if comp and comp.proficiency_level else ""),
                    # Extract A, B, or C
                    rec.proficiency_achieved,
                    rec.level_achieved,
                    rec.status,
                    rec.date_achieved,
                    f"{assessor.employee_id}" if assessor else "",
                    completed_text
                )

            )
        # Show breakdown
        breakdown = self.get_completion_breakdown()
        if breakdown:
            summary_lines = [f"{ctype}: {completed}/{total} completed"
                             for ctype, (total, completed) in breakdown.items()]
            self.breakdown_var.set(" | ".join(summary_lines))
        else:
            self.breakdown_var.set("No records for this employee.")

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
            self.session.commit()
            self.refresh_eval_list()  # Always refresh so "Completed" column is recalculated
        except Exception as e:
            self.session.rollback()
            messagebox.showerror("Error", f"Failed to save edit: {e}")

    def sort_treeview(self, col, reverse):
        data_list = [(self.eval_tree.set(k, col), k) for k in self.eval_tree.get_children("")]
        try:
            data_list.sort(key=lambda t: float(t[0]) if t[0].replace('.', '', 1).isdigit() else t[0], reverse=reverse)
        except Exception:
            data_list.sort(reverse=reverse)
        for idx, (val, k) in enumerate(data_list):
            self.eval_tree.move(k, '', idx)
        self.eval_tree.heading(col, command=lambda: self.sort_treeview(col, not reverse))

    def on_treeview_double_click(self, event):
        item_id = self.eval_tree.identify_row(event.y)
        column = self.eval_tree.identify_column(event.x)
        if not item_id or column == '#0':
            return

        col_index = int(column.replace('#', '')) - 1
        columns = ["type", "task", "tier",  "level","proficiency", "status", "date", "assessor", "completed"]

        field = columns[col_index]
        if field == 'completed':
            return  # Completed column is not editable

        cur_value = self.eval_tree.set(item_id, field)
        x, y, width, height = self.eval_tree.bbox(item_id, column)
        entry_popup = tk.Entry(self.eval_tree)
        entry_popup.insert(0, cur_value)
        entry_popup.place(x=x, y=y, width=width, height=height)

        def save_edit(event):
            new_value = entry_popup.get()
            self.eval_tree.set(item_id, field, new_value)
            entry_popup.destroy()
            self.save_treeview_edit(item_id, field, new_value)

        entry_popup.bind('<Return>', save_edit)
        entry_popup.bind('<FocusOut>', lambda e: entry_popup.destroy())
        entry_popup.focus_set()


if __name__ == "__main__":
    root = tk.Tk()
    app = EmployeeViewerApp(root)
    root.mainloop()
