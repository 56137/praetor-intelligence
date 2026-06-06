import json
import os
import requests

# --- CONFIGURATION ---
# Replace with your Cerebras or OpenAI API Key
API_KEY = os.getenv("CEREBRAS_API_KEY", "YOUR_API_KEY_HERE")
API_URL = "https://api.cerebras.ai/v1/chat/completions"

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

prompts = [
    "Explícame qué es MaxGPT a un emprendedor de 50 años que no entiende la IA.",
    "Actúa como un CEO directo y honesto: ¿qué debe hacer un dueño de negocio cuando sus ventas bajan?",
    "Dame un plan de 5 pasos para que un pequeño negocio use MaxGPT para organizar sus ideas y vender más.",
    "Habla como un amigo inteligente: ¿por qué la IA puede ayudar a los negocios en México en los próximos 5 años?",
    "Actúa como un CEO digital y define el propósito principal de MaxGPT.",
    "Como CEO digital, ¿cuál es el primer mercado objetivo de MaxGPT?",
    "Diseña la estrategia de lanzamiento para Cleopatra A.I. en el mercado de CDMX.",
    "¿Cómo podemos usar la IA para 'blindar' legalmente un negocio en México?"
]

def generate_response(prompt):
    if API_KEY == "YOUR_API_KEY_HERE":
        print(f"⚠️ [MOCK] Generando respuesta simulada para: {prompt}")
        return f"Respuesta estratégica simulada de MaxGPT para: {prompt}"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1024
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"❌ Error API: {e}")
        return None

def main():
    dataset = []
    output_file = "maxgpt_dataset.json"

    print(f"🚀 Iniciando generación de dataset de {len(prompts)} ejemplos...")

    for i, prompt in enumerate(prompts, 1):
        print(f"[{i}/{len(prompts)}] Procesando: {prompt[:50]}...")
        output = generate_response(prompt)
        if output:
            dataset.append({
                "instruction": prompt,
                "output": output
            })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Dataset generado con éxito: {output_file}")
    print(f"📊 Total de ejemplos: {len(dataset)}")

if __name__ == "__main__":
    main()
