"""
🎨 Dashboard Web Generator for Physarum-Mind
=============================================
Genera un dashboard HTML interactivo que visualiza:
  - Grafo de conexiones entre notas
  - Fortaleza de cada conexión
  - Síntesis creadas
  - Historial de ciclos de pensamiento

El dashboard se regenera cada ciclo del agente y se guarda en /docs/index.html
Se visualiza en: https://username.github.io/physarum-mind (con GitHub Pages activado)
"""

import os
import json
import glob
from datetime import datetime
from pathlib import Path


# ==================== CONFIGURACIÓN ====================
GRAFO_FILE = "grafo.json"
NOTAS_PATH = "notas"
DOCS_PATH = "docs"
DASHBOARD_FILE = os.path.join(DOCS_PATH, "index.html")


# ==================== UTILIDADES ====================

def asegurar_directorio():
    """Crea el directorio /docs si no existe."""
    os.makedirs(DOCS_PATH, exist_ok=True)


def cargar_grafo():
    """Carga el grafo de conexiones."""
    if os.path.exists(GRAFO_FILE):
        with open(GRAFO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"nodos": {}, "enlaces": {}}


def contar_sintesis():
    """Cuenta las síntesis generadas."""
    if not os.path.exists(NOTAS_PATH):
        return 0
    return len([f for f in os.listdir(NOTAS_PATH) if f.startswith("Sintesis_")])


def obtener_top_conexiones(grafo, limite=10):
    """Obtiene las conexiones más fuertes."""
    enlaces_ordenados = sorted(
        grafo.get("enlaces", {}).items(),
        key=lambda x: x[1],
        reverse=True
    )
    return enlaces_ordenados[:limite]


def generar_html(grafo):
    """
    Genera el HTML del dashboard.
    
    Características:
    - Visualización de red con D3.js (CDN)
    - Estadísticas en tiempo real
    - Síntesis más recientes
    - Historial interactivo
    """
    
    top_conexiones = obtener_top_conexiones(grafo)
    sintesis_count = contar_sintesis()
    nodos_count = len(grafo.get("nodos", {}))
    enlaces_count = len(grafo.get("enlaces", {}))
    
    # Preparar datos para la visualización
    nodos_json = json.dumps([
        {"id": n, "label": n.replace('.md', '')} 
        for n in grafo.get("nodos", {}).keys()
    ])
    
    enlaces_json = json.dumps([
        {
            "source": enlace.split("--")[0],
            "target": enlace.split("--")[1],
            "weight": fuerza
        }
        for enlace, fuerza in top_conexiones
    ])
    
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 Physarum-Mind Dashboard</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #333;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.2);
        }}
        
        .stat-number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2a5298;
            margin: 10px 0;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.95em;
        }}
        
        .section {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .section h2 {{
            color: #2a5298;
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 3px solid #2a5298;
            padding-bottom: 10px;
        }}
        
        #network {{
            width: 100%;
            height: 500px;
            background: #f9f9f9;
            border-radius: 8px;
            border: 1px solid #ddd;
        }}
        
        .conexion {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            margin-bottom: 10px;
            background: #f5f5f5;
            border-left: 4px solid #2a5298;
            border-radius: 4px;
        }}
        
        .conexion-nombre {{
            flex: 1;
            font-weight: 500;
            color: #333;
        }}
        
        .conexion-fuerza {{
            background: #2a5298;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }}
        
        .timestamp {{
            text-align: center;
            color: #999;
            font-size: 0.9em;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
        
        .status {{
            display: inline-block;
            padding: 8px 12px;
            background: #4caf50;
            color: white;
            border-radius: 4px;
            font-size: 0.9em;
            margin-bottom: 20px;
        }}
        
        footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            opacity: 0.7;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧠 Physarum-Mind Dashboard</h1>
            <p>Visualización en tiempo real de la red autónoma de pensamiento</p>
            <div class="status">✓ Sistema Activo - Ciclo Cada Hora</div>
        </header>
        
        <div class="grid">
            <div class="card">
                <div class="stat-label">Nodos Activos</div>
                <div class="stat-number">{nodos_count}</div>
                <small>notas en la red</small>
            </div>
            <div class="card">
                <div class="stat-label">Conexiones</div>
                <div class="stat-number">{enlaces_count}</div>
                <small>enlaces entre ideas</small>
            </div>
            <div class="card">
                <div class="stat-label">Síntesis</div>
                <div class="stat-number">{sintesis_count}</div>
                <small>ideas generadas</small>
            </div>
            <div class="card">
                <div class="stat-label">Actualizado</div>
                <div class="stat-number">Ahora</div>
                <small>cada 1 hora</small>
            </div>
        </div>
        
        <div class="section">
            <h2>🌐 Red de Pensamiento</h2>
            <p style="font-size: 0.9em; color: #666; margin-bottom: 15px;">
                Cada nodo es una nota/idea. Las líneas representan conexiones semánticas.
                El grosor indica la fortaleza de la conexión.
            </p>
            <div id="network"></div>
        </div>
        
        <div class="section">
            <h2>🔗 Conexiones Más Fuertes</h2>
            <div id="conexiones"></div>
        </div>
        
        <div class="timestamp">
            Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
        </div>
    </div>
    
    <script>
        // Datos del grafo
        const nodos = {nodos_json};
        const enlaces = {enlaces_json};
        
        // Configuración básica
        const width = document.getElementById('network').clientWidth;
        const height = 500;
        
        // Crear simulación de fuerza
        const simulation = d3.forceSimulation(nodos)
            .force('link', d3.forceLink(enlaces)
                .id(d => d.id)
                .distance(100)
                .strength(0.5))
            .force('charge', d3.forceManyBody().strength(-300))
            .force('center', d3.forceCenter(width / 2, height / 2));
        
        // Crear SVG
        const svg = d3.select('#network').append('svg')
            .attr('width', width)
            .attr('height', height);
        
        // Dibujar enlaces
        const link = svg.selectAll('line')
            .data(enlaces)
            .enter()
            .append('line')
            .attr('stroke', '#999')
            .attr('stroke-opacity', 0.6)
            .attr('stroke-width', d => Math.sqrt(d.weight) * 2);
        
        // Dibujar nodos
        const node = svg.selectAll('circle')
            .data(nodos)
            .enter()
            .append('circle')
            .attr('r', 8)
            .attr('fill', '#2a5298')
            .attr('stroke', '#fff')
            .attr('stroke-width', 2)
            .style('cursor', 'pointer');
        
        // Añadir etiquetas
        const labels = svg.selectAll('text')
            .data(nodos)
            .enter()
            .append('text')
            .attr('font-size', '11px')
            .attr('font-weight', 'bold')
            .attr('fill', '#2a5298')
            .attr('text-anchor', 'middle')
            .attr('dy', 25)
            .text(d => d.label.substring(0, 10));
        
        // Actualizar posiciones
        simulation.on('tick', () => {{
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);
            
            node
                .attr('cx', d => d.x)
                .attr('cy', d => d.y);
            
            labels
                .attr('x', d => d.x)
                .attr('y', d => d.y);
        }});
        
        // Interactividad con drag
        node.call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));
        
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
        
        // Renderizar conexiones
        const conexionesHtml = {json.dumps(top_conexiones)}.map(([nombre, fuerza]) => `
            <div class="conexion">
                <div class="conexion-nombre">${{nombre.replace('--', ' ↔️ ').replace('.md', '')}}</div>
                <div class="conexion-fuerza">${{(fuerza * 100).toFixed(0)}}%</div>
            </div>
        `).join('');
        document.getElementById('conexiones').innerHTML = conexionesHtml;
    </script>
    
    <footer>
        <p>🧠 Physarum-Mind • Pensamiento autónomo basado en biología computacional</p>
        <p style="font-size: 0.9em; opacity: 0.7;">${{REPO_NAME}} • GitHub Actions • Actualización horaria</p>
    </footer>
</body>
</html>
"""
    return html_content


# ==================== GENERACIÓN ====================

def generar_dashboard():
    """
    Punto de entrada principal.
    
    Flujo:
    1. Carga el grafo actual
    2. Genera el HTML
    3. Lo guarda en /docs/index.html
    4. Listo para visualizar en GitHub Pages
    """
    asegurar_directorio()
    
    print("📊 Generando dashboard web...")
    
    try:
        grafo = cargar_grafo()
        html = generar_html(grafo)
        
        with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"✅ Dashboard generado en: {DASHBOARD_FILE}")
        print(f"   Nodos: {len(grafo.get('nodos', {}))}")
        print(f"   Conexiones: {len(grafo.get('enlaces', {}))}")
        print(f"   Síntesis: {contar_sintesis()}")
        
    except Exception as e:
        print(f"❌ Error al generar dashboard: {e}")


if __name__ == "__main__":
    generar_dashboard()
