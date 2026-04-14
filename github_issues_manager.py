"""
🧠 GitHub Issues Manager for Physarum-Mind
===========================================
Gestor bidireccional de issues GitHub:
  1. IMPORT: Lee ideas de issues etiquetados con 'idea' y las crea como notas.md
  2. PUBLISH: Publica síntesis interesantes como issues etiquetadas

Uso:
  python github_issues_manager.py --import      # Importar ideas de issues
  python github_issues_manager.py --publish     # Publicar síntesis como issues
"""

import os
import sys
import json
import argparse
from datetime import datetime

try:
    import requests
    from github import Github
except ImportError:
    print("⚠️  Instalando dependencias...")
    os.system("pip install PyGithub requests")
    from github import Github
    import requests


# ==================== CONFIGURACIÓN ====================
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_NAME = "Gunther-Frager/physarum-mind"  # Cambiar si es necesario
NOTAS_PATH = "notas"
GRAFO_FILE = "grafo.json"
SYNTHESIS_LOG_FILE = ".synthesis_published"  # Para evitar duplicados

# ==================== UTILIDADES ====================

def cargar_synthesis_log():
    """Carga el registro de síntesis ya publicadas para evitar duplicados."""
    if os.path.exists(SYNTHESIS_LOG_FILE):
        with open(SYNTHESIS_LOG_FILE, 'r') as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def guardar_synthesis_log(log):
    """Guarda el registro de síntesis publicadas."""
    with open(SYNTHESIS_LOG_FILE, 'w') as f:
        json.dump(log, f, indent=2)

# ==================== IMPORTAR IDEAS DE ISSUES ====================

def importar_ideas_desde_issues():
    """
    Lee issues etiquetados con 'idea' y crea notas.md automáticamente.
    
    Flujo:
    1. Conecta a GitHub API
    2. Busca issues con label 'idea'
    3. Por cada issue no procesado:
       - Crea un archivo .md en /notas/
       - Cierra el issue con comentario
       - Marca como procesado
    """
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN no configurado. No se pueden importar ideas.")
        return

    print("\n🔍 Buscando ideas en GitHub Issues...")
    
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        
        # Buscar issues abiertos con label 'idea'
        issues = repo.get_issues(state='open', labels=['idea'])
        
        contador = 0
        for issue in issues:
            titulo = issue.title
            cuerpo = issue.body or "(Sin descripción)"
            numero = issue.number
            
            # Crear nombre de archivo seguro
            nombre_archivo = f"idea_{numero}_{titulo[:30].replace(' ', '_').replace('/', '_')}.md"
            ruta = os.path.join(NOTAS_PATH, nombre_archivo)
            
            # Evitar sobrescribir notas existentes
            if os.path.exists(ruta):
                print(f"⏭️  Idea #{numero} ya importada")
                continue
            
            # Crear la nota
            contenido = f"# {titulo}\n\n*Importada desde Issue #{numero}*\n\n{cuerpo}\n"
            with open(ruta, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            # Comentar y cerrar el issue
            issue.create_comment(
                f"✅ Idea importada como nota autónoma.\n\n"
                f"Archivo: `{nombre_archivo}`\n\n"
                f"El Slime Mold ahora procesará esta idea junto con las otras notas. "
                f"Las conexiones y síntesis resultantes aparecerán aquí."
            )
            issue.edit(state='closed')
            
            print(f"✓ Importada idea #{numero}: {titulo}")
            contador += 1
        
        if contador == 0:
            print("✓ Sin nuevas ideas que importar")
        else:
            print(f"\n✅ Se importaron {contador} idea(s) exitosamente")
            
    except Exception as e:
        print(f"❌ Error al importar ideas: {e}")


# ==================== PUBLICAR SÍNTESIS COMO ISSUES ====================

def evaluar_calidad_sintesis(contenido):
    """
    Evalúa si una síntesis es 'interesante' para publicar.
    
    Criterios:
    - Longitud mínima (contenido sustancial)
    - Sin palabras clave de error
    
    Retorna: (es_interesante: bool, confianza: float 0-1)
    """
    palabras_negativas = ["error", "unable", "unable to", "failed", "no content"]
    es_largo = len(contenido) > 100
    sin_errores = not any(neg in contenido.lower() for neg in palabras_negativas)
    
    confianza = 0.0
    if es_largo and sin_errores:
        confianza = 0.9
    elif es_largo:
        confianza = 0.5
    
    return confianza > 0.7, confianza


def publicar_sintesis_como_issues():
    """
    Busca síntesis nuevas (archivos Sintesis_*.md) y las publica como issues.
    
    Flujo:
    1. Busca archivos Sintesis_*.md en /notas/
    2. Verifica si ya fueron publicados (evita duplicados)
    3. Crea issue con:
       - Título descriptivo
       - Cuerpo con la síntesis
       - Label 'synthesis'
       - Label 'auto-generated'
    4. Marca como publicado en .synthesis_published
    """
    if not GITHUB_TOKEN:
        print("❌ GITHUB_TOKEN no configurado. No se pueden publicar síntesis.")
        return

    print("\n📤 Buscando síntesis nuevas para publicar...")
    
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        log_publicadas = cargar_synthesis_log()
        
        # Buscar archivos de síntesis
        if not os.path.exists(NOTAS_PATH):
            print("✓ Directorio de notas aún no existe")
            return
        
        sintesis_files = [f for f in os.listdir(NOTAS_PATH) if f.startswith("Sintesis_")]
        
        contador = 0
        for filename in sintesis_files:
            ruta = os.path.join(NOTAS_PATH, filename)
            
            # Evitar duplicados
            if filename in log_publicadas:
                continue
            
            # Leer contenido
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()
            
            # Evaluar si es interesante
            es_interesante, confianza = evaluar_calidad_sintesis(contenido)
            
            if not es_interesante:
                print(f"⏭️  {filename} - Confianza baja ({confianza:.1%}), no publicado")
                continue
            
            # Extraer título (primera línea con #)
            lineas = contenido.split('\n')
            titulo = next((l.replace('# ', '').strip() for l in lineas if l.startswith('#')), 
                         "Nueva Síntesis del Slime Mold")
            
            # Crear issue
            titulo_issue = f"🧠 {titulo}"
            cuerpo_issue = (
                f"*Síntesis autónoma del Slime Mold*\n\n"
                f"{contenido}\n\n"
                f"---\n"
                f"**Confianza:** {confianza:.1%}\n"
                f"**Archivo:** `{filename}`"
            )
            
            try:
                issue = repo.create_issue(
                    title=titulo_issue,
                    body=cuerpo_issue,
                    labels=['synthesis', 'auto-generated', '🧠-autonomous']
                )
                log_publicadas.append(filename)
                guardar_synthesis_log(log_publicadas)
                print(f"✓ Publicada síntesis: {titulo_issue} (Issue #{issue.number})")
                contador += 1
            except Exception as e:
                print(f"⚠️  Error al publicar {filename}: {e}")
        
        if contador == 0:
            print("✓ Sin síntesis nuevas para publicar")
        else:
            print(f"\n✅ Se publicaron {contador} síntesis como issues")
            
    except Exception as e:
        print(f"❌ Error al publicar síntesis: {e}")


# ==================== PUNTO DE ENTRADA ====================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="🧠 Gestor bidireccional GitHub ↔️ Slime Mold"
    )
    parser.add_argument(
        "--import",
        action="store_true",
        help="Importar ideas desde issues con label 'idea'"
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publicar síntesis nuevas como issues"
    )
    
    args = parser.parse_args()
    
    if args.import:
        importar_ideas_desde_issues()
    
    if args.publish:
        publicar_sintesis_como_issues()
    
    if not args.import and not args.publish:
        print("⚠️  Especifica --import o --publish")
        print(f"Uso: {sys.argv[0]} --import  # Importar ideas")
        print(f"     {sys.argv[0]} --publish # Publicar síntesis")
