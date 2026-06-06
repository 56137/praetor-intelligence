import smtplib
import ssl

def cierre_operacion_praetor():
    email = "tjlovetjgang@gmail.com"
    # CLAVE EXACTA CON ESPACIOS
    clave = "tacj cwts bmma ckbz" 

    print("--- PRAETOR: INICIANDO DISPARO DE VALIDACIÓN FINAL ---")
    
    try:
        contexto = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=contexto) as server:
            server.login(email, clave)
            
            asunto = "Subject: PRAETOR: OPERATIVO AL 100%\n\n"
            cuerpo = "Felicidades. El sistema esta listo."
            
            server.sendmail(email, email, asunto + cuerpo)
            
        print("\n[✓] ¡IMPACTO CONFIRMADO! Revisa tu bandeja de entrada.")
    except Exception as e:
        print(f"\n[!] ERROR: {e}")

if __name__ == "__main__":
    cierre_operacion_praetor()