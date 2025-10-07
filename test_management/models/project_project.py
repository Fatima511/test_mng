from odoo import models, fields, api

class ProjectProject(models.Model):
    _inherit = 'project.project'

    # Computed fields for counts
    bug_count = fields.Integer(compute='_compute_bug_count', string="Bug Count")
    test_case_count = fields.Integer(compute='_compute_test_case_count', string="Test Case Count")

    def _compute_bug_count(self):
        """Compute the number of bugs related to the project."""
        bug_data = self.env['test.bug'].read_group(
            domain=[('project_id', 'in', self.ids)],
            fields=['project_id'],
            groupby=['project_id']
        )
        bug_count_dict = {data['project_id'][0]: data['project_id_count'] for data in bug_data}
        for project in self:
            project.bug_count = bug_count_dict.get(project.id, 0)

    def _compute_test_case_count(self):
        """Compute the number of test cases related to the project."""
        test_case_data = self.env['test.case'].read_group(
            domain=[('project_id', 'in', self.ids)],
            fields=['project_id'],
            groupby=['project_id']
        )
        test_case_count_dict = {data['project_id'][0]: data['project_id_count'] for data in test_case_data}
        for project in self:
            project.test_case_count = test_case_count_dict.get(project.id, 0)

    def action_view_bugs(self):
        """Open the list view of bugs related to the project."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Bugs',
            'res_model': 'test.bug',
            'view_mode': 'list,form,pivot,graph,kanban',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }

    def action_view_test_cases(self):
        """Open the list view of test cases related to the project."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Test Cases',
            'res_model': 'test.case',
            'view_mode': 'list,form,pivot,graph,kanban',
            'domain': [('project_id', '=', self.id)],
            'context': {'default_project_id': self.id},
        }
