import sys
import os
import json
import asyncio
import traceback

SCREENSHOT_POLICY_MESSAGE = (
    "POLICY: Do not take screenshots unless explicitly requested by the user in their prompt. "
    "To validate page content, titles, or field values, always prefer using the HTML/accessibility tree "
    "retrieved from the page. Only use the 'take_screenshot' action if the user's task specifically "
    "asks for a visual confirmation or a screenshot."
)

# Add the project root to sys.path
sys.path.append(os.getcwd())

# Suppress browser_use logging to keep stdout clean for JSON communication
os.environ['BROWSER_USE_SETUP_LOGGING'] = 'false'

async def main():
    if len(sys.argv) < 3:
        print(json.dumps({"type": "error", "text": "Insufficient arguments for browser_agent_runner.py"}), flush=True)
        return

    task = sys.argv[1]
    global_config = json.loads(sys.argv[2])
    agent_config = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
    llm_specific_config = json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
    browser_config_args = json.loads(sys.argv[5]) if len(sys.argv) > 5 else {}

    try:
        # Use browser_use's built-in LLM wrappers (v0.12+)
        from browser_use import Agent, Browser
        from browser_use.llm.google.chat import ChatGoogle
        from browser_use.llm.ollama.chat import ChatOllama

        provider = global_config.get("provider", "gemini")

        # Initialize LLM using browser_use's native clients
        if provider == "gemini":
            api_key = global_config.get("api_key")
            model = global_config.get("model", "gemini-2.5-flash")

            print(json.dumps({"type": "step", "text": f"🔧 Initializing Gemini ({model})..."}), flush=True)

            if not api_key:
                print(json.dumps({"type": "error", "text": "Gemini API key is missing from global_config. Please configure your API key in Global Settings."}), flush=True)
                return

            llm = ChatGoogle(model=model, api_key=api_key)
        else:
            base_url = global_config.get("base_url", "http://localhost:11434")
            model = global_config.get("model", "llama3")
            print(json.dumps({"type": "step", "text": f"🔧 Initializing Ollama ({model}) at {base_url}..."}), flush=True)
            llm = ChatOllama(model=model, host=base_url)

        # Set Action Timeouts via Environment Variables
        timeouts = agent_config.get("timeouts")
        if isinstance(timeouts, dict):
            if timeouts.get("navigate"): os.environ["TIMEOUT_NavigateToUrlEvent"] = str(timeouts["navigate"])
            if timeouts.get("click"): os.environ["TIMEOUT_ClickElementEvent"] = str(timeouts["click"])
            if timeouts.get("type"): os.environ["TIMEOUT_TypeTextEvent"] = str(timeouts["type"])
            if timeouts.get("screenshot"): os.environ["TIMEOUT_ScreenshotEvent"] = str(timeouts["screenshot"])

        # Configure browser profile
        headless = browser_config_args.get("headless", False)
        window_size = {
            "width": browser_config_args.get("window_width", 1280),
            "height": browser_config_args.get("window_height", 1100)
        }
        viewport = {
            "width": browser_config_args.get("viewport_width", 1280),
            "height": browser_config_args.get("viewport_height", 1100)
        }
        
        # Domain parsing
        def parse_domains(s):
            if not s: return None
            # Handle both commas and newlines
            import re
            domains = [d.strip() for d in re.split(r'[,\n]', s) if d.strip()]
            return domains if domains else None

        # Resolve and create directories for recordings & debugging
        def resolve_dir(d):
            if not d: return None
            # If relative, join with current work dir
            abs_d = os.path.abspath(os.path.join(os.getcwd(), d))
            # Create if not exists
            os.makedirs(abs_d, exist_ok=True)
            return abs_d

        record_video_dir = resolve_dir(browser_config_args.get("record_video_dir"))
        traces_dir = resolve_dir(browser_config_args.get("traces_dir"))

        print(json.dumps({"type": "step", "text": f"🌐 Configuring browser (headless={headless}, size={window_size['width']}x{window_size['height']})..."}), flush=True)
        
        browser = Browser(
            headless=headless,
            window_size=window_size,
            viewport=viewport,
            keep_alive=browser_config_args.get("keep_alive"),
            enable_default_extensions=browser_config_args.get("enable_default_extensions", True),
            user_data_dir=browser_config_args.get("user_data_dir") or None,
            # Recording & Debugging
            record_video_dir=record_video_dir,
            record_video_size={
                "width": browser_config_args.get("record_video_width", 1280),
                "height": browser_config_args.get("record_video_height", 720)
            },
            record_video_framerate=browser_config_args.get("record_video_framerate", 30),
            record_har_path=browser_config_args.get("record_har_path") or None,
            traces_dir=traces_dir,
            record_har_content=browser_config_args.get("record_har_content", "embed"),
            record_har_mode=browser_config_args.get("record_har_mode", "full"),
            # Domain Filtering
            allowed_domains=parse_domains(browser_config_args.get("allowed_domains")),
            prohibited_domains=parse_domains(browser_config_args.get("prohibited_domains"))
        )

        step_count = [0]

        def step_callback(browser_state, agent_output, step_number):
            """Called after each agent step to report progress."""
            step_count[0] = step_number
            try:
                thought = ""
                if agent_output and agent_output.current_state:
                    thought = agent_output.current_state.next_goal or agent_output.current_state.thought or ""
                    thought = thought[:200]  # Truncate to prevent massive output

                msg = f"📍 Step {step_number}: {thought}" if thought else f"📍 Completed step {step_number}"
                print(json.dumps({"type": "step", "text": msg}), flush=True)
            except Exception:
                print(json.dumps({"type": "step", "text": f"📍 Completed step {step_number}"}), flush=True)

        print(json.dumps({"type": "step", "text": "🧠 Agent starting task reasoning..."}), flush=True)

        # Vision mode mapping
        use_vision = agent_config.get("use_vision", "auto")
        if use_vision == "true": use_vision = True
        elif use_vision == "false": use_vision = False

        # History parsing
        max_history = agent_config.get("max_history_items")
        if max_history == 0 or max_history == "": max_history = None

        agent = Agent(
            task=task,
            llm=llm,
            browser=browser,
            register_new_step_callback=step_callback,
            use_vision=use_vision,
            max_actions_per_step=agent_config.get("max_actions_per_step", 4),
            max_failures=agent_config.get("max_failures", 3),
            use_thinking=agent_config.get("use_thinking", True),
            flash_mode=agent_config.get("flash_mode", False),
            llm_timeout=agent_config.get("llm_timeout", 90),
            generate_gif=agent_config.get("generate_gif", False),
            # Performance & Limits
            max_history_items=max_history,
            step_timeout=agent_config.get("step_timeout", 120),
            directly_open_url=agent_config.get("directly_open_url", True),
            extend_system_message=SCREENSHOT_POLICY_MESSAGE
        )

        # Run the agent
        history = await agent.run()

        result_text = "Task completed successfully."
        if history and hasattr(history, 'final_result') and history.final_result():
            result_text = str(history.final_result())

        total_steps = step_count[0]
        
        # Extract metrics from history object as per documentation
        metrics = {
            "is_successful": False,
            "has_errors": False,
            "number_of_steps": total_steps,
            "total_duration_seconds": 0,
            "urls": [],
            "action_names": [],
            "screenshot_paths": [],
            "extracted_content": []
        }
        
        if history:
            try:
                metrics["is_successful"] = history.is_successful() if history.is_successful() is not None else False
                metrics["has_errors"] = history.has_errors()
                metrics["number_of_steps"] = history.number_of_steps()
                metrics["total_duration_seconds"] = history.total_duration_seconds()
                metrics["urls"] = list(set(history.urls())) # Get unique URLs
                metrics["action_names"] = history.action_names()
                metrics["screenshot_paths"] = history.screenshot_paths()
                
                # Check for errors and update result_text appropriately
                if metrics["has_errors"]:
                    errors = [str(e) for e in history.errors() if e]
                    if errors:
                        last_error = errors[-1]
                        if "429" in last_error or "quota" in last_error.lower() or "RESOURCE_EXHAUSTED" in last_error:
                            result_text = f"Task failed: 429 Quota Exceeded. You have exceeded your API quota.\n\nDetails: {last_error}"
                        else:
                            result_text = f"Task stopped due to an error: {last_error}"
                    else:
                        result_text = "Task failed to complete successfully."
                elif not metrics["is_successful"] and result_text == "Task completed successfully.":
                    result_text = "Task did not complete successfully (max steps reached or stopped)."

                # Get extracted content safely
                try:
                    metrics["extracted_content"] = [str(c) for c in history.extracted_content() if c]
                except:
                    metrics["extracted_content"] = []

            except Exception as e:
                print(json.dumps({"type": "step", "text": f"⚠️ Error extracting history metrics: {str(e)}"}), flush=True)

        print(json.dumps({"type": "step", "text": f"✅ Finished after {metrics['number_of_steps']} steps."}), flush=True)
        
        # If the runner detected errors via has_errors(), or if is_successful is False, report as failed
        is_successful = metrics.get("is_successful", False)
        has_errors = metrics.get("has_errors", False)
        final_status = "success" if is_successful and not has_errors else "failed"
        
        # Robust Fallback: if status is 'success' but the word 'failed' or similar is prominent in the result text, force to 'failed'
        # This catches cases where the engine thinks it's done but says "Verification failed" in the final text.
        lower_res = result_text.lower()
        if final_status == "success":
            failure_keywords = ["failed", "unable to verify", "could not find", "incorrect", "mismatch", "error:"]
            if any(keyword in lower_res for keyword in failure_keywords):
                final_status = "failed"
                metrics["is_successful"] = False # Sync metrics too

        # Ensure result_text accurately reflects failure if status is failed
        if final_status == "failed":
            # If the result text sounds too positive, prepend a clear failure indicator
            if not any(word in lower_res for word in ["failed", "error", "stopped", "incomplete", "unable", "could not"]):
                result_text = f"❌ TASK FAILED / INCOMPLETE: {result_text}"

        print(json.dumps({"type": "done", "text": result_text, "metrics": metrics, "status": final_status}), flush=True)

    except ImportError as e:
        print(json.dumps({"type": "error", "text": f"Missing dependency: {str(e)}. Ensure browser-use is installed in .venv."}), flush=True)
    except Exception as e:
        print(json.dumps({"type": "error", "text": f"Agent Error: {str(e)}\n{traceback.format_exc()}"}), flush=True)

if __name__ == "__main__":
    asyncio.run(main())
