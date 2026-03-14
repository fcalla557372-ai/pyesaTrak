# ManageUsersController.py — Archive instead of Delete
from ManageUsersModel import ManageUsersModel
from ManageUsersView import ManageUsersView, UserFormDialog
from PyQt6.QtWidgets import QMessageBox


class ManageUsersController:
    def __init__(self, user_data=None):
        self.model = ManageUsersModel()
        self.view = ManageUsersView()
        self.user_data = user_data

        self.view.search_input.textChanged.connect(self.refresh_data)
        self.view.role_combo.currentTextChanged.connect(self.refresh_data)
        self.view.status_combo.currentTextChanged.connect(self.refresh_data)

        self.view.add_user_clicked.connect(self.handle_add_user)
        self.view.edit_user_clicked.connect(self.handle_edit_user)
        self.view.archive_user_clicked.connect(self.handle_archive_user)
        # delete_user_clicked kept for compat — wire to archive too
        self.view.delete_user_clicked.connect(self.handle_archive_user)

    def refresh_data(self):
        search = self.view.search_input.text()
        role   = self.view.role_combo.currentText()
        status = self.view.status_combo.currentText()
        if "All" in role:   role   = "All"
        if "All" in status: status = "All"
        users = self.model.get_users(role, status, search)
        self.view.load_data(users)

    def handle_add_user(self):
        dialog = UserFormDialog(self.view)        # add mode — role locked to Staff
        if dialog.exec():
            data = dialog.get_data()
            if not data['username'] or not data['password']:
                QMessageBox.warning(self.view, "Error", "Username and Password are required!")
                return
            # Enforce: only Staff can be added through this dialog
            data['role'] = 'Staff'
            if self.model.add_user(data):
                QMessageBox.information(self.view, "Success", "User added successfully!")
                self.refresh_data()
            else:
                QMessageBox.critical(self.view, "Error", "Failed to add user. Username might already be taken.")

    def handle_edit_user(self, uid):
        user = self.model.get_user_by_id(uid)
        if not user:
            QMessageBox.warning(self.view, "Error", "User not found.")
            return
        dialog = UserFormDialog(self.view, user)   # edit mode — role is read-only label
        if dialog.exec():
            data = dialog.get_data()
            # Never allow role change via edit — preserve original role
            data['role'] = user.get('role', 'Staff')
            if not data['password']:
                del data['password']
            if self.model.update_user(uid, data):
                QMessageBox.information(self.view, "Success", "User updated successfully!")
                self.refresh_data()
            else:
                QMessageBox.critical(self.view, "Error", "Failed to update user.")

    def handle_archive_user(self, uid):
        """Toggle user status between Active ↔ Inactive (archive/unarchive)."""
        if self.user_data and uid == self.user_data.get('user_id'):
            QMessageBox.warning(self.view, "Error", "You cannot archive your own account!")
            return

        user = self.model.get_user_by_id(uid)
        if not user:
            QMessageBox.warning(self.view, "Error", "User not found.")
            return

        is_active = user.get('status') == 'Active'
        action    = "archive" if is_active else "unarchive"
        new_status = "Inactive" if is_active else "Active"

        reply = QMessageBox.question(
            self.view, f"Confirm {action.capitalize()}",
            f"Are you sure you want to {action} this user?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.model.update_user(uid, {'status': new_status}):
                QMessageBox.information(self.view, "Success", f"User {action}d successfully.")
                self.refresh_data()
            else:
                QMessageBox.critical(self.view, "Error", f"Failed to {action} user.")