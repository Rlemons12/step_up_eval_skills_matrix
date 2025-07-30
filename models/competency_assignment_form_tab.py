import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_main import Employee, MaintenancePerson, Supervisor, TechnicalSkill, MechanicalSkill, ElectricalSkill, \
    ToolSkill, TrainingCompetency, CommunicationCompetency, LeadershipCompetency
from db_main import( CoreCompetency,  AreaChecklist, ChecklistSection, ChecklistTask, OperationalTask,OperationalSkill,MechanicalTask,
                     ElectricalTask, ToolTask, TaskSkillAssignment, ChecklistTaskCompetency, EmployeeCompetency)
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import filedialog
import csv

def normalize_str(val):
    """Ensure blank or whitespace string is always stored as None, and trims spaces."""
    if val is None:
        return None
    val = str(val).strip()
    return val if val else None

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
        self.selected_assignment_id = None
        self.selected_assignment_type = None
        self.setup_editing_indicators()


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

        # -- Section: Current Task Details
        self.create_current_task_details_section(main_frame)
        self.task_details_tree.bind('<<TreeviewSelect>>', self.on_task_details_row_selected)
        self.task_details_tree.bind('<Double-1>', self.on_task_details_tree_double_click)

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