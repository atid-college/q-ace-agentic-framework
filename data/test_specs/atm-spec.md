# Software Requirements Specification (SRS)
## ATM System

### 1. Introduction

#### 1.1 Purpose
This document describes the functional and non-functional requirements for an Automated Teller Machine (ATM) System. The system allows bank customers to perform basic banking transactions such as withdrawing cash, checking account balances, and depositing funds.

#### 1.2 Scope
The ATM System provides a secure interface between bank customers and the bank’s core banking system. It enables customers to authenticate using a bank card and PIN and perform financial transactions through the ATM terminal.

#### 1.3 Definitions
- ATM – Automated Teller Machine used for banking transactions.
- PIN – Personal Identification Number used for authentication.
- Bank Server – Central banking system that processes transactions.

---

### 2. Overall Description

#### 2.1 System Overview
The ATM system consists of:
- ATM terminal hardware (card reader, screen, keypad, cash dispenser, receipt printer)
- ATM application software
- Secure connection to the bank server

The system authenticates users and processes requests through the bank’s backend system.

#### 2.2 User Classes
- Bank Customers – Individuals using ATM cards to perform transactions.
- Bank Administrators – Personnel responsible for maintenance and monitoring.

#### 2.3 Operating Environment
- ATM machine running embedded operating system
- Secure network connection to bank servers
- Integration with banking database systems

---

### 3. Functional Requirements

#### 3.1 User Authentication
- The system shall read the user’s ATM card.
- The system shall request the user to enter a PIN.
- The system shall validate the PIN with the bank server.
- The system shall block the card after 3 incorrect PIN attempts.

#### 3.2 Balance Inquiry
- The user shall be able to request account balance.
- The system shall retrieve balance information from the bank server.
- The balance shall be displayed on the screen and optionally printed.

#### 3.3 Cash Withdrawal
- The user shall select withdrawal amount.
- The system shall verify sufficient account balance.
- The system shall dispense cash if the transaction is approved.
- The system shall update the account balance in the bank server.

#### 3.4 Deposit
- The user shall be able to deposit cash or checks.
- The system shall record the deposit and send the information to the bank server.
- A receipt shall be printed for confirmation.

#### 3.5 Receipt Printing
- The system shall print a receipt after each transaction.
- The receipt shall include transaction type, date, time, and amount.

---

### 4. Non-Functional Requirements

#### 4.1 Security
- All communication with the bank server must be encrypted.
- User PIN must never be stored locally.

#### 4.2 Reliability
- The system should operate 24/7 with minimal downtime.
- Transactions must be processed accurately.

#### 4.3 Performance
- Authentication should complete within 5 seconds.
- Transaction processing should complete within 10 seconds.

#### 4.4 Usability
- The interface should be simple and easy to use.
- Instructions must be clearly displayed on the screen.

---

### 5. External Interfaces

#### 5.1 Hardware Interfaces
- Card reader
- Keypad
- Display screen
- Cash dispenser
- Receipt printer

#### 5.2 Software Interfaces
- Bank core banking system
- Transaction processing server

---

### 6. Constraints
- The system must comply with banking security standards.
- The ATM must support standard debit/credit cards.