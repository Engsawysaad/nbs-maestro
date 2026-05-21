# NBS School

Nottingham British School customizations for ERPNext.

## Features

- Permission hooks for Education module (Course Schedule, Student, etc.)
- Auto-creation of User Permissions on Course Schedule submission
- Custom workspace configurations for NBS roles
- Integration with NBS permission matrix (12 custom roles, 5 modules)

## Installation

```bash
bench get-app https://github.com/Engsawysaad/nbs-maestro.git --branch main
bench --site your-site install-app nbs_school
bench --site your-site migrate
```

## Dependencies

- Frappe >= v16.0.0
