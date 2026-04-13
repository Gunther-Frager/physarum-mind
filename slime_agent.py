import os
import json
import random
import glob
import numpy as np
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from datetime import datetime

# --- CONFIGURACIÓN ---
NOTAS_PATH = "notas"
GRAFO_FILE = "grafo.json"
MODELO_EMBEDDING = 'all-MiniLM-L6-v2' # Ligero y rápido
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
EVAPORATION_RATE = 0.95  # Las conexiones pierden 5% de fuerza cada ciclo
THRESHOLD_CONECTAR = 0.6 # Similitud mínima para reforzar rastro

genai.configure(api_key=GEMINI_API_KEY)
model_gemini = genai.GenerativeModel('gemini-1.5-flash')
embed_model = SentenceTransformer(MODELO_EMBEDDING)

# Convert float32 arrays to Python floats
if isinstance(data, np.ndarray):
    data = data.astype(float).tolist()
elif isinstance(data, np.float32):
    data = float(data)

def cargar_notas():
    archivos = glob.glob(f"{NOTAS_PATH}/*.md")
    notas = {}
    for f in archivos:
        with open(f, 'r', encoding='utf-8') as file:
            nombre = os.path.basename(f)
            notas[nombre] = file.read()
    return notas

def cargar_grafo():
    if os.path.exists(GRAFO_FILE):
        with open(GRAFO_FILE, 'r') as f:
            return json.load(f)
    return {"nodos": {}, "enlaces": {}}

def guardar_datos(grafo):
    with open(GRAFO_FILE, 'w') as f:
        json.dump(grafo, f, indent=4)

def sintetizar_idea(nota_a_nombre, nota_a_cont, nota_b_nombre, nota_b_cont):
    prompt = f"""
    Actúa como un sistema de inteligencia biológica (Slime Mold). 
    Has detectado una conexión fuerte entre estas dos ideas:
    
    IDEA A ({nota_a_nombre}): {nota_a_cont[:500]}
    IDEA B ({nota_b_nombre}): {nota_b_cont[:500]}
    
    Escribe una breve "Nota de Síntesis" (máximo 150 palabras) que fusione ambos conceptos o proponga una nueva dirección de pensamiento. 
    Devuelve solo el texto de la nota, sin introducciones.
    """
    try:
        response = model_gemini.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error en Gemini: {e}")
        return None

def ejecutar_agente():
    if not os.path.exists(NOTAS_PATH):
        os.makedirs(NOTAS_PATH)
        return

    notas = cargar_notas()
    if len(notas) < 2:
        print("Faltan notas para relacionar.")
        return

    grafo = cargar_grafo()
    nombres = list(notas.keys())
    textos = list(notas.values())

    # 1. Olfato: Calcular Embeddings y Similitud
    embeddings = embed_model.encode(textos)
    
    # 2. Metabolismo: Evaporación de rastros viejos
    for enlace in grafo["enlaces"]:
        grafo["enlaces"][enlace] *= EVAPORATION_RATE

    # 3. Exploración: Comparar pares de notas
    nuevas_conexiones = []
    for i in range(len(nombres)):
        for j in range(i + 1, len(nombres)):
            # Similitud de Coseno: $\frac{A \cdot B}{\|A\| \|B\|}$
            sim = np.dot(embeddings[i], embeddings[j]) / (np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j]))
            
            key = f"{nombres[i]}--{nombres[j]}"
            if sim > THRESHOLD_CONECTAR:
                grafo["enlaces"][key] = grafo["enlaces"].get(key, 0) + sim
                if grafo["enlaces"][key] > 1.5: # Umbral para síntesis
                    nuevas_conexiones.append((nombres[i], nombres[j]))

    # 4. Crecimiento: Crear nueva nota si la conexión es muy fuerte
    if nuevas_conexiones:
        # Elegir una conexión al azar para sintetizar
        a, b = random.choice(nuevas_conexiones)
        # Evitar crear infinitas notas sobre lo mismo
        id_sintesis = f"Sintesis_{a[:5]}_{b[:5]}.md"
        
        if id_sintesis not in notas:
            print(f"Sintetizando: {a} + {b}")
            nueva_idea = sintetizar_idea(a, notas[a], b, notas[b])
            if nueva_idea:
                ruta_nueva = os.path.join(NOTAS_PATH, id_sintesis)
                with open(ruta_nueva, 'w', encoding='utf-8') as f:
                    f.write(f"# Pensamiento Autónomo: {a} & {b}\n\n{nueva_idea}")
                print(f"Nueva nota creada: {id_sintesis}")

    # Limpiar enlaces muertos (muy débiles)
    grafo["enlaces"] = {k: v for k, v in grafo["enlaces"].items() if v > 0.1}
    
    guardar_datos(grafo)
    print("Ciclo de pensamiento completado.")

if __name__ == "__main__":
    ejecutar_agente()