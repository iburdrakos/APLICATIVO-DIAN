import PyInstaller.__main__
import sys
import os
from cx_Freeze import setup, Executable
import argparse

def build_exe():
    """Construye solo el ejecutable usando PyInstaller"""
    print("Construyendo ejecutable con PyInstaller...")
    PyInstaller.__main__.run([
        'main.py',
        '--name=DIAN_Processor',
        '--onefile',
        '--windowed',
        '--add-data=assets/*;assets',
        '--icon=assets/icon.ico',
        '--clean'
    ])
    print("Ejecutable creado en ./dist/DIAN_Processor.exe")

def build_installer():
    """Construye el instalador usando cx_Freeze"""
    print("Construyendo instalador con cx_Freeze...")
    
    base = None
    if sys.platform == "win32":
        base = "Win32GUI"

    include_files = [
        ("assets/", "assets/"),
        "config/",
        "LICENSE",
        "README.md"
    ]

    build_options = {
        "packages": [
            "PyQt5", 
            "pdfplumber", 
            "PyPDF2", 
            "pandas", 
            "selenium", 
            "seleniumbase",
            "requests"
        ],
        "excludes": [],
        "include_files": include_files
    }

    executables = [
        Executable(
            "main.py",
            base=base,
            target_name="DIAN_Processor.exe",
            icon="assets/icon.ico",
            copyright="Copyright © 2024",
            shortcut_name="DIAN Processor",
            shortcut_dir="DesktopFolder"
        )
    ]

    setup(
        name="DIAN Processor",
        version="1.0.0",
        description="Procesador de documentos DIAN",
        options={"build_exe": build_options},
        executables=executables,
        author="Tu Nombre",
        author_email="tu@email.com"
    )
    print("Instalador creado en ./dist")

def main():
    parser = argparse.ArgumentParser(description='Script de construcción para DIAN Processor')
    parser.add_argument('--type', choices=['exe', 'installer', 'both'], 
                      default='both', help='Tipo de construcción (exe/installer/both)')
    
    args = parser.parse_args()
    
    if args.type in ['exe', 'both']:
        build_exe()
    
    if args.type in ['installer', 'both']:
        build_installer()

if __name__ == '__main__':
    main()