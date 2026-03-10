# Dental Clinic Management System
#### Video Demo: https://youtu.be/VLEhD6xINyQ?si=jhPtguwrKNCYMsYK

## Description:
This project is a comprehensive web-based application designed to streamline the daily operations of a dental clinic. The application facilitates patient management, appointment scheduling with dynamic time-slot validation, and business performance visualization through interactive dashboards.

The system implements a **Role-Based Access Control (RBAC)** model, ensuring that each user can only access features relevant to their specific position:

1. **Owner/Admin:** Has access to financial and management analytics, as well as oversight of all medical personnel.
2. **Secretary:** Responsible for patient registration and comprehensive schedule management.
3. **Doctor:** Can view their personal daily agenda and mark patient attendance.

### File Structure:

* **app.py:** The core of the Flask application. It manages routing, authentication logic, and all interactions with the SQL database.
* **dentist.db:** An SQLite database storing information for users, patients, specialties, and appointments.
* **reset_database.py:** An initialization script that defines the database schema with normalized tables to ensure data integrity and prevent redundancy.
* **helper.py:** Contains custom decorators used to enforce login requirements and role-specific access to protected routes.
* **generate_graphs_data.py & pupulate_data.py:** Development tools used to populate the system with mock data, allowing for the verification of chart functionality and scheduling logic.
* **templates/:** A collection of HTML files utilizing **Jinja2** to render dynamic content, such as custom dashboards for each role.
* **static/:** Contains custom CSS styles providing a professional and clean user interface.

### Design Choices:

* **Appointment Management:** I implemented 30-minute intervals for appointments, which are calculated dynamically based on each doctor's specific start and end times defined in the database.
* **Security:** User passwords are never stored as plain text; instead, they are secured using `werkzeug.security` hashes to meet the industry standards learned during the course.
* **Data Visualization:** I integrated **Chart.js** into the Owner’s dashboard to transform raw SQL data into visual insights, facilitating better business decision-making.

### AI Attribution:
This project utilized **Gemini 1.5 Pro** as an assistant for generating mock data for testing and for debugging complex SQL queries used in the monthly analytics reports.