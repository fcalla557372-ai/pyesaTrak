# controller/ManageUsersController.py
# MVC LAYER: CONTROLLER
# Responsibilities: handle user actions, call Model, instruct View.
# Must NOT import PyQt6 widgets directly or call QMessageBox.

from model.ManageUsersModel import ManageUsersModel          # ← fixed package import
from view.ManageUsersView import ManageUsersView, UserFormDialog  # ← fixed package import


class ManageUsersController:
    """
    Mediates between ManageUsersModel and ManageUsersView.
    - Calls model CRUD methods in response to view signals.
    - Passes data or status messages to the view for display.
    - No raw SQL, no PyQt widget construction, no QMessageBox here.
    """

    def __init__(self, user_data=None):
        self.model     = ManageUsersModel()
        self.view      = ManageUsersView()
        self.user_data = user_data

        # Filter signals → refresh table
        self.view.search_input.textChanged.connect(self.refresh_data)
        self.view.role_combo.currentTextChanged.connect(self.refresh_data)
        self.view.status_combo.currentTextChanged.connect(self.refresh_data)

        # Action signals → handlers
        self.view.add_user_clicked.connect(self.handle_add_user)
        self.view.edit_user_clicked.connect(self.handle_edit_user)
        self.view.archive_user_clicked.connect(self.handle_archive_user)
        self.view.delete_user_clicked.connect(self.handle_archive_user)   # alias

    # ── READ ──────────────────────────────────────────────────────────────────

    def refresh_data(self):
        search = self.view.search_input.text()
        role   = self.view.role_combo.currentText()
        status = self.view.status_combo.currentText()
        role   = "All" if "All" in role   else role
        status = "All" if "All" in status else status
        users  = self.model.get_users(role, status, search)
        self.view.load_data(users)

    # ── CREATE ────────────────────────────────────────────────────────────────

    def handle_add_user(self):
        dialog = UserFormDialog(self.view)   # add mode — role locked to Staff in dialog
        if not dialog.exec():
            return

        data = dialog.get_data()

        if not data['username'] or not data['password']:
            self.view.show_message("Error", "Username and Password are required!", "warning")
            return

        # Business rule: only Staff accounts may be created through this UI
        data['role'] = 'Staff'

        if self.model.add_user(data):
            self.view.show_message("Success", "User added successfully!", "info")
            self.refresh_data()
        else:
            self.view.show_message(
                "Error",
                "Failed to add user. Username might already be taken.",
                "critical")

    # ── UPDATE ────────────────────────────────────────────────────────────────

    def handle_edit_user(self, uid: int):
        user = self.model.get_user_by_id(uid)
        if not user:
            self.view.show_message("Error", "User not found.", "warning")
            return

        dialog = UserFormDialog(self.view, user)   # edit mode — role is read-only label
        if not dialog.exec():
            return

        data = dialog.get_data()
        data['role'] = user.get('role', 'Staff')   # role is immutable after creation

        if not data.get('password'):
            data.pop('password', None)   # don't overwrite if left blank

        if self.model.update_user(uid, data):
            self.view.show_message("Success", "User updated successfully!", "info")
            self.refresh_data()
        else:
            self.view.show_message("Error", "Failed to update user.", "critical")

    # ── ARCHIVE / UNARCHIVE ───────────────────────────────────────────────────

    def handle_archive_user(self, uid: int):
        """Toggle Active ↔ Inactive. View handles the confirmation dialog."""
        if self.user_data and uid == self.user_data.get('user_id'):
            self.view.show_message(
                "Error", "You cannot archive your own account!", "warning")
            return

        user = self.model.get_user_by_id(uid)
        if not user:
            self.view.show_message("Error", "User not found.", "warning")
            return

        is_active  = user.get('status') == 'Active'
        action     = "archive" if is_active else "unarchive"
        new_status = "Inactive" if is_active else "Active"

        # View owns the confirmation dialog — controller only reads the result
        confirmed = self.view.confirm_action(
            f"Confirm {action.capitalize()}",
            f"Are you sure you want to {action} this user?")

        if not confirmed:
            return

        if self.model.update_user(uid, {'status': new_status}):
            self.view.show_message("Success", f"User {action}d successfully.", "info")
            self.refresh_data()
        else:
            self.view.show_message("Error", f"Failed to {action} user.", "critical")