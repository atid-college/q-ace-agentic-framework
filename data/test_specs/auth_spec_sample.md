# Sample Specification: User Authentication System

## 1. Login Functionality
The system shall allow users to log in using their email and password.
- Email must be a valid format.
- Password must be at least 8 characters long.
- After 3 failed attempts, the account should be locked for 15 minutes.

## 2. Password Reset
Users can request a password reset by providing their email.
- A reset link is sent to the email address if it exists in the system.
- The link is valid for 1 hour.

## 3. Security Requirements
- All passwords must be hashed using bcrypt.
- Session tokens must be invalidated upon logout.
- Direct access to the dashboard without a valid session should redirect to login.
