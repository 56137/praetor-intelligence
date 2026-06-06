import json

def procesador_industrial():
    print("--- INICIANDO ESCÁNER PRAETOR ---")
    
    # Datos de inteligencia (tus objetivos actuales)
    resultados = [
        {"nombre": "Empresa_Alpha", "prioridad": "ALTA (CONTRATO CRÍTICO)"},
        {"nombre": "Inmuebles_Beta", "prioridad": "ESTÁNDAR"},
        {"nombre": "Crypto_Vault_X", "prioridad": "ALTA (CONTRATO CRÍTICO)"}
    ]

    for fila in resultados:
        print(f"[+] Analizado: {fila['nombre']} | Prioridad: {fila['prioridad']}")

    # FORZAMOS EL NOMBRE CORRECTO AQUÍ
    archivo_salida = 'campaña_final_praetor.json'
    
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=4, ensure_ascii=False)

    print(f"\n[✓] PROCESO COMPLETADO. Datos guardados en: {archivo_salida}")

if __name__ == "__main__":
    procesador_industrial()