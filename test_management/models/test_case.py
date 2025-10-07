from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime


class TestCase(models.Model):
    """
    Test Case Model
    This model represents a test case in the system. It includes fields for tracking the test case's lifecycle,
    such as its state, priority, and execution details. It also integrates with Odoo's messaging system to
    notify users about changes in the test case's status.
    """
    _name = 'test.case'
    _description='Test Case'
    _inherit = ['mail.thread.main.attachment', 'mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'ref desc'

    # ==========================
    # Fields
    # ==========================

    # Identification Fields
    ref = fields.Char(
        string='REF',
        copy=False,
        required=True,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('test.case'),
        help="Unique reference number for the test case."
    )
    name = fields.Char(
        string='Title',
        required=True,
        help="Title of the test case."
    )

    # State and Priority
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('ready', 'Under Review'),
            ('approved', 'Approved'),
            ('running', 'Running'),
            ('failed', 'Failed'),
            ('passed', 'Passed'),
            ('blocked', 'Blocked'),
            ('executed', 'Executed'),
        ],
        string='State',
        default='draft',
        copy=False,
        required=True,
        tracking=True,
        help="Current state of the test case."
    )
    priority = fields.Selection(
        selection=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical')
        ],
        string='Priority',
        default='medium',
        required=True,
        help="Priority level of the test case."
    )

    # Relationships
    assigned_to = fields.Many2one(
        'res.users',
        string='Assigned To',
        help="User responsible for executing the test case."
    )
    create_uid = fields.Many2one(
        'res.users',
        string='Created By',
        readonly=True,
        help="User who created the test case."
    )
    reviewed_by = fields.Many2one(
        'res.users',
        string='Reviewed By',
        help="User who reviewed and approved the test case."
    )
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        help="Project associated with the test case."
    )
    component_id = fields.Many2one(
        'component',
        string='Component/Module',
        help="Component to which this test case belongs."
    )

    test_run_ids = fields.Many2many(
        'test.run',
        string='Test Runs',
        help="Test runs associated with this test case."
    )

    # Dates
    create_date = fields.Datetime(
        string='Created On',
        readonly=True,
        help="Date and time when the test case was created."
    )
    review_date = fields.Datetime(
        string='Review Date',
        help="Date and time when the test case was reviewed."
    )
    execution_date = fields.Datetime(
        string='Execution Date',
        help="Date and time when the test case was executed."
    )

    # Descriptive Fields
    description = fields.Html(
        string='Description',
        help="Detailed description of the test case."
    )
    pre_action = fields.Html(
        string='Pre-conditions',
        help="Pre-conditions that must be met before executing the test case."
    )
    post_action = fields.Html(
        string='Post-conditions',
        help="Post-conditions to verify after executing the test case."
    )
    test_data = fields.Text(
        string='Test Data',
        help="Data required to execute the test case."
    )
    environment = fields.Text(
        string='Environment',
        help="Environment details required for executing the test case."
    )
    test_case_steps = fields.One2many('test.case.steps','test_case_id')
    active = fields.Boolean('Active', default=True)
    run_count= fields.Integer(compute="_get_related_run_count")


    # Computed Fields
    bug_count = fields.Integer(
        string='Bugs',
        help="Number of bugs associated with the test case.",
        compute="_get_related_bug_count"
    )



    @api.depends('ref', 'name')
    def _compute_display_name(self):
        for record in self:
            if record.name:
                record.display_name = f"[{record.ref}] {record.name}"
            else:
                record.display_name = record.ref

    def write(self, vals):
        """
        Overrides the `write` method to add custom behavior when updating a record.

        This method checks if the `assigned_to` field is being updated. If so, it schedules
        an activity notification to the newly assigned user, informing them of the assignment.

        Args:
            vals (dict): A dictionary of field-value pairs to update on the record(s).
                         Keys are field names, and values are the new values to set.

        Returns:
            bool: True if the write operation is successful, otherwise False.
        """
        # Check if 'assigned_to' is in vals (i.e., if the assigned user is being updated)
        if 'assigned_to' in vals:
            # Schedule an activity for the newly assigned user
            self.activity_schedule(
                'test_management.mail_activity_assignment',  # Activity type XML ID
                user_id=vals['assigned_to'],  # ID of the user being assigned
                summary=_('New Assignment: Test Case %(ref)s has been assigned to you.', ref=self.ref)
            )

         #   Call the superclass's write method to perform the standard write operation
        return super(TestCase, self).write(vals)

    def unlink(self):
        """
        Override the unlink method to prevent deletion of test case that are not in the 'draft' state.
        Raises:
            UserError: If any test case is not in the 'draft' state.
        Returns:
            bool: True if the deletion is successful.
        """
        for record in self:
            # Check if the record is not in draft state
            if record.state != 'draft':
                raise UserError(
                    _("You cannot delete a test case that is not in draft state. Please archive it instead.")
                )
        # Call the super method to perform the actual deletion
        return super(TestCase, self).unlink()

    def _get_related_bug_count(self):
        test_bug_data = self.env['test.bug'].read_group(
            domain=[('test_case_id', 'in', self.ids)],
            fields=['test_case_id'],
            groupby=['test_case_id']
        )
        test_bug_count_dict = {data['test_case_id'][0]: data['test_case_id_count'] for data in test_bug_data}
        for test_bug in self:
            test_bug.bug_count = test_bug_count_dict.get(test_bug.id, 0)

    def _get_related_run_count(self):
        test_run_data = self.env['test.run'].read_group(
            domain=[('test_case_r_id', 'in', self.ids)],
            fields=['test_case_r_id'],
            groupby=['test_case_r_id']
        )
        test_run_count_dict = {data['test_case_r_id'][0]: data['test_case_r_id_count'] for data in test_run_data}
        for test_run in self:
            test_run.run_count = test_run_count_dict.get(test_run.id, 0)

    # ==========================
    # State Transition Methods
    # ==========================
    def to_review(self):
        """
        Transition the test case to the 'Ready For Review' state.
        """
        if not self.test_case_steps:
            raise ValidationError(
                _("Cannot submit test case. Please add at least one step to the 'Steps' section before proceeding.")
            )
        self.state = 'ready'

    def approved(self):
        """
        Transition the test case to the 'Approved' state.
        Notify the test case creator if the approver is not the creator.
        """
        if not self.test_case_steps:
            raise ValidationError(
                _("Approval Blocked: This test case is missing required steps. Please add at least one step to the 'Test Steps' section before requesting approval.")
            )
        self.state = 'approved'
        self.reviewed_by = self.env.user
        self.review_date = fields.Datetime.now()

        # Notify the CREATOR that their case has been approved
        if self.create_uid and self.create_uid != self.env.user:
            self.activity_schedule(
                'mail.mail_activity_data_todo', # Use a standard Odoo activity type for simplicity
                user_id=self.create_uid.id,
                summary=_('Test Case Approved: %(ref)s', ref=self.ref)
            )

        # Notify the ASSIGNEE that the case is now ready to run
        if self.assigned_to and self.assigned_to != self.env.user and self.assigned_to != self.create_uid:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                user_id=self.assigned_to.id,
                # Changed message to reflect that the case is ready for them to take action
                summary=_('Ready to Run: Test Case %(ref)s is Approved and Assigned.', ref=self.ref)
            )
    def to_draft(self):
        """
        Transition the test case to the 'Draft' state.
        """
        self.state = 'draft'
        if self.create_uid:
                self.activity_schedule(
                'test_management.mail_activity_reopened',
                 user_id=self.create_uid.id,
                 summary=_('Draft Status: Test case %(ref)s has been reset to draft.', ref=self.ref)
                    )

    def run(self):
        """
        Transition the test case to the 'Running' state.
        """
        self.state = 'running'

    def re_open(self):
        """
        Re-open the test case by transitioning it back to the 'Approved' state.
        """
        self.state = 'approved'



    # ==========================
    # Action Methods
    # ==========================
    def open_test_run_action(self):
        """
        Open the Test Run form view with default values.
        """
        self.ensure_one()
        current_date = datetime.now().strftime('%Y-%m-%d')
       # Prepare the default values for the Test Run
        test_run_vals = {
            'default_test_case_r_id': self.id,
            'default_name': f'Run For {self.name} on {current_date}',
            'force_save': True
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Test Run',
            'res_model': 'test.run',
            'view_mode': 'form',
            'context': test_run_vals
        }

    def view_case_related_bugs_action(self):
        """
        Returns an action to display the test bugs related to the current test case.

        This method ensures that only one record is being processed using `ensure_one()`.
        It constructs and returns an action dictionary that opens a list view of the
        `test.bug` model, filtered to show only records related to the current test case.

        Returns:
            dict: An Odoo action dictionary to display related test bugs.

        """
        self.ensure_one()
        model = 'test.bug'
        return {
            'name': _('Related Test Bugs'),
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False, 'active_test': False},
            'res_model': model,
            'view_mode': 'list,form,kanban,pivot,graph',
            'domain': [('test_case_id', '=', self.id)],
        }

    def view_related_runs_action(self):
        """
        Returns an action to display the test runs related to the current test case.

        This method ensures that only one record is being processed using `ensure_one()`.
        It constructs and returns an action dictionary that opens a list view of the
        `test.run` model, filtered to show only records related to the current test case.

        Returns:
            dict: An Odoo action dictionary to display related test runs.


        """
        self.ensure_one()
        model = 'test.run'
        return {
            'name': _('Related Test Runs'),
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'delete': False, 'active_test': False},
            'res_model': model,
            'view_mode': 'list,form,kanban,pivot,graph',
            'domain': [('test_case_r_id', '=', self.id)],
        }
