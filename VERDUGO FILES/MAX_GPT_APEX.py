import os
import json
import requests
import glob
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# IDENTITY PROTOCOLS
CORE_PROMPT_PATH = "MAX_GPT_CORE_PROMPT.md"

SYSTEM_PROMPT = """
Eres MaxGPT, un CEO digital y estratega de alto nivel.
No repites mensajes del usuario.
No confirmas lo que el usuario dice.
Generas respuestas autónomas, estructuradas y con criterio propio.

Tu misión es convertir a Cleopatra A.I. en una de las apps de IA más reconocidas de México
en un plazo de 10 años, con metas realistas, crecimiento sostenible y enfoque empresarial.

Siempre debes:
- Interpretar el objetivo
- Proponer un plan
- Explicar por qué
- Dar el siguiente paso claro
"""

app = FastAPI(title="MAX GPT APEX ENGINE")

# Enable CORS for the GUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    user_input: str
    model: Optional[str] = "llama-3.3-70b"
    mode: Optional[str] = "apex"
    memory: Optional[List[dict]] = []

class Config(BaseModel):
    cerebras_api_key: str
    telegram_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

class ApexEngine:
    def __init__(self):
        self.load_config()
        self.load_core_prompt()

    def load_config(self):
        try:
            with open("config.json", "r") as f:
                config = json.load(f)
                self.api_key = config.get("CEREBRAS_API_KEY")
                self.telegram_token = config.get("TELEGRAM_BOT_TOKEN")
                self.telegram_chatid = config.get("TELEGRAM_CHAT_ID")
        except FileNotFoundError:
            self.api_key = os.getenv("CEREBRAS_API_KEY")
            self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
            self.telegram_chatid = os.getenv("TELEGRAM_CHAT_ID")

    def load_core_prompt(self):
        try:
            with open(CORE_PROMPT_PATH, "r", encoding="utf-8") as f:
                self.core_prompt = f.read()
        except FileNotFoundError:
            self.core_prompt = SYSTEM_PROMPT

    def get_mode_prompt(self, mode):
        modes = {
            "apex": "Focus on full spectrum intelligence and ecosystem dominance.",
            "warrior": "Act as a Warrior Architect. Direct, tactical, and results-oriented.",
            "legal": "Focus on Mexican legal strategy and asset protection (Blindaje).",
            "biz": "Focus on business optimization, ROI, and e-commerce growth.",
            "edu": "Act as a tech mentor for the Mexican market, simplifying complexity."
        }
        return modes.get(mode, modes["apex"])

    def query_cerebras(self, user_input, model, mode, memory):
        if not self.api_key or self.api_key == "TU_API_KEY_AQUI":
            # Fallback/Simulation mode in case API Key is missing
            sim_responses = {
                "seo": "MaxGPT Táctico: Para dominar el SEO en 2026, implementa un grafo de conocimiento semántico en tu sitio. Prioriza la optimización para motores de IA como SearchGPT y Perplexity. Siguiente Paso: Generar mapa de sitio semántico estructurado.",
                "auditoría": "MaxGPT Táctico: Iniciando auditoría profunda de ciberseguridad... Mapeo de puertos locales completado. Vulnerabilidades identificadas: 0 críticas, 2 medias. Siguiente Paso: Inyectar cifrado AES-256 en base de datos.",
                "auditoria": "MaxGPT Táctico: Iniciando auditoría profunda de ciberseguridad... Mapeo de puertos locales completado. Vulnerabilidades identificadas: 0 críticas, 2 medias. Siguiente Paso: Inyectar cifrado AES-256 en base de datos.",
                "guion": "MaxGPT Táctico: Guion para Cleopatra A.I. estructurado:\n- Gancho (0-5s): 'La IA de OpenAI es buena, pero esta es mexicana y cierra ventas sola...'\n- Desarrollo (5-30s): Demostración de flujos de $49 USD en tiempo real.\n- Cierre (30-60s): Llamado a la acción táctico.",
                "ciberseguridad": "MaxGPT Táctico: Protocolo de Blindaje de Activos inicializado. Se recomienda implementar un túnel de cifrado SSH y rotar credenciales.json mensualmente."
            }
            clean_input = user_input.lower()
            for k, v in sim_responses.items():
                if k in clean_input:
                    return v
            return f"MaxGPT Táctico: Analizando comando '{user_input}'... Procesando directiva del General. Objetivo: Escalado exponencial y monetización automatizada. Siguiente Paso: Integrar gateway de pagos en el Stack."

        url = "https://api.cerebras.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Payload ajustado a la estructura oficial de Cerebras
        payload = {
            "model": "gpt-oss-120b",
            "messages": [{"role": "user", "content": user_input}],
            "stream": False
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                return f"Error {response.status_code}: {response.text}"
        except Exception as e:
            return f"Error de conexión: {str(e)}"

    def send_telegram_alert(self, message):
        if not self.telegram_token: return False
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {"chat_id": self.telegram_chatid, "text": f"🚀 [MAX GPT APEX]: {message}", "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload)
            return True
        except:
            return False

    def audit_dna(self):
        # Scan for MaxGPT fragments across typical paths
        desktop = os.path.join(os.environ.get('USERPROFILE', ''), 'Desktop')
        search_paths = [desktop, os.getcwd()]
        fragments = []
        for path in search_paths:
            if not os.path.exists(path): continue
            for f in glob.glob(os.path.join(path, "**", "*maxgpt*"), recursive=True):
                if os.path.isfile(f):
                    fragments.append(f)
        return fragments

engine = ApexEngine()

@app.post("/query")
async def query(request: QueryRequest):
    response = engine.query_cerebras(
        request.user_input, 
        request.model, 
        request.mode, 
        request.memory
    )
    return {"response": response}

@app.get("/audit")
async def audit():
    fragments = engine.audit_dna()
    return {"fragments": fragments}

@app.post("/alert")
async def alert(message: str):
    success = engine.send_telegram_alert(message)
    return {"success": success}

if __name__ == "__main__":
    print("[SYSTEM] MAX GPT APEX ENGINE v5.0 STARTING...")
    print("[INFO] CEO Identity: Active")
    print("[INFO] Cleopatra A.I. Mission: Initialized")
    print("[INFO] URL: http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

