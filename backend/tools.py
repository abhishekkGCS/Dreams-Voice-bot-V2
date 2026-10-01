# tools.py
import pygetwindow as gw
import json
import asyncio
from datetime import datetime
from livekit.agents import llm, log
from ddgs import DDGS
import psutil
import pyautogui
from PIL import ImageGrab
import pytesseract
from AppOpener import open as open_app
import subprocess
import pyperclip
import time
from app_controller import AppController
from system_monitor import SystemMonitor
from memory import MemoryManager, WorkingMemory

# Point Python to the Tesseract software you installed
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
logger = log.logger

class JarvisTools(llm.Toolset):
    def __init__(self, working_memory: WorkingMemory | None = None, metrics=None):
        super().__init__(id="jarvis_tools")
        self.memory = MemoryManager()
        self.working_memory = working_memory or WorkingMemory()
        self.metrics = metrics

    # --- SYSTEM & UTILITIES ---

    @llm.function_tool(description="Get the current time and date.")
    async def get_time(self):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: get_time")
            now = datetime.now().strftime("%I:%M %p on %A, %B %d")
            return f"The current time is {now}"
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("get_time", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Check full system performance metrics: CPU load, RAM memory usage, and primary disk storage.")
    async def get_system_info(self):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: get_system_info")
            return await asyncio.to_thread(SystemMonitor.get_full_overview)
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("get_system_info", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Check dedicated GPU status, including GPU load, temperature, and VRAM usage.")
    async def get_gpu_info(self):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: get_gpu_info")
            return await asyncio.to_thread(SystemMonitor.get_gpu_status)
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("get_gpu_info", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Check storage and free disk space on the computer.")
    async def get_disk_space(self):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: get_disk_space")
            return await asyncio.to_thread(SystemMonitor.get_disk_status)
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("get_disk_space", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Control media playback on the computer (play, pause, next, previous, mute).")
    async def media_control(self, action: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: media_control", extra={"action": action})
            valid_actions = {
                "play": "playpause",
                "pause": "playpause",
                "next": "nexttrack",
                "previous": "prevtrack",
                "mute": "volumemute",
            }
            cmd = valid_actions.get(action.lower().strip())
            if not cmd:
                return f"I don't know how to perform the media action: {action}. Supported actions are play, pause, next, previous, and mute."
            pyautogui.press(cmd)
            return f"Successfully executed media action: {action}"
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("media_control", (time.perf_counter() - start) * 1000, success)

    # --- SCREEN & CONTEXT TOOLS ---

    @llm.function_tool(description="Read all the visible text currently on the user's computer screen.")
    async def get_screen_text(self):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: get_screen_text")
            try:
                def perform_ocr():
                    screenshot = ImageGrab.grab().convert("L")
                    text = pytesseract.image_to_string(screenshot)
                    return text.strip()[:3000]
                screen_text = await asyncio.to_thread(perform_ocr)
                if screen_text:
                    return f"Here is the raw text currently visible on the user's screen:\n{screen_text}"
                return "The screen appears to be blank or I could not detect any readable text."
            except Exception as e:
                logger.error("get_screen_text failed", exc_info=e)
                return "I encountered an error trying to read the screen."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("get_screen_text", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Check what application or window the user is currently looking at on their screen.")
    async def get_active_window(self):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: get_active_window")
            try:
                active_window = gw.getActiveWindow()
                if active_window and active_window.title:
                    return f"The user is currently looking at a window titled: '{active_window.title}'"
                return "The user is on the desktop or I cannot read the active window title."
            except Exception as e:
                logger.error("get_active_window failed", exc_info=e)
                return "I was unable to read the active window."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("get_active_window", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Read the text currently highlighted or selected by the user's mouse cursor.")
    async def get_cursor_context(self):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: get_cursor_context")
            try:
                def grab_highlighted_text():
                    previous_clipboard = pyperclip.paste()
                    pyperclip.copy("")
                    pyautogui.hotkey("ctrl", "c")
                    time.sleep(0.1)
                    selected_text = pyperclip.paste().strip()
                    if not selected_text and previous_clipboard:
                        pyperclip.copy(previous_clipboard)
                    return selected_text
                selected = await asyncio.to_thread(grab_highlighted_text)
                if selected:
                    return f"Text currently selected by the user:\n\"\"\"\n{selected[:2000]}\n\"\"\""
                return "No text appears to be selected or highlighted right now."
            except Exception as e:
                logger.error("get_cursor_context failed", exc_info=e)
                return "I was unable to read the highlighted text."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("get_cursor_context", (time.perf_counter() - start) * 1000, success)

    # --- APPLICATION & BROWSER CONTROL ---

    @llm.function_tool(description="Launch or bring an application to the foreground. Resolves 'it' to the currently active app.")
    async def open_application(self, app_name: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: open_application", extra={"app_name": app_name})
            target = self.working_memory.current_app if app_name.lower().strip() in ["it", "this", "app"] else app_name
            if not target:
                return "I don't know which application you're referring to. Please specify the name."
            result = await asyncio.to_thread(AppController.launch_or_focus, target)
            self.working_memory.set_app(target)
            return result
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("open_application", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Close or quit a running application. If the user says 'close it', closes the currently active app.")
    async def close_application(self, app_name: str = "it"):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: close_application", extra={"app_name": app_name})
            target = self.working_memory.current_app if app_name.lower().strip() in ["it", "this", "app", ""] else app_name
            if not target:
                return "I don't have an active application in memory to close. Please tell me the name of the app."
            result = await asyncio.to_thread(AppController.close_app, target)
            self.working_memory.clear_app(target)
            return result
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("close_application", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Check what app, project, or task is currently held in the assistant's working memory.")
    async def get_active_context(self):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: get_active_context")
            return self.working_memory.get_summary()
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("get_active_context", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Open a new tab in the user's web browser and navigate to a specific website.")
    async def open_website(self, url: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: open_website", extra={"url": url})
            import webbrowser
            try:
                if not url.startswith("http"):
                    url = "https://" + url
                webbrowser.open_new_tab(url)
                return f"I have opened a new tab and navigated to {url}."
            except Exception as e:
                logger.error("open_website failed", exc_info=e)
                return f"I could not open the website: {url}."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("open_website", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Open the user's web browser and perform a Google Search for them.")
    async def search_google_browser(self, query: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: search_google_browser", extra={"query": query})
            import webbrowser
            import urllib.parse
            try:
                encoded_query = urllib.parse.quote_plus(query)
                search_url = f"https://www.google.com/search?q={encoded_query}"
                webbrowser.open_new_tab(search_url)
                return f"I have opened a Google search for {query} on your screen."
            except Exception as e:
                logger.error("search_google_browser failed", exc_info=e)
                return "I could not perform the Google search."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("search_google_browser", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Type text directly onto the user's screen using their virtual keyboard and press Enter. Useful for searching inside a specific website.")
    async def type_and_search(self, text_to_type: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: type_and_search", extra={"text": text_to_type})
            try:
                def simulate_typing():
                    pyautogui.write(text_to_type, interval=0.05)
                    pyautogui.press("enter")
                await asyncio.to_thread(simulate_typing)
                return f"I have successfully typed '{text_to_type}' and pressed Enter."
            except Exception as e:
                logger.error("type_and_search failed", exc_info=e)
                return "I encountered an error trying to type on the keyboard."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("type_and_search", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Play a specific song, artist, or video on YouTube.")
    async def play_music_youtube(self, search_query: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: play_music_youtube", extra={"search_query": search_query})
            import webbrowser
            try:
                def get_youtube_link():
                    with DDGS() as ddgs:
                        results = list(ddgs.text(f"site:youtube.com {search_query}", max_results=1))
                        return results[0]["href"] if results else None
                url = await asyncio.to_thread(get_youtube_link)
                if url:
                    webbrowser.open(url)
                    return f"I have opened a new tab and started playing {search_query} on YouTube."
                return f"I couldn't find a YouTube link for {search_query}."
            except Exception as e:
                logger.error("play_music_youtube failed", exc_info=e)
                return "I had trouble accessing YouTube right now."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("play_music_youtube", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Search the web for real-time news, facts, or information.")
    async def search_web(self, query: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: search_web", extra={"query": query})
            try:
                def do_search():
                    with DDGS() as ddgs:
                        return list(ddgs.text(query, max_results=3))
                results = await asyncio.to_thread(do_search)
                if not results:
                    return f"I couldn't find any information on '{query}'."
                formatted = "Raw Web Data:\n"
                for i, res in enumerate(results):
                    formatted += f"\nResult {i+1}: {res['title']}\nSnippet: {res['body']}\n"
                return formatted
            except Exception as e:
                logger.error("search_web tool failed", exc_info=e)
                return "I am having trouble accessing the internet right now."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("search_web", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Calculate math equations.")
    async def calculator(self, equation: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: calculator", extra={"equation": equation})
            try:
                import ast
                expr = ast.parse(equation, mode="eval")
                allowed = {
                    ast.Expression, ast.Constant, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub,
                    ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd, ast.FloorDiv,
                    ast.LShift, ast.RShift, ast.BitXor, ast.BitAnd, ast.BitOr, ast.Invert,
                }
                for node in ast.walk(expr):
                    if type(node) not in allowed:
                        raise ValueError("Unsupported expression")
                result = eval(compile(expr, filename="<ast>", mode="eval"), {}, {})
                return f"The answer is {result}"
            except Exception:
                return "I could not calculate that."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("calculator", (time.perf_counter() - start) * 1000, success)

    # --- MEMORY TOOLS (REAL MONGODB) ---

    @llm.function_tool(description="Save an important fact or preference about the user to long-term memory.")
    async def save_user_fact(self, fact: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: save_user_fact", extra={"fact": fact})
            await self.memory.save_fact(fact)
            return "Fact saved successfully to long-term memory."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("save_user_fact", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Look up past notes or facts about the user.")
    async def recall_user_facts(self):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: recall_user_facts")
            facts = await self.memory.get_facts()
            if not facts:
                return "No past memories found."
            return json.dumps(facts)
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("recall_user_facts", (time.perf_counter() - start) * 1000, success)

    # --- PROJECT MANAGER TOOLS (REAL MONGODB & WORKING MEMORY) ---

    @llm.function_tool(description="Create a new empty project workspace.")
    async def create_project(self, project_name: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: create_project", extra={"project_name": project_name})
            collection = self.memory.db["projects"]
            existing = await collection.find_one({"name": project_name})
            if existing:
                return f"Project '{project_name}' already exists."
            await collection.insert_one({"name": project_name, "tasks": []})
            self.working_memory.set_project(project_name)
            return f"Project '{project_name}' created successfully in MongoDB."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("create_project", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Add a new task to an existing project with a deadline and priority.")
    async def add_task(self, project_name: str, task_name: str, deadline: str, priority: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: add_task", extra={"project": project_name, "task": task_name})
            collection = self.memory.db["projects"]
            project = await collection.find_one({"name": project_name})
            if not project:
                return f"Error: Project '{project_name}' does not exist. Tell the user to create it first."
            new_task = {
                "name": task_name,
                "deadline": deadline,
                "priority": priority,
                "status": "pending",
            }
            await collection.update_one({"name": project_name}, {"$push": {"tasks": new_task}})
            self.working_memory.set_project(project_name)
            self.working_memory.set_task(task_name)
            return f"Task added to project '{project_name}' successfully."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("add_task", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="Update the status of a specific task.")
    async def update_task_status(self, project_name: str, task_name: str, status: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: update_task_status", extra={"project": project_name, "task": task_name, "status": status})
            collection = self.memory.db["projects"]
            result = await collection.update_one(
                {"name": project_name, "tasks.name": task_name},
                {"$set": {"tasks.$.status": status}},
            )
            if result.modified_count > 0:
                self.working_memory.set_task(task_name)
                return f"Task '{task_name}' marked as {status}."
            return f"Could not find task '{task_name}' in project '{project_name}'."
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("update_task_status", (time.perf_counter() - start) * 1000, success)

    @llm.function_tool(description="List all tasks for a specific project.")
    async def list_tasks(self, project_name: str):
        start = time.perf_counter()
        success = True
        try:
            logger.info("executing tool: list_tasks", extra={"project": project_name})
            collection = self.memory.db["projects"]
            project = await collection.find_one({"name": project_name})
            if not project:
                return f"Project '{project_name}' does not exist."
            tasks = project.get("tasks", [])
            if not tasks:
                return f"There are no tasks in project '{project_name}'."
            self.working_memory.set_project(project_name)
            return json.dumps(tasks)
        except Exception as e:
            success = False
            raise e
        finally:
            if self.metrics: self.metrics.record_tool("list_tasks", (time.perf_counter() - start) * 1000, success)