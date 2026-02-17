import PyInstaller.__main__
import os
import customtkinter

ctk_path = os.path.dirname(customtkinter.__file__)
print(f"Starting Compiilation - Ruta CustomTkinter: {ctk_path}")

args = [
    'main.py',                          # <--- CAMBIA ESTO SI TU ARCHIVO SE LLAMA DISTINTO
    '--name=Livery_Manager_PMDG_v1.0.7', # Nombre del ejecutable final
    '--onefile',                        # Crear un solo archivo .exe portátil
    '--windowed', 
    #'--uac-admin',                      # Ocultar la consola negra de fondo
    '--icon=ico.ico',                   # Tu icono
    '--version-file=version_info.txt',  # La información de versión que creamos arriba
    '--clean',                          # Limpiar caché previo
    '--noconfirm',                      # Sobrescribir sin preguntar
    
    f'--add-data={ctk_path};customtkinter',      # Incluir tema de CustomTkinter
    '--add-data=msfs24_data;msfs24_data',        # Incluir el LayoutGenerator
]

# 3. Ejecutar compilación
PyInstaller.__main__.run(args)

print("\n--- COMPILACIÓN FINALIZADA ---")