"""
🧠 PHYSARUM-MIND: Agente Autónomo Biológico de Pensamiento
===========================================================

Un sistema de pensamiento basado en el comportamiento del Slime Mold (Physarum Polycephalum).
El agente procesa notas, encuentra conexiones semánticas y SINTETIZA IDEAS NUEVAS automáticamente.

CÓMO FUNCIONA:
1. OLFATO:       Calcula embeddings semánticos de cada nota (sentence-transformers)
2. EXPLORACIÓN:  Compara notas buscando similitud > threshold
3. METABOLISMO:  Debilita conexiones viejas (evaporación = olvido)
4. CRECIMIENTO:  Si 2 notas conectan fuertemente → genera síntesis con IA (Gemini)

FLUJO DE DATOS:
  notas/*.md → embeddings → similitud → grafo.json → síntesis → notas/Sintesis_*.md

CICLO POR DEFECTO: Cada 1 hora (configurable en .github/workflows/main.yml)
"""

import os
import json
import random
import glob
import numpy as np
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from datetime import datetime

# ==================== CONFIGURACIÓN ====================
# 📁 Ubicaciones
NOTAS_PATH = "notas"                           # Directorio de notas (importadas + síntesis)
GRAFO_FILE = "grafo.json"                     # Archivo persistente del grafo de conexiones

# 🧠 Modelos IA
MODELO_EMBEDDING = 'all-MiniLM-L6-v2'        # Embeddings: ligero (33MB), rápido, preciso
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") # Clave para generación de síntesis

# ⚙️ Parámetros de Comportamiento
EVAPORATION_RATE = 0.95                        # Metabolismo: conexiones pierden 5% de fuerza/ciclo
THRESHOLD_CONECTAR = 0.6                       # Olfato: similitud coseno mínima para registrar enlace
THRESHOLD_SINTESIS = 1.5                       # Crecimiento: fuerza mínima para crear síntesis

# Inicializar modelos
genai.configure(api_key=GEMINI_API_KEY)
model_gemini = genai.GenerativeModel('gemini-1.5-flash')
embed_model = SentenceTransformer(MODELO_EMBEDDING)


# ==================== UTILIDADES ====================

class NumpyEncoder(json.JSONEncoder):
    """
    Encoder personalizado para serializar numpy types a JSON.
    Necesario porque el grafo contiene floats y arrays de numpy.
    """
    def default(self, obj):
        if isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def cargar_notas():
    """
    📖 Lee todas las notas .md del directorio.
    
    Retorna:
        dict: {nombre_archivo.md: contenido}
    """
    archivos = glob.glob(f"{NOTAS_PATH}/*.md")
    notas = {}
    for f in archivos:
        with open(f, 'r', encoding='utf-8') as file:
            nombre = os.path.basename(f)
            notas[nombre] = file.read()
    return notas


def cargar_grafo():
    """
    🌐 Carga el grafo persistente.
    
    Estructura:
        {
            "nodos": {archivo.md: metadata},
            "enlaces": {archivo1--archivo2: fuerza}
        }
    
    Si no existe, devuelve grafo vacío.
    """
    if os.path.exists(GRAFO_FILE):
        with open(GRAFO_FILE, 'r') as f:
            return json.load(f)
    return {"nodos": {}, "enlaces": {}}


def guardar_grafo(grafo):
    """
    💾 Persiste el grafo en JSON.
    Usa NumpyEncoder para manejar tipos numpy.
    """
    with open(GRAFO_FILE, 'w') as f:
        json.dump(grafo, f, indent=4, cls=NumpyEncoder)


def sintetizar_idea(nota_a_nombre, nota_a_cont, nota_b_nombre, nota_b_cont):
    """
    🧠 SÍNTESIS: Genera una idea nueva fusionando dos conceptos.
    
    Args:
        nota_a_nombre: Nombre del archivo de la primera nota
        nota_a_cont:   Contenido de la primera nota
        nota_b_nombre: Nombre del archivo de la segunda nota
        nota_b_cont:   Contenido de la segunda nota
    
    Proceso:
        1. Crea prompt biológico para Gemini
        2. Solicita síntesis (máx 150 palabras)
        3. Retorna el texto de la nueva idea
    
    Retorna:
        str: Síntesis generada, o None si falla
    """
    prompt = f"""
    Actúa como un sistema de inteligencia biológica (Slime Mold). 
    Has detectado una conexión fuerte entre estas dos ideas:
    
    IDEA A ({nota_a_nombre}): {nota_a_cont[:500]}
    IDEA B ({nota_b_nombre}): {nota_b_cont[:500]}
    
    Escribe una breve "Nota de Síntesis" (máximo 150 palabras) que:
    - Fusione ambos conceptos de forma creativa
    - Proponga una nueva dirección de pensamiento
    - Sea similar en profundidad a las notas originales
    
    Devuelve solo el texto de la nota, sin introducciones.
    """
    try:
        response = model_gemini.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"⚠️  Error en Gemini al sintetizar: {e}")
        return None


# ==================== CICLO PRINCIPAL ====================

def ejecutar_agente():
    """
    🔄 CICLO DE PENSAMIENTO COMPLETO del Slime Mold.
    
    Pasos:
    1️⃣  PREPARACIÓN: Carga notas del directorio
    2️⃣  OLFATO:     Calcula embeddings semánticos
    3️⃣  METABOLISMO: Debilita conexiones viejas (evaporación)
    4️⃣  EXPLORACIÓN: Busca similitudes entre notas
    5️⃣  CRECIMIENTO: Sintetiza ideas de conexiones fuertes
    6️⃣  PERSISTENCIA: Guarda grafo y nuevas notas
    
    Se ejecuta automáticamente cada hora (configurable en .github/workflows/main.yml)
    """
    
    # 1️⃣ PREPARACIÓN
    print("\n" + "="*60)
    print("🧠 INICIANDO CICLO DE PENSAMIENTO")
    print("="*60)
    
    if not os.path.exists(NOTAS_PATH):
        os.makedirs(NOTAS_PATH)
        print(f"📁 Directorio {NOTAS_PATH} creado.")
        return
    
    notas = cargar_notas()
    print(f"📖 Notas cargadas: {len(notas)}")
    
    if len(notas) < 2:
        print("⚠️  Necesitas al menos 2 notas para generar conexiones.")
        print("   Añade notas a /notas/*.md o crea issues cuyo label sea 'idea'")
        return
    
    grafo = cargar_grafo()
    nombres = list(notas.keys())
    textos = list(notas.values())
    
    print(f"🌐 Grafo actual: {len(grafo['nodos'])} nodos, {len(grafo['enlaces'])} enlaces")
    
    # 2️⃣ OLFATO: Calcular Embeddings
    print("\n🔵 OLFATO: Calculando embeddings semánticos...")
    embeddings = embed_model.encode(textos)
    print(f"   ✓ {len(embeddings)} embeddings calculados")
    
    # 3️⃣ METABOLISMO: Evaporación
    print("\n🔴 METABOLISMO: Evaporando rastros viejos (olvido natural)...")
    conexiones_antes = len(grafo["enlaces"])
    for enlace in grafo["enlaces"]:
        grafo["enlaces"][enlace] *= EVAPORATION_RATE
    print(f"   ✓ Fortaleza reducida al {EVAPORATION_RATE*100:.0f}%")
    
    # 4️⃣ EXPLORACIÓN: Comparar pares
    print("\n🟢 EXPLORACIÓN: Buscando conexiones semánticas...")
    nuevas_conexiones = []
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            # Similitud de Coseno
            sim = np.dot(embeddings[i], embeddings[j]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
            )
            
            key = f"{nombres[i]}--{nombres[j]}"
            
            # Registrar si supera threshold
            if sim > THRESHOLD_CONECTAR:
                grafo["enlaces"][key] = grafo["enlaces"].get(key, 0) + sim
                
                # ¿Es suficientemente fuerte para sintetizar?
                if grafo["enlaces"][key] > THRESHOLD_SINTESIS:
                    nuevas_conexiones.append((nombres[i], nombres[j], grafo["enlaces"][key]))
                    print(f"   🔗 {nombres[i]} ↔️ {nombres[j]} (fuerza: {grafo['enlaces'][key]:.2f})")
    
    print(f"   ✓ {len(nuevas_conexiones)} conexión(es) suficientemente fuerte(s)")
    
    # 5️⃣ CRECIMIENTO: Sintetizar
    print("\n🟡 CRECIMIENTO: Generando síntesis de ideas...")
    if nuevas_conexiones:
        # Elegir una conexión aleatoria
        a, b, fuerza = random.choice(nuevas_conexiones)
        
        # Evitar duplicados
        id_sintesis = f"Sintesis_{a.replace('.md', '')[:15]}_{b.replace('.md', '')[:15]}.md"
        
        if id_sintesis not in notas:
            print(f"\n   🧠 Sintetizando: {a} + {b}")
            print(f"      Fuerza de conexión: {fuerza:.2f}")
            
            nueva_idea = sintetizar_idea(a, notas[a], b, notas[b])
            
            if nueva_idea:
                ruta_nueva = os.path.join(NOTAS_PATH, id_sintesis)
                with open(ruta_nueva, 'w', encoding='utf-8') as f:
                    f.write(f"# Síntesis Autónoma\n\n*Fusión de: {a} & {b}*\n\n{nueva_idea}")
                print(f"   ✅ Nota creada: {id_sintesis}")
            else:
                print(f"   ❌ Fallo en generación de síntesis")
        else:
            print(f"   ⏭️  {id_sintesis} ya existe")
    else:
        print("   ℹ️  Sin conexiones suficientemente fuertes esta vez")
    
    # 6️⃣ LIMPIEZA: Eliminar enlaces débiles
    print("\n🟣 LIMPIEZA: Podando conexiones débiles...")
    enlaces_antes = len(grafo["enlaces"])
    grafo["enlaces"] = {k: v for k, v in grafo["enlaces"].items() if v > 0.1}
    enlaces_podados = enlaces_antes - len(grafo["enlaces"])
    print(f"   ✓ {enlaces_podados} enlace(s) débil(es) eliminado(s)")
    
    # 7️⃣ PERSISTENCIA
    print("\n💾 PERSISTENCIA: Guardando estado...")
    guardar_grafo(grafo)
    print(f"   ✓ Grafo guardado con {len(grafo['enlaces'])} enlaces")
    
    print("\n" + "="*60)
    print("✅ CICLO DE PENSAMIENTO COMPLETADO")
    print(f"   Notas: {len(notas)}")
    print(f"   Conexiones: {len(grafo['enlaces'])}")
    print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")


# ==================== PUNTO DE ENTRADA ====================

if __name__ == "__main__":
    ejecutar_agente()