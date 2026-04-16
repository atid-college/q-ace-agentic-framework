# 📱 Mobile Agent

The Mobile Agent is an AI-powered component of the Q-ACE framework that automates interaction with Android (and iOS) devices via [Appium](https://appium.io/). It interprets natural language tasks, observes the live device UI hierarchy, and executes actions — clicks, typing, swipes — in real time.

## 🚀 Key Capabilities

- **Natural Language Task Execution**: Give instructions like *"Open the Settings app and enable Dark Mode"* or *"Launch the app, log in as 'testuser', and verify the home screen title."*
- **Live UI Observation**: Automatically fetches and analyzes the device's XML UI hierarchy at each step to understand the current screen state.
- **Intelligent Action Loop**: Uses an LLM to decide the best next action (click, type, swipe) based on the visible UI elements.
- **Streaming Execution Log**: All steps are streamed in real-time to the console panel via SSE (Server-Sent Events).
- **History Tracking**: Every run is persisted to the database — including failed and cancelled executions.

## 🛠️ Technology Stack

- **Automation Library**: `Appium-Python-Client==1.3.0`
- **WebDriver**: `selenium==3.141.0` (used by the Appium client)
- **Server**: Appium server (must be running separately on `http://localhost:4723/wd/hub`)
- **Interface**: FastAPI SSE streaming → Alpine.js frontend
- **Database**: SQLite (`data/q-ace.db`) for history persistence

## ⚙️ Prerequisites & Setup

### 1. Install Appium
```bash
npm install -g appium
```

### 2. Install the Android Driver
```bash
appium driver install uiautomator2
```

### 3. Start the Appium Server
```bash
appium --base-path /wd/hub
```
The server should be running at `http://localhost:4723/wd/hub`.

### 4. Connect a Device or Start an Emulator
- Connect a physical Android device with USB Debugging enabled, or
- Start an Android Virtual Device (AVD) via Android Studio.

## 🔧 Configuration (Appium Config Tab)

| Field | Description | Example |
|---|---|---|
| **Appium Server URL** | URL of the running Appium server | `http://localhost:4723` |
| **Platform Name** | Target platform | `Android` or `iOS` |
| **Device UDID** | Device identifier (optional for single device) | `emulator-5554` |
| **App Package** | Android app package name | `com.example.myapp` |
| **App Activity** | Main activity to launch | `.MainActivity` |

All settings are auto-persisted in `localStorage` between sessions.

## 🤖 Supported LLM Providers

The Mobile Agent uses the shared Q-ACE LLM client and supports any configured provider:
- **Google Gemini** (recommended: `gemini-2.5-flash`)
- **Ollama** (local, e.g., `llama3`, `gemma3`)

## 📊 History & Analytics (Results Tab)

Every execution (success, failure, or cancellation) is automatically saved to `data/q-ace.db`:

- **Dashboard view**: KPI cards (Total Runs, Success Rate, Failures) and a 7-day execution frequency chart.
- **Run detail view**: Step-by-step console logs, the final result, and a timestamp.
- **Status icons**: Green ✓ for success, Red ✗ for failures and cancellations.

## 🚀 Execution Model

The agent runs as an async streaming task via `/api/mobile-agent/run`:
1. Connects to the Appium server and launches the target app.
2. Fetches the UI XML hierarchy and sanitizes invalid characters.
3. Sends the filtered hierarchy + task prompt to the configured LLM.
4. Parses the LLM JSON response (`click`, `type`, `swipe`, `done`) and executes the action.
5. Repeats steps 2–4 until `done` is emitted or an error/stop signal is received.
6. Saves the full execution record (logs + result) to the history database.

## 🐛 Known Limitations

- Requires Appium `1.3.0` client — newer versions use a different API (`AppiumOptions`).
- Some apps with dynamic or non-standard UI hierarchies may produce XML parsing errors; the agent automatically sanitizes these.
- iOS support requires Appium's `XCUITest` driver and additional macOS toolchain.
