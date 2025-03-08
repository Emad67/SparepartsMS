# Spare Parts Management System (SPMS)

A comprehensive web application for managing spare parts inventory, sales, and operations. Built with Flask and SQLite, perfect for small to medium-sized spare parts shops.

Copyright © 2025 Aman Kflom and Nesredin Abdelrahim. All rights reserved.

CONFIDENTIAL AND PROPRIETARY

This work is protected under copyright law. The receipt or possession of this source code and associated documentation files (the "Software") does not convey any rights to use, modify, or distribute it.

No part of this software may be reproduced, distributed, or transmitted in any form or by any means, including photocopying, recording, or other electronic or mechanical methods, without the prior written permission of the copyright holders, except in the case of brief quotations embodied in critical reviews and certain other noncommercial uses permitted by copyright law.

Made with ❤️ by:
- Aman Kflom (07229417)
- Nesredin Abdelrahim (07546658)

## Features

### 1. Inventory Management
- Track parts inventory across multiple warehouses
- Automatic stock level monitoring
- Minimum stock level alerts
- Part categorization and search
- Image support for parts


### 2. Point of Sale (POS)
- Quick part search and selection
- Shopping cart functionality
- Real-time stock checking
- Sales receipt generation
- Transaction history

### 3. Financial Management
- Sales tracking
- Purchase management
- Expense tracking
- Revenue reports
- Profit/Loss analysis
- Credit management

### 4. User Management
- Role-based access control (Admin, Manager, Staff)
- Secure authentication
- User activity tracking
- Internal messaging system

### 5. Reports & Analytics
- Sales reports
- Inventory reports
- Financial reports
- Stock transfer reports
- Export to PDF/Excel

### 6. Additional Features
- Stock transfers between warehouses
- Supplier management
- Customer management
- Loan tracking
- Bincard system
- Backup/Restore functionality

## Technical Requirements

### System Requirements
- Python 3.8 or higher
- SQLite 3
- Modern web browser

### Dependencies
```
# Core Framework
Flask==2.3.2
Flask-WTF==1.0.1
Flask-Login==0.6.2
Flask-Security==4.0.0
Flask-SQLAlchemy==3.0.3
Flask-Migrate==4.0.4
Flask-Mail==0.9.1

# Database
SQLAlchemy==2.0.15
alembic==1.11.1

# Forms and Validation
WTForms==3.0.1
email-validator==2.0.0

# Security
werkzeug==2.3.6
bcrypt==4.0.1
passlib==1.7.4

# Report Generation
reportlab==4.0.4
WeasyPrint==59.0
openpyxl==3.1.2
XlsxWriter==3.1.2

# Image Processing
Pillow==9.5.0

# Utilities
python-dateutil==2.8.2
python-dotenv==1.0.0

# Testing
pytest==7.3.1
pytest-flask==1.2.0
```

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd spareparts
```

2. activate the virtual environment:
```bash

# On Windows:
.\spareparts\Scripts\activate
# On Unix or MacOS:
source spareparts/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create .env file
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///spms.db
```

5. Initialize the database:
```bash
flask db upgrade
```
6. Run the application:
```bash
python create_tables.py && python init_db.py

```

7. Run the application:
```bash
python wsgi.py
```

## First Time Setup

1. Access the application at `http://localhost:5000`
2. Log in with default admin credentials:
   - Username: admin
   - Password: admin
3. Change the default password immediately
4. Set up:
   - Categories
   - Warehouses
   - Suppliers
   - Initial inventory

## Database Management

### Backup
- Regular backups can be performed from the admin panel
- Backup files are stored in the `backups` directory
- Both manual and scheduled backups are supported

### Restore
- Restore functionality available in admin panel
- Select backup file to restore
- System validates backup file before restoration

## Security Features

- Password hashing using bcrypt
- Role-based access control
- Session management
- CSRF protection
- Input validation
- Secure file uploads

## Best Practices

1. Regular Backups
   - Daily automated backups
   - Manual backups before major changes

2. User Management
   - Regular password changes
   - Proper role assignments
   - Activity monitoring

3. Inventory Management
   - Regular stock counts
   - Minimum stock level maintenance
   - Timely updates of part information

4. System Maintenance
   - Regular database optimization
   - Log monitoring
   - System updates

## Support

For support and inquiries, please contact:
- Aman Kflom (07229417)
- Nesredin Abdelrahim (07546658)

## License and Legal Notice

This software is proprietary and confidential. 

Unauthorized copying, modification, distribution, or use of this software, via any medium, is strictly prohibited. The software is protected by copyright law and international treaties.

Any use or disclosure of this software without explicit written permission from the copyright holders (Aman Kflom and Nesredin Abdelrahim) is strictly prohibited and may result in severe legal consequences.

For licensing inquiries, please contact:
- Aman Kflom (07229417)
- Nesredin Abdelrahim (07546658)

---

Made with ❤️ in Flask