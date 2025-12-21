# KAYO - Youth Delegates Registration System

A Flask web application for managing youth delegate registrations with M-Pesa payment integration.

## Features

- 🔐 **Authentication System** - Login for Chairs, Finance, and Admins
- 👥 **Delegate Registration** - Register delegates with church details
- 💳 **M-Pesa Integration** - Daraja API for seamless payments via STK Push
- 📊 **Admin Dashboard** - Overview with statistics, reports, and exports
- 📄 **Export Reports** - Excel and PDF export functionality
- 📱 **Responsive Design** - Bootstrap 5 for mobile-friendly interface

## Tech Stack

- **Backend:** Flask (Python)
- **Database:** SQLAlchemy (SQLite/PostgreSQL)
- **Frontend:** Bootstrap 5, Jinja2 Templates
- **Payment:** M-Pesa Daraja API
- **Authentication:** Flask-Login

## Project Structure

```
KAYO/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── forms.py             # WTForms definitions
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py          # User model
│   │   ├── delegate.py      # Delegate model
│   │   └── payment.py       # Payment model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py          # Authentication routes
│   │   ├── main.py          # Main dashboard routes
│   │   ├── delegates.py     # Delegate management
│   │   ├── payments.py      # Payment processing
│   │   └── admin.py         # Admin routes
│   ├── services/
│   │   ├── __init__.py
│   │   └── mpesa.py         # M-Pesa Daraja API
│   └── templates/
│       ├── base.html
│       ├── dashboard.html
│       ├── auth/
│       ├── delegates/
│       ├── payments/
│       └── admin/
├── config.py                # Configuration
├── run.py                   # Entry point
├── init_db.py              # Database initialization
├── requirements.txt
├── .env.example            # Environment template
└── README.md
```

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/KAYO.git
   cd KAYO
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize the database**
   ```bash
   python init_db.py
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

7. **Open in browser**
   ```
   http://localhost:5000
   ```

## Default Admin Login

- **Email:** admin@kayo.org
- **Password:** admin123

⚠️ **Change the admin password immediately after first login!**

## M-Pesa Configuration

1. Register at [Safaricom Developer Portal](https://developer.safaricom.co.ke/)
2. Create an app and get your credentials
3. Update `.env` with your M-Pesa credentials:
   ```
   MPESA_CONSUMER_KEY=your-consumer-key
   MPESA_CONSUMER_SECRET=your-consumer-secret
   MPESA_SHORTCODE=your-paybill-number
   MPESA_PASSKEY=your-passkey
   MPESA_CALLBACK_URL=https://yourdomain.com/payments/callback
   MPESA_ENV=sandbox  # or 'production'
   ```

## Database Migration (PostgreSQL)

For production with PostgreSQL:

1. Update `DATABASE_URL` in `.env`:
   ```
   DATABASE_URL=postgresql://username:password@localhost/kayo_db
   ```

2. Initialize migrations:
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

## Deployment (PythonAnywhere)

1. Upload project to PythonAnywhere
2. Set up virtual environment
3. Configure WSGI file to point to `run.py`
4. Set environment variables in PythonAnywhere console
5. Ensure M-Pesa callback URL is accessible

## Usage Guide

### For Chairs

1. Register an account with your church details
2. Log in to access your dashboard
3. Register delegates using the form
4. Once done, initiate payment for all unpaid delegates
5. Complete M-Pesa payment via STK Push

### For Admins

1. Log in with admin credentials
2. View overall statistics on dashboard
3. Manage users (create, edit, deactivate)
4. View all delegates with filters
5. Export reports to Excel or PDF
6. Monitor payment status

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/login` | GET, POST | User login |
| `/register` | GET, POST | User registration |
| `/dashboard` | GET | User dashboard |
| `/delegates/register` | GET, POST | Register delegate |
| `/delegates/` | GET | List delegates |
| `/payments/` | GET | Payment page |
| `/payments/initiate` | POST | Initiate M-Pesa payment |
| `/payments/callback` | POST | M-Pesa callback |
| `/admin/` | GET | Admin dashboard |
| `/admin/export/delegates` | GET | Export to Excel |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Support

For support, email support@kayo.org or create an issue on GitHub.
