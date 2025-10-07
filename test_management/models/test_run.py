from odoo import api, fields, models, _
from odoo.exceptions import UserError

class TestRun(models.Model):
    _name = 'test.run'
    _description = 'Test Run'
    _order= "ref desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'mail.activity.mixin']

    ref = fields.Char(
        'REF', copy=False, required=True, readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('test.run'))
    name= fields.Char('Name',required=True)
    description= fields.Text('Description')
    config= fields.Text('Test Configuration')
    test_case_r_id= fields.Many2one('test.case',string='Test Case', required=True,store=True,)
    test_run_step_ids= fields.One2many('test.run.steps','test_run_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed')
    ], string="State", default='draft', tracking=True)
    status = fields.Selection([
        ('passed', 'Passed'),
        ('failed', 'Failed')], string="Status", tracking=True)
    start_date = fields.Datetime(string="Start Date")
    end_date = fields.Datetime(string="End Date")
    run_by = fields.Many2one('res.users','Run By')
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        store=True,
        related='test_case_r_id.project_id',
        help="Project associated with the test case."
    )
    component_id = fields.Many2one(
        'component',
        string='Component',
        store=True,
        related='test_case_r_id.component_id',
        help="Project associated with the test case."
    )

    active = fields.Boolean('Active', default=True)
    bug_count= fields.Integer(compute="_get_related_bug_count")

    def create(self, vals):
        # Check if test_case_r_id is set
        test_run = super(TestRun, self).create(vals)
        if test_run.test_case_r_id:
            test_run.test_case_r_id.state = 'running'
        return test_run

    def unlink(self):
        """
        Override the unlink method to prevent deletion of test runs that are not in the 'draft' state.
        Raises:
            UserError: If any test run is not in the 'draft' state.
        Returns:
            bool: True if the deletion is successful.
        """
        for record in self:
            # Check if the record is not in draft state
            if record.state != 'draft':
                raise UserError(_("Deletion Failed: Only test runs in the 'Draft' status can be deleted. Please use the 'Archive' action instead.") )
        # Call the super method to perform the actual deletion
        return super(TestRun, self).unlink()


    def _get_related_bug_count(self):
        self.bug_count=self.env['test.bug'].search_count([('test_run_id','=',self.id)])


    @api.depends('ref', 'name')
    def _compute_display_name(self):
        for record in self:
            if record.name:
                record.display_name = f"[{record.ref}] {record.name}"
            else:
                record.display_name = record.ref


    def start_run(self):
        self.state='in_progress'
        self.start_date= fields.Datetime.now()
        self.run_by = self.env.user
        # If there are test case steps, prepare them for the Test Run
        if self.test_case_r_id:
            for record in self.test_case_r_id.test_case_steps:
                    self.test_run_step_ids = [(0, 0, {
                            'num': record.num,
                            'action':record.action,
                            'expected_result': record.expected_result,
                            'test_case_id': self.test_case_r_id.id,
                            'test_run_id':self.id,
                        })]

    def complete(self):
        self.state='completed'
        self.end_date=fields.Datetime.now()
        if any(step.result == False for step in self.test_run_step_ids):
            raise UserError(
                _("Cannot Close Run: One or more test steps are still unexecuted. Please complete all steps before setting the run to 'Completed'.")
            )
        if any(step.result in ('failed', 'blocked') for step in self.test_run_step_ids):
            self.status = 'failed'
        else:
            self.status = 'passed'
        self.test_case_r_id.state='executed'


    def get_steps(self):
            if self.test_case_r_id:
                for record in self.test_case_r_id.test_case_steps:
                        self.test_run_step_ids = [(0, 0, {
                        'num': record.num,
                        'step':record.step,
                        'expected_result': record.expected_result,
                        'test_case_id': self.test_case_r_id.id,
                        'test_run_id':self.id,
                         'active':True,
                    })]


    def view_related_bugs_action(self):
        self.ensure_one()
        model='test.bug'
        return {
                'name': _('Related Test Steps'),
                'type': 'ir.actions.act_window',
                'context': {'create': False, 'delete': False,'active_test': False},
                'res_model': model,
                'view_mode': 'list,form,kanban,pivot,graph',
                'domain': [('test_run_id', '=', self.id)],
            }
