# 📄 Test Generator Agent

The Test Generator Agent transforms technical specifications, documents, and web pages into comprehensive, structured test suites. It applies industrial testing techniques to ensure full coverage of your system's requirements.

## 🚀 Key Features

- **Multi-Source Analysis**: Analyze specifications from **PDF files, JSON documents, or live URLs**.
- **Versatile Test Categories**: Generate tests for various quality gates:
    - Functionality
    - Security
    - Performance
    - Accessibility
    - Usability
    - Reliability
- **Advanced Testing Techniques**: Automatically applies proven methodologies:
    - Boundary Value Analysis (BVA)
    - Equivalence Partitioning (EP)
    - Decision Table Testing
    - State Transition Testing
    - Smoke Testing
    - Positive/Negative Testing
- **Multi-Language Support**: Generates test cases in the same language as the source documentation (e.g., Hebrew specs result in Hebrew test cases).
- **Test Case Management**: Built-in features to save, view, delete, and manage generated test suites.

## 🛠️ How It Works

1. **Content Extraction**: The agent scrapes URLs or extracts text from local files (PDF, JSON, TXT).
2. **Contextual Analysis**: An LLM analyzes the extracted content based on the selected test category and techniques.
3. **Drafting**: The agent generates a structured Markdown table containing IDs, Titles, Descriptions, Steps, and Expected Results.
4. **Gap Identification**: Beyond just generating tests, the agent identifies ambiguities or missing information in the original specification.

## 🚦 Usage Examples

- *"Analyze the login-spec.pdf using Boundary Value Analysis for security"*
- *"Generate functionality smoke tests from https://api.docs.com/v1"*
- *"בצע ניתוח של מסמך הדרישות ובנה חבילת בדיקות עבור ביצועים"*
- *"Apply state transition testing to the checkout-flow.json"*

## 📂 Output Format

Test cases are generated in a clean, professional Markdown table format, including:
- **Prerequisites**: What needs to be in place before the test starts.
- **Priority**: High, Medium, or Low impact.
- **Applied Technique**: Which specific testing logic was used for each case.

## ⚙️ Test Management

- **Save to Local**: All generated tests are stored in `data/generated_tests/`.
- **Review History**: Access previous test suites, review their content, or delete obsolete versions.
- **Spec Repository**: Manage your source documents in the central `data/test_specs/` folder.
