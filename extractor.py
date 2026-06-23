import os

# Configuración de extracción
OUTPUT_FILE = "PRAETOR_CONTEXTO_COMPLETO.txt"
EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "venv", "env", ".mypy_cache", "VERDUGO_FILES_EXTRAIDOS"}
EXCLUDE_EXTS = {".pdf", ".jpg", ".png", ".exe", ".pyc", ".pptx", ".zip"}

def extraer_codigo():
    print("[*] Iniciando barrido del ecosistema...")
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:
        for root, dirs, files in os.walk("."):
            # Filtrar carpetas excluidas
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in EXCLUDE_EXTS or file == OUTPUT_FILE or file == "extractor.py":
                    continue
                
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as infile:
                        contenido = infile.read()
                        
                    # Separador visual de grado industrial
                    outfile.write("="*80 + "\n")
                    outfile.write(f"[+] ARCHIVO: {filepath}\n")
                    outfile.write("="*80 + "\n\n")
                    outfile.write(contenido)
                    outfile.write("\n\n")
                    print(f"  -> Integrado: {filepath}")
                except Exception as e:
                    outfile.write(f"// [!] ERROR LECTURA en {filepath}: {e}\n\n")

    print(f"\n[+] EXTRACCIÓN COMPLETADA. Archivo maestro generado: {OUTPUT_FILE}")

if __name__ == "__main__":
    extraer_codigo()