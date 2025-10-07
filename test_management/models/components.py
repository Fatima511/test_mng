from odoo import models, fields

class Component(models.Model):
    """
    Model representing a system component associated with a project.
    """
    _name = 'component'
    _description = 'System Component Model'
    _order = 'id desc'

    # Basic Fields
    name = fields.Char(
        string="Name",
        required=True,
        help="Name of the system component."
    )
    description = fields.Text(
        string="Description",
        help="Detailed description of the component."
    )

    # Relationships
    project_id = fields.Many2one(
        'project.project',
        string="Project",
        required=True,
        help="The project to which this component belongs."
    )

    # Status Field
    active = fields.Boolean(
        string="Active",
        default=True,
        help="Indicates whether the component is active."
    )

    # Constraints
    _sql_constraints = [
        (
            'name_project_unique',
            'unique (name, project_id)',
            "Each component must have a unique name within a project."
        ),
    ]
