from datetime import timedelta
from odoo import api, fields, models, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError


class TestBug(models.Model):
    """
    Test Bug Model
    This model represents a bug reported during testing. It tracks the bug's lifecycle,
    including its state, severity, priority, and related test cases or steps.
    """

    _name = "test.bug"
    _description="Test Bug"
    _inherit = ['mail.thread.main.attachment', 'mail.thread', 'mail.activity.mixin']
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
        default=lambda self: self.env['ir.sequence'].next_by_code('test.bug'),
        help="Unique reference number for the bug."
    )
    name = fields.Char(
        string="Summary",
        required=True,
        tracking=True,
        help="A short summary of the bug."
    )
    description = fields.Text(
        string="Description",
        help="A detailed description of the bug, including steps to reproduce."
    )
    environment = fields.Text(
        string="Environment",
        help="The environment (e.g., OS, browser, server version) where the bug was encountered."
    )

    # Date Fields
    due_date = fields.Date(
        string='Due Date',
        help="The expected date by which the bug should be resolved."
    )
    reported_date = fields.Datetime(
        string="Reported On",
        default=fields.Datetime.now,
        help="Date and time when the bug was reported."
    )
    fix_start_date = fields.Datetime(
        string="Fix Start Date",
        help="The date and time when work on the bug fix began."
    )
    fix_end_date = fields.Datetime(
        string="Fix End Date",
        help="The date and time when the bug fix was completed."
    )

    # Relational Fields
    test_case_id = fields.Many2one(
        'test.case',
        string="Test Case",
        help="The specific test case associated with this bug."
    )
    test_step_id = fields.Many2one(
        'test.case.steps',
        string="Failing Step",
        ondelete='restrict',
        help="The specific test step where the bug was encountered."
    )
    dependency = fields.Many2one(
        'test.bug',
        string="Related Bug",
        help="Another bug that this bug is dependent on, or a possible duplicate"
    )
    assignee_id = fields.Many2one(
        'res.users',
        string="Assigned To",
        help="The user responsible for fixing the bug."
    )
    project_id = fields.Many2one(
        'project.project',
        string="Project",
        related="test_case_id.project_id",
        store=True,
        readonly=False,
        help="Project associated with the bug."
    )
    reported_by = fields.Many2one(
        'res.users',
        string="Reported By",
        default=lambda self: self.env.user,
        help="User who reported the bug."
    )
    fixed_by = fields.Many2one(
        'res.users',
        string="Fixed By",
        help="The user who committed the bug fix."
    )
    test_run_id = fields.Many2one(
        'test.run',
        string='Test Run',
        help="Test run during which the bug was encountered."
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        string="Attachments",
        help="Files attached to the bug report."
    )
    component_id = fields.Many2one(
        'component',
        string='Component/Module',
        related='test_case_id.component_id',
        store=True,
        readonly=False,

        help="Component to which this bug belongs."
    )

    # Selection Fields
    severity = fields.Selection(
        selection=[
            ('low', 'Minor'),
            ('medium', 'Medium'),
            ('high', 'Major'),
            ('critical', 'Critical'),
            ('blocker', 'Blocker')
        ],
        string="Severity",
        default='medium',
        tracking=True,
        help="The severity level of the bug, reflecting its impact on system functionality."
    )
    priority = fields.Selection(
        selection=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent')
        ],
        string="Priority",
        default='medium',
        tracking=True,
        help="The priority level of the bug, reflecting its business importance and fix urgency."
    )
    state = fields.Selection(
        selection=[
            ('new', 'New'),
            ('confirmed', 'Confirmed'),
            ('in_progress', 'In Progress'),
            ('fixed', 'Resolved'),
            ('retest', 'Retesting'),
            ('reject', 'Re-opened'),
            ('closed', 'Closed')
        ],
        string="State",
        default='new',
        tracking=True,
        help="Current state of the bug."
    )
    rejection_reason = fields.Text(string="Reopening Reason")

    active = fields.Boolean('Active', default=True)

    # ==========================
    # Methods
    # ==========================

    @api.depends('ref', 'name')
    def _compute_display_name(self):
        for record in self:
            if record.name:
                record.display_name = f"[{record.ref}] {record.name}"
            else:
                record.display_name = record.ref

    def write(self, vals):
        """
        Override the write method to handle assignment and reopening activities.
        """
        if 'assignee_id' in vals:
            self._schedule_assignment_activity(vals['assignee_id'])
        if 'rejection_reason' in vals:
            self._schedule_reopened_activity()
        return super(TestBug, self).write(vals)

    def unlink(self):
        """
        Override the unlink method to prevent deletion of bugs that are not in the 'draft' state.
        """
        for record in self:
            if record.state != 'new':
                raise UserError(
                    _("You cannot delete a bug that is not in the 'New' state. Please archive it instead.")
                )
        return super(TestBug, self).unlink()

    @api.onchange('test_case_id')
    def _onchange_test_case_id(self):
        """
        Update the project when the test case is changed.
        Apply a domain to restrict test cases to those in 'failed' or 'running' states.
        """
        if self.test_case_id:
            self.project_id = self.test_case_id.project_id
            return {'domain': {'test_case_id': ['|', ('state', '=', 'failed'), ('state', '=', 'running')]}}
        return {}

    @api.onchange('test_step_id')
    def _onchange_test_step_id(self):
        """
        Update the test case when the test step is changed.
        """
        if self.test_step_id:
            self.test_case_id = self.test_step_id.test_case_id

    # ==========================
    # State Transition Methods
    # ==========================

    def confirm(self):
        """
        Transition the bug to the 'Confirmed' state.
        """
        self.state = 'confirmed'

    def in_progress(self):
        """
        Transition the bug to the 'In Progress' state.
        """
        self.state = 'in_progress'
        self.fix_start_date = fields.Datetime.now()

    def fixed(self):
        """
        Transition the bug to the 'Fixed' state.
        Set the fixed by user and fixed date.
        """
        self.state = 'fixed'
        self.fixed_by = self.env.user
        self.fix_end_date = fields.Datetime.now()
        self._schedule_fixed_activity()

    def rejected(self):
        """
        Transition the bug to the 'Rejected' state.
        """
        self.state = 'reject'

    def closed(self):
        """
        Transition the bug to the 'Closed' state.
        """
        self.state = 'closed'
        self._schedule_closed_activity()

    def re_open(self):
        """
        Transition the bug to the 'confirmed' state.
        """
        self.state = 'confirmed'



    def action_open_reopen_wizard(self):
        """
        Open the wizard for reopening a bug.
        """
        return {
            'name': 'Reopen Bug',
            'type': 'ir.actions.act_window',
            'res_model': 'reopen.bug.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }

    # Helper Methods
    def _schedule_assignment_activity(self, assignee_id):
        """
        Schedule an activity when a bug is assigned to a developer.
        """
        self.activity_schedule(
            'test_management.mail_activity_assignment',
            user_id=assignee_id,
                summary=_('New bug assigned: %(ref)s - %(name)s', ref=self.ref, name=self.name)
        )

    def _schedule_reopened_activity(self):
        """
        Schedule an activity when a bug is reopened.
        """
        self.activity_schedule(
            'test_management.mail_activity_reopened',
            user_id=self.assignee_id.id,
            summary=_('Bug Reopened: %(ref)s. Please review the reasons and restart work.', ref=self.ref)
           )

    def _schedule_fixed_activity(self):
        """
        Schedule an activity when a bug is fixed.
        """
        self.ensure_one()

        # Schedule the activity
        self.activity_schedule(
                'test_management.mail_activity_fixed',
                user_id=self.reported_by.id,
                summary=_('Bug Fixed: %(ref)s is ready for retesting.', ref=self.ref) # Improved message
        )

    def _schedule_closed_activity(self):
        """
        Schedule an activity when a bug is closed.
        """
        self.activity_schedule(
            'test_management.mail_activity_assignment',
            user_id=self.assignee_id.id,
            summary=_('Bug Closed: %(ref)s. Well done!', ref=self.ref)
        )



