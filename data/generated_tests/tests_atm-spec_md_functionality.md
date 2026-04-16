## Test Cases for ATM System - Functionality

### Potential Issues/Gaps:

*   **Deposit Functionality Details:** The specification for Deposit (3.4) is vague. It mentions "deposit cash or checks" but lacks details on:
    *   How cash is deposited (e.g., slot type, capacity, verification process).
    *   How checks are deposited (e.g., scanning, amount entry, endorsement requirements).
    *   Whether there are limits on deposit amounts or number of items.
    *   Error handling for incorrect denominations or invalid checks.
*   **Withdrawal Amount Selection:** The specification for Cash Withdrawal (3.3) states "The user shall select withdrawal amount," but doesn't specify constraints like:
    *   Minimum/maximum withdrawal limits per transaction or per day.
    *   Availability of predefined withdrawal amounts.
    *   Handling of withdrawal amounts not divisible by ATM's dispense units (e.g., $20 bills).
*   **Account Types:** The specification doesn't mention different account types (e.g., savings, checking) and if there are any specific rules or limits associated with them for different transactions.
*   **Card Types:** While 6. Constraints mentions supporting "standard debit/credit cards," it doesn't specify if the ATM supports all card networks (Visa, Mastercard, Amex, etc.) or if there are any limitations.
*   **Error Messages and User Feedback:** The specification doesn't detail specific error messages that should be displayed to the user in various scenarios (e.g., insufficient funds, invalid PIN, card error, network issues).
*   **Transaction Limits/Timeouts:** No mention of session timeouts or transaction limits.
*   **Denominations:** The specification does not mention the denominations of cash the ATM can dispense. This is crucial for withdrawal testing.
*   **Receipt Printer Status:** No mention of how the system handles a full or malfunctioning receipt printer.
*   **Network Disruption:** No requirements or handling for network disconnections during a transaction.

---

### Test Cases:

| ID    | Title                                     | Description                                                                                                                                                                  | Prerequisites                                                                                                                                                                                                                                                                   | Steps