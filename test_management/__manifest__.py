{
    'name': 'Test Management',
    'version': '1.0',
    'summary': 'Module for managing software tests',
    'description': 'This Odoo module is designed to manage test cases, test runs, test steps, and bugs in a structured and efficient manner. It provides a comprehensive solution for quality assurance teams to plan, execute, and track testing activities. ',
    'author': 'ApplyIT',
    'category': 'Quality Assurance',
    'price':60,
    'currency':'USD',
    'depends': ['base','project','mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'data/test_sequence.xml',
        'data/mail_activity_data.xml',

        'wizard/reopen_bug_view.xml',

        'views/project_view.xml',
        'views/component_view.xml',
        'views/test_case_view.xml',
        'views/test_run_view.xml',
        'views/test_bug.xml',
        'views/menu.xml',

    ],
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': True,
    'license': 'OPL-1',

}
