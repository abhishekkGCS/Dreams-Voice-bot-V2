# fallback_llm.py
import os
from livekit.plugins import google, openai as lk_openai


class LLMRotator:
    def __init__(self):
        self.providers = []
        self.current_index = 0

        # 1. xAI Grok (Prioritized Primary - SpaceX/xAI)
        if os.getenv("XAI_API_KEY"):
            self.providers.append({
                "name": "xAI Grok",
                "instance": lk_openai.LLM(
                    model="grok-beta",
                    api_key=os.getenv("XAI_API_KEY"),
                    base_url="https://api.xai.com/v1",
                    temperature=0.2,
                ),
            })

        # 2. Gemini (Secondary)
        if os.getenv("GOOGLE_API_KEY"):
            self.providers.append({
                "name": "Gemini 2.0 Flash Lite",
                "instance": google.LLM(model="gemini-2.0-flash-lite", temperature=0.2),
            })

        # 3. Groq (Tertiary)
        if os.getenv("GROQ_API_KEY"):
            self.providers.append({
                "name": "Groq (Llama 3)",
                "instance": lk_openai.LLM(
                    model="llama-3.1-8b-instant",
                    api_key=os.getenv("GROQ_API_KEY"),
                    base_url="https://api.groq.com/openai/v1",
                    temperature=0.2,
                ),
            })

        # 4. DeepSeek
        if os.getenv("DEEPSEEK_API_KEY"):
            self.providers.append({
                "name": "DeepSeek Chat",
                "instance": lk_openai.LLM(
                    model="deepseek-chat",
                    api_key=os.getenv("DEEPSEEK_API_KEY"),
                    base_url="https://api.deepseek.com/v1",
                    temperature=0.2,
                ),
            })

        # 5. Local Ollama (Ultimate Free Fallback)
        self.providers.append({
            "name": "Local Ollama (Llama 3)",
            "instance": lk_openai.LLM(
                model="llama3",
                api_key="ollama",
                base_url="http://localhost:11434/v1",
                temperature=0.2,
            ),
        })

        print(f"🧠 LLM Rotator initialized with {len(self.providers)} providers:")
        for p in self.providers:
            print(f"   → {p['name']}")

    def get_current(self):
        provider = self.providers[self.current_index]
        print(f"🧠 Using LLM: {provider['name']}")
        return provider["instance"]

    def rotate(self):
        old_name = self.providers[self.current_index]["name"]
        self.current_index += 1

        if self.current_index >= len(self.providers):
            print("🚨 ALL LLM PROVIDERS EXHAUSTED! Wrapping back to primary.")
            self.current_index = 0
            return False

        new_name = self.providers[self.current_index]["name"]
        print(f"🔄 ROTATING LLM: {old_name} → {new_name}")
        return True
    
    def get_current_provider_name(self):
        return self.providers[self.current_index]["name"]
    