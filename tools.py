

"""
The Theory (How Function Calling Works):
JSON Schemas: Gemini cannot actually browse the web or run Python code. Instead, we give Gemini a JSON document that describes the tools we have available (e.g., "I have a tool called get_time").
The Routing Decision: When you ask a question, Gemini makes a routing decision: "Can I answer this from my training data, OR should I output a JSON string asking the server to run a tool?"
Tool Execution: If Gemini outputs a tool request, the LiveKit framework intercepts it, pauses the audio, runs your actual Python function, takes the result (like the current time), injects it back into the context window, and tells Gemini: "Here is the data, now formulate a spoken response for the user."
LiveKit makes this incredibly easy. You just write normal Python classes and use the @llm.function_tool decorator. LiveKit handles generating the JSON schemas and executing the routing automatically
"""



"""
The Theory: How AI "Remembers"
LLMs can't natively remember anything between sessions. To solve this, we use two techniques:

Short-Term Memory (Redis): If you disconnect from the room and reconnect 5 minutes later, you shouldn't have to introduce yourself again. We serialize the ChatContext (the array of messages) and save it to Redis with a 1-hour expiration. When you connect, we pull it from Redis and hand it back to the LiveKit Agent.
Long-Term Memory (MongoDB): We cannot shove 6 months of conversation logs into the LLM context window—it would be too slow and cost a fortune in API tokens.
The Solution: We give Jarvis Memory Tools. We teach him to automatically extract facts. If you say, "By the way, my name is Alex," Jarvis uses a tool to save { "name": "Alex" } to MongoDB.
The Injection: Next week, when you connect to a new room, we query MongoDB before Jarvis says hello, and we inject those facts directly into his system prompt: "You are talking to Alex. He likes Python."
"""

# tools.py
import pygetwindow as gw
import json
import asyncio
from datetime import datetime
from livekit.agents import llm, log
from ddgs import DDGS
import psutil
import pyautogui # Real web search
from memory import MemoryManager # Real Mongo database manager
from PIL import ImageGrab
import pytesseract
from AppOpener import open as open_app
import subprocess
import pyperclip
from app_controller import AppController
from system_monitor import SystemMonitor


# Point Python to the Tesseract software you just installed
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
logger = log.logger

class JarvisTools(llm.Toolset):
    def __init__(self):
        super().__init__(id="jarvis_tools")
        # Instantiate memory connection (connects to real Mongo & Redis)
        self.memory = MemoryManager()

    # --- SYSTEM & UTILITIES ---

    @llm.function_tool(description="Get the current time and date.")
    async def get_time(self):
        
        logger.info("executing tool: get_time")
        now = datetime.now().strftime("%I:%M %p on %A, %B %d")
        return f"The current time is {now}"
    
    @llm.function_tool(description="Check full system performance metrics: CPU load, RAM memory usage, and primary disk storage.")
    async def get_system_info(self):
        logger.info("executing tool: get_system_info")
        import asyncio
        return await asyncio.to_thread(SystemMonitor.get_full_overview)

    @llm.function_tool(description="Check dedicated GPU status, including GPU load, temperature, and VRAM usage.")
    async def get_gpu_info(self):
        logger.info("executing tool: get_gpu_info")
        import asyncio
        return await asyncio.to_thread(SystemMonitor.get_gpu_status)

    @llm.function_tool(description="Check storage and free disk space on the computer.")
    async def get_disk_space(self):
        logger.info("executing tool: get_disk_space")
        import asyncio
        return await asyncio.to_thread(SystemMonitor.get_disk_status)

    @llm.function_tool(description="Control media playback on the computer (play, pause, next, previous, mute).")
    async def media_control(self, action: str):
        logger.info("executing tool: media_control", extra={"action": action})
        
        # Map the LLM's chosen action to the actual Windows media key commands
        valid_actions = {
            "play": "playpause",
            "pause": "playpause",
            "next": "nexttrack",
            "previous": "prevtrack",
            "mute": "volumemute"
        }
        
        # Normalize the action string to lowercase
        cmd = valid_actions.get(action.lower().strip())
        
        if not cmd:
            return f"I don't know how to perform the media action: {action}. Supported actions are play, pause, next, previous, and mute."
            
        # Simulate pressing the media key on the keyboard
        pyautogui.press(cmd)
        return f"Successfully executed media action: {action}"
    
    # --- SCREEN & WINDOW TOOLS ---
    # # Reading the screen and active window is useful for context-aware responses, especially when the user is multitasking.
    # @llm.function_tool(description="Read all the visible text currently on the user's computer screen.")
    # async def get_screen_text(self):
    #     logger.info("executing tool: get_screen_text")
    #     import asyncio
        
    #     try:
    #         def perform_ocr():
    #             # Take an invisible screenshot of the main monitor
    #             screenshot = ImageGrab.grab()
    #             # Extract the text using Tesseract
    #             text = pytesseract.image_to_string(screenshot)
    #             return text.strip()
    #         # Run this in a background thread to prevent audio stutter
    #         screen_text = await asyncio.to_thread(perform_ocr)
            
    #         if screen_text:
    #             return f"Here is the raw text currently visible on the user's screen:\n{screen_text}"
    #         else:
    #             return "The screen appears to be blank or I could not detect any readable text."
                
    #     except Exception as e:
    #         logger.error("get_screen_text failed", exc_info=e)
    #         return "I encountered an error trying to read the screen."     
    
    @llm.function_tool(description="Read all the visible text currently on the user's computer screen.")
    async def get_screen_text(self):
        logger.info("executing tool: get_screen_text")
        import asyncio
        
        try:
            def perform_ocr():
                # Take an invisible screenshot of the main monitor
                screenshot = ImageGrab.grab()
                
                # FIX 1: Convert image to grayscale to help Tesseract read Dark Mode
                screenshot = screenshot.convert('L')
                
                # Extract the text using Tesseract
                text = pytesseract.image_to_string(screenshot)
                
                # FIX 2: Limit text to 3000 characters so it doesn't crash the LLM memory
                return text.strip()[:3000]
            # Run this in a background thread to prevent audio stutter
            screen_text = await asyncio.to_thread(perform_ocr)
            
            if screen_text:
                return f"Here is the raw text currently visible on the user's screen:\n{screen_text}"
            else:
                return "The screen appears to be blank or I could not detect any readable text."
                
        except Exception as e:
            logger.error("get_screen_text failed", exc_info=e)
            return "I encountered an error trying to read the screen."
        
        
    @llm.function_tool(description="Launch or bring an application to the foreground (e.g. spotify, notepad, chrome, code, calculator).")
    async def open_application(self, app_name: str):
        logger.info("executing tool: open_application", extra={"app_name": app_name})
        import asyncio
        return await asyncio.to_thread(AppController.launch_or_focus, app_name)

    @llm.function_tool(description="Close or quit a running application (e.g. close notepad, close calculator).")
    async def close_application(self, app_name: str):
        logger.info("executing tool: close_application", extra={"app_name": app_name})
        import asyncio
        return await asyncio.to_thread(AppController.close_app, app_name)
       
    @llm.function_tool(description="Open a new tab in the user's web browser and navigate to a specific website.")
    async def open_website(self, url: str):
        logger.info("executing tool: open_website", extra={"url": url})
        import webbrowser
        
        try:
            # If the AI just says "google.com", we need to add the https://
            if not url.startswith("http"):
                url = "https://" + url
                
            # Pop open a new tab!
            webbrowser.open_new_tab(url)
            return f"I have opened a new tab and navigated to {url}."
            
        except Exception as e:
            logger.error("open_website failed", exc_info=e)
            return f"I could not open the website: {url}."
    
    @llm.function_tool(description="Play a specific song, artist, or video on YouTube.")
    async def play_music_youtube(self, search_query: str):
        logger.info("executing tool: play_music_youtube", extra={"search_query": search_query})
        import webbrowser
        import asyncio
        from ddgs import DDGS
        
        try:
            def get_youtube_link():
                # Search DuckDuckGo specifically for a YouTube link
                with DDGS() as ddgs:
                    results = list(ddgs.text(f"site:youtube.com {search_query}", max_results=1))
                    if results:
                        return results[0]['href']
                    return None
            
            # Run the search in the background
            url = await asyncio.to_thread(get_youtube_link)
            
            if url:
                # Open the default web browser to the YouTube video!
                webbrowser.open(url)
                return f"I have opened a new tab and started playing {search_query} on YouTube."
            else:
                return f"I couldn't find a YouTube link for {search_query}."
                
        except Exception as e:
            logger.error("play_music_youtube failed", exc_info=e)
            return "I had trouble accessing YouTube right now."
    
    @llm.function_tool(description="Search the web for real-time news, facts, or information.")
    async def search_web(self, query: str):
        logger.info("executing tool: search_web", extra={"query": query})
        try:
            # We wrap the synchronous DDGS search in a background thread 
            # so it doesn't freeze the LiveKit audio loop!
            def do_search():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=3))
                    
            results = await asyncio.to_thread(do_search)
            
            if not results:
                return f"I couldn't find any information on '{query}'."
            formatted_results = "Raw Web Data:\n"
            for i, res in enumerate(results):
                formatted_results += f"\nResult {i+1}: {res['title']}\nSnippet: {res['body']}\n"
            return formatted_results
            
        except Exception as e:
            logger.error("search_web tool failed", exc_info=e)
            return "I am having trouble accessing the internet right now."
        
    @llm.function_tool(description="Open the user's web browser and perform a Google Search for them.")
    async def search_google_browser(self, query: str):
        logger.info("executing tool: search_google_browser", extra={"query": query})
        import webbrowser
        import urllib.parse
        
        try:
            # Format the user's spoken words into a proper Google URL
            # e.g. "cute cats" -> "cute+cats"
            encoded_query = urllib.parse.quote_plus(query)
            search_url = f"https://www.google.com/search?q={encoded_query}"
            
            # Pop open the new tab directly to the results!
            webbrowser.open_new_tab(search_url)
            return f"I have opened a Google search for {query} on your screen."
            
        except Exception as e:
            logger.error("search_google_browser failed", exc_info=e)
            return "I could not perform the Google search."
    
    @llm.function_tool(description="Type text directly onto the user's screen using their virtual keyboard and press Enter. Useful for searching inside a specific website.")
    async def type_and_search(self, text_to_type: str):
        logger.info("executing tool: type_and_search", extra={"text": text_to_type})
        import pyautogui
        import asyncio
        
        try:
            def simulate_typing():
                # Type the text just like a human typing on a keyboard
                pyautogui.write(text_to_type, interval=0.05)
                # Press the Enter key to submit the search
                pyautogui.press('enter')
                
            # Run in a background thread
            await asyncio.to_thread(simulate_typing)
            return f"I have successfully typed '{text_to_type}' and pressed Enter."
            
        except Exception as e:
            logger.error("type_and_search failed", exc_info=e)
            return "I encountered an error trying to type on the keyboard."

    @llm.function_tool(description="Calculate math equations.")
    async def calculator(self, equation: str):
        logger.info("executing tool: calculator", extra={"equation": equation})
        try:
            import ast

            expr = ast.parse(equation, mode="eval")

            allowed_nodes = {
                ast.Expression,
                ast.Constant,
                ast.BinOp,
                ast.UnaryOp,
                ast.Add,
                ast.Sub,
                ast.Mult,
                ast.Div,
                ast.Pow,
                ast.Mod,
                ast.USub,
                ast.UAdd,
                ast.FloorDiv,
                ast.LShift,
                ast.RShift,
                ast.BitXor,
                ast.BitAnd,
                ast.BitOr,
                ast.Invert,
            }

            for node in ast.walk(expr):
                if type(node) not in allowed_nodes:
                    raise ValueError("Unsupported expression")

            result = eval(compile(expr, filename="<ast>", mode="eval"), {}, {})
            return f"The answer is {result}"
        except Exception:
            return "I could not calculate that."
        
    @llm.function_tool(description="Read the text currently highlighted or selected by the user's mouse cursor.")
    async def get_cursor_context(self):
        logger.info("executing tool: get_cursor_context")
        import asyncio
        import pyautogui
        import pyperclip
        import time

        try:
            def grab_highlighted_text():
                # Step 1: Save existing clipboard content so we do not overwrite the user's data
                previous_clipboard = pyperclip.paste()

                # Step 2: Clear clipboard temporarily to detect if new text is copied
                pyperclip.copy("")

                # Step 3: Trigger Ctrl+C to copy whatever is currently selected
                pyautogui.hotkey("ctrl", "c")
                time.sleep(0.1)  # Brief pause for Windows to process the clipboard event

                # Step 4: Grab the newly highlighted text
                selected_text = pyperclip.paste().strip()

                # Step 5: Restore the user's previous clipboard data if nothing was selected
                if not selected_text and previous_clipboard:
                    pyperclip.copy(previous_clipboard)

                return selected_text

            # Execute in a thread pool so audio playback does not block
            selected = await asyncio.to_thread(grab_highlighted_text)

            if selected:
                return f"Text currently selected by the user:\n\"\"\"\n{selected[:2000]}\n\"\"\""
            else:
                return "No text appears to be selected or highlighted right now."

        except Exception as e:
            logger.error("get_cursor_context failed", exc_info=e)
            return "I was unable to read the highlighted text."
    

    # --- MEMORY TOOLS (REAL MONGODB) ---

    @llm.function_tool(description="Save an important fact or preference about the user to long-term memory.")
    async def save_user_fact(self, fact: str):
        logger.info("executing tool: save_user_fact", extra={"fact": fact})
        await self.memory.save_fact(fact)
        return "Fact saved successfully to long-term memory."

    @llm.function_tool(description="Look up past notes or facts about the user.")
    async def recall_user_facts(self):
        logger.info("executing tool: recall_user_facts")
        facts = await self.memory.get_facts()
        if not facts:
            return "No past memories found."
        return json.dumps(facts)

    # --- PROJECT MANAGER TOOLS (REAL MONGODB) ---

    @llm.function_tool(description="Create a new empty project workspace.")
    async def create_project(self, project_name: str):
        logger.info("executing tool: create_project", extra={"project_name": project_name})
        collection = self.memory.db["projects"]
        
        # Check if project exists in real Mongo
        existing = await collection.find_one({"name": project_name})
        if existing:
            return f"Project '{project_name}' already exists."

        await collection.insert_one({"name": project_name, "tasks": []})
        return f"Project '{project_name}' created successfully in MongoDB."

    @llm.function_tool(description="Add a new task to an existing project with a deadline and priority.")
    async def add_task(
        self,
        project_name: str,
        task_name: str,
        deadline: str,
        priority: str,
    ):
        logger.info("executing tool: add_task", extra={"project": project_name, "task": task_name})
        collection = self.memory.db["projects"]
        
        project = await collection.find_one({"name": project_name})
        if not project:
            return f"Error: Project '{project_name}' does not exist. Tell the user to create it first."

        new_task = {
            "name": task_name,
            "deadline": deadline,
            "priority": priority,
            "status": "pending"
        }
        
        # Push task into the project's array in MongoDB
        await collection.update_one({"name": project_name}, {"$push": {"tasks": new_task}})
        return f"Task added to project '{project_name}' successfully."

    @llm.function_tool(description="Update the status of a specific task.")
    async def update_task_status(
        self,
        project_name: str,
        task_name: str,
        status: str,
    ):
        logger.info("executing tool: update_task_status", extra={"project": project_name, "task": task_name, "status": status})
        collection = self.memory.db["projects"]
        
        # Update the task status inside the array
        result = await collection.update_one(
            {"name": project_name, "tasks.name": task_name},
            {"$set": {"tasks.$.status": status}}
        )
        
        if result.modified_count > 0:
            return f"Task '{task_name}' marked as {status}."
        return f"Could not find task '{task_name}' in project '{project_name}'."

    @llm.function_tool(description="List all tasks for a specific project.")
    async def list_tasks(
        self,
        project_name: str,
    ):
        logger.info("executing tool: list_tasks", extra={"project": project_name})
        collection = self.memory.db["projects"]
        
        project = await collection.find_one({"name": project_name})
        if not project:
            return f"Project '{project_name}' does not exist."

        tasks = project.get("tasks", [])
        if not tasks:
            return f"There are no tasks in project '{project_name}'."

        return json.dumps(tasks)
    
    
    # Giving bot eyes
    # This tool will help you tell which windows is currently active or opened.
    @llm.function_tool(description="Check what application or window the user is currently looking at on their screen.")
    async def get_active_window(self):
        logger.info("executing tool: get_active_window")
        try:
            # Grab the window that is currently active/focused
            active_window = gw.getActiveWindow()
            
            if active_window and active_window.title:
                return f"The user is currently looking at a window titled: '{active_window.title}'"
            else:
                return "The user is on the desktop or I cannot read the active window title."
                
        except Exception as e:
            logger.error("get_active_window failed", exc_info=e)
            return "I was unable to read the active window."