from odoo import models, fields, api

class ReopenBugWizard(models.TransientModel):
    _name = 'reopen.bug.wizard'
    _description = 'Reopen Bug Wizard'

    reopen_reason = fields.Text(string="Reopen Reason", required=True)

    def action_reopen_bug(self):
        # Get the active bug record
        bug_id = self.env.context.get('active_id')
        bug = self.env['test.bug'].browse(bug_id)

        # Update the bug state and rejection reason
        bug.write({
            'state': 'reject',
            'rejection_reason': self.reopen_reason,
        })
