def operacion_maestra_praetor():
    print("--- PRAETOR INTELLIGENCE: INICIANDO OPERACION AUTONOMA ---")
    contexto = ssl.create_default_context()
    objetivos_logrados = 0
    
    try:
        with open('prospectos.csv', mode='r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            # Limpiamos posibles espacios en los nombres de las columnas
            lector.fieldnames = [name.strip().lower() for name in lector.fieldnames] if lector.fieldnames else []
            
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=contexto) as server:
                server.login(SENDER, PASSWORD)
                
                for fila in lector:
                    # Si la fila está vacía, la saltamos
                    if not fila or not any(fila.values()):
                        continue
                        
                    email_objetivo = fila.get('email')
                    if not email_objetivo:
                        continue
                        
                    nombre = fila.get('nombre', 'Cliente')
                    asunto = f"Subject: ESTRATEGIA PRAETOR - {nombre}\n\n"
                    cuerpo = f"Operativo iniciado. Sistema listo para {nombre}."
                    
                    server.sendmail(SENDER, email_objetivo, asunto + cuerpo)
                    registrar_logistica(email_objetivo, "Propuesta_Base_15K")
                    objetivos_logrados += 1
                    print(f"[✓] IMPACTO: {email_objetivo}")
                    time.sleep(2) 

        # Reporte Final
        asunto_reporte = "Subject: PRAETOR: OPERACION COMPLETADA\n\n"
        # ... (resto del envío de reporte a Max Esquerra)