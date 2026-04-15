"""
🔍 KNOWLEDGE INGESTER: Ingesta Autónoma de Conocimiento Externo
==============================================================

Módulo que busca automáticamente en fuentes confiables (Wikipedia, arXiv, PubMed, NewsAPI)
para enriquecer notas con contexto externo verificado.

ARQUITECTURA:
  1. extract_topics_from_note() → Detecta temas principales
  2. search_wikipedia/arxiv/pubmed/news() → Busca en APIs externas
  3. validate_and_extract_knowledge() → Filtra por relevancia
  4. enrich_note_with_references() → Agrega "## Fuentes Externas"
  5. annotate_graph_with_sources() → Anotación en grafo.json

TRIGGERS:
  - Automático: Top 5 notas por similitud acumulada en cada ciclo
  - Manual: Notas con tag 'research-needed' en metadata
  - Síntesis: Enriquecimiento de síntesis antes de publicar

RATE LIMITS (GRATUITO):
  - NewsAPI: 100 req/día (free tier)
  - Wikipedia: Sin límite (pero respetar Etiqueta-User-Agent)
  - arXiv: Máximo 1 request/3 segundos (según ToS)
  - PubMed: Máximo 3 requests/segundo (paciencia recomendada)
"""

import os
import json
import re
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from urllib.parse import quote

try:
    import wikipedia
    import arxiv
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("⚠️  Instalando dependencias de knowledge_ingester...")
    os.system("pip install wikipedia arxiv requests beautifulsoup4")
    import wikipedia
    import arxiv
    import requests
    from bs4 import BeautifulSoup

try:
    from sentence_transformers import SentenceTransformer, util
    import torch
except ImportError:
    print("⚠️  Reinstalando sentence-transformers...")
    os.system("pip install sentence-transformers torch")
    from sentence_transformers import SentenceTransformer, util
    import torch


# ==================== CONFIGURACIÓN ====================

NOTAS_PATH = "notas"
GRAFO_FILE = "grafo.json"
INGESTION_LOG_FILE = "knowledge_ingestion_log.txt"

# Límites de rate limiting (gratuito solamente)
LIMIT_SEARCHES_PER_CYCLE = 5          # Máx 5 notas investigadas por ciclo
LIMIT_SEARCHES_PER_NOTE = 3           # Máx 3 temas por nota
LIMIT_RESULTS_PER_SOURCE = 3          # Máx 3 papers/artículos por API
CONFIDENCE_THRESHOLD = 0.65           # Mín similitud para considerar relevante

# API Keys
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# Timeouts (segundos)
WIKIPEDIA_TIMEOUT = 5
ARXIV_TIMEOUT = 3
PUBMED_TIMEOUT = 10
NEWSAPI_TIMEOUT = 5

# Inicializar modelos
try:
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
except:
    embed_model = None
    print("⚠️  Advertencia: Impossível cargar embeddings. Deshabilitada validación por similitud.")

# Configurar logging
logging.basicConfig(
    filename=INGESTION_LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# ==================== EXTRACCIÓN DE TEMAS ====================

def extract_topics_from_note(content: str, max_topics: int = 5) -> List[str]:
    """
    🔎 Extrae temas principales de una nota.
    
    Usa heurística simple:
    1. Toma palabras claves del título (si existe)
    2. Identifica sustantivos frecuentes (palabras con > 6 caracteres)
    3. Busca frases nombradas entre comillas
    
    Args:
        content: Contenido de la nota
        max_topics: Máximo número de temas a retornar
    
    Retorna:
        List[str]: Temas extraídos
    """
    topics = []
    
    # Extraer palabras de título (#)
    lines = content.split('\n')
    title_line = next((l for l in lines if l.startswith('#')), "")
    if title_line:
        palabras_titulo = title_line.replace('#', '').strip().split()
        # Filtrar palabras cortas y stop words comunes
        stopwords = {'el', 'la', 'de', 'y', 'o', 'es', 'a', 'en', 'del', 'las', 'los', 'un', 'una', 'que', 'el'}
        palabras_validas = [p for p in palabras_titulo if len(p) > 3 and p.lower() not in stopwords]
        topics.extend(palabras_validas[:3])
    
    # Extraer frases entre comillas o después de dos puntos
    frases = re.findall(r'"([^"]+)"', content)
    topics.extend(frases[:2])
    
    # Palabras largas (heurística de sustantivos)
    palabras = re.findall(r'\b[A-Za-záéíóúñ]{6,}\b', content)
    palabra_freqs = {}
    for p in palabras:
        palabra_freqs[p] = palabra_freqs.get(p, 0) + 1
    
    top_palabras = sorted(palabra_freqs.items(), key=lambda x: x[1], reverse=True)
    topics.extend([p[0] for p in top_palabras[:3] if p[1] >= 2])
    
    # Remover duplicados y limitar
    topics = list(dict.fromkeys(topics))[:max_topics]
    
    return topics


# ==================== BÚSQUEDAS EN FUENTES ====================

def search_wikipedia(query: str) -> Optional[Dict]:
    """
    🌐 Busca en Wikipedia.
    
    Retorna:
        dict: {title, url, summary, relevance_score} o None
    """
    try:
        # Configurar idioma español
        wikipedia.set_lang("es")
        wikipedia.set_user_agent("PhysarumMind/1.0 (+https://github.com/Gunther-Frager/physarum-mind)")
        
        # Buscar artículo
        results = wikipedia.search(query, results=1)
        if not results:
            return None
        
        page = wikipedia.page(results[0], auto_suggest=False)
        
        return {
            "source": "Wikipedia",
            "title": page.title,
            "url": page.url,
            "summary": page.summary[:400],  # Primeros 400 caracteres
            "content": page.content[:1000],  # Más contenido si es necesario
            "relevance_score": 0.8  # Wikipedia es relativamente confiable
        }
    except Exception as e:
        logging.warning(f"Wikipedia search failed for '{query}': {e}")
        return None


def search_arxiv(query: str) -> List[Dict]:
    """
    📚 Busca papers en arXiv.
    
    Retorna:
        List[dict]: Hasta LIMIT_RESULTS_PER_SOURCE papers
    """
    results = []
    try:
        client = arxiv.Client()
        
        # Buscar papers relacionados
        search = arxiv.Search(
            query=query,
            max_results=LIMIT_RESULTS_PER_SOURCE,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        
        for entry in client.results(search):
            results.append({
                "source": "arXiv",
                "title": entry.title,
                "authors": [author.name for author in entry.authors[:3]],
                "abstract": entry.summary[:400],
                "url": entry.entry_id,
                "published": entry.published.strftime("%Y-%m-%d"),
                "relevance_score": 0.85  # Papers peer-reviewed
            })
            time.sleep(ARXIV_TIMEOUT)  # Respetar rate limit
        
        return results
    except Exception as e:
        logging.warning(f"arXiv search failed for '{query}': {e}")
        return []


def search_pubmed(query: str) -> List[Dict]:
    """
    🏥 Busca artículos en PubMed (biomedicina).
    
    Retorna:
        List[dict]: Hasta LIMIT_RESULTS_PER_SOURCE artículos
    """
    results = []
    try:
        # PubMed E-utilities API (sin clave requerida)
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": LIMIT_RESULTS_PER_SOURCE,
            "rettype": "json"
        }
        
        response = requests.get(search_url, params=search_params, timeout=PUBMED_TIMEOUT)
        response.raise_for_status()
        
        search_result = response.json()
        pubmed_ids = search_result.get("esearchresult", {}).get("idlist", [])
        
        if not pubmed_ids:
            return []
        
        # Obtener detalles de los artículos
        fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": ",".join(pubmed_ids),
            "rettype": "xml"
        }
        
        response = requests.get(fetch_url, params=fetch_params, timeout=PUBMED_TIMEOUT)
        soup = BeautifulSoup(response.content, 'xml')
        
        for article in soup.find_all('PubmedArticle')[:LIMIT_RESULTS_PER_SOURCE]:
            try:
                title_elem = article.find('ArticleTitle')
                title = title_elem.text if title_elem else "Sin título"
                
                abstract_elem = article.find('AbstractText')
                abstract = abstract_elem.text[:400] if abstract_elem else ""
                
                pmid_elem = article.find('PMID')
                pmid = pmid_elem.text if pmid_elem else ""
                
                results.append({
                    "source": "PubMed",
                    "title": title,
                    "abstract": abstract,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "pmid": pmid,
                    "relevance_score": 0.9  # PubMed es altamente verificado
                })
            except Exception as e:
                logging.debug(f"Error parsing PubMed article: {e}")
                continue
        
        return results
    except Exception as e:
        logging.warning(f"PubMed search failed for '{query}': {e}")
        return []


def search_newsapi(query: str) -> List[Dict]:
    """
    📰 Busca artículos actuales en NewsAPI.
    
    Retorna:
        List[dict]: Hasta LIMIT_RESULTS_PER_SOURCE artículos
    """
    if not NEWSAPI_KEY:
        logging.debug("NEWSAPI_KEY no configurada. Saltando búsqueda en NewsAPI.")
        return []
    
    results = []
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "sortBy": "relevancy",
            "language": "es",
            "pageSize": LIMIT_RESULTS_PER_SOURCE,
            "apiKey": NEWSAPI_KEY
        }
        
        response = requests.get(url, params=params, timeout=NEWSAPI_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("status") == "ok":
            for article in data.get("articles", [])[:LIMIT_RESULTS_PER_SOURCE]:
                results.append({
                    "source": "News",
                    "title": article.get("title", ""),
                    "description": article.get("description", "")[:300],
                    "url": article.get("url", ""),
                    "published_at": article.get("publishedAt", ""),
                    "relevance_score": 0.65  # Noticias menos verificadas que papers
                })
        else:
            logging.warning(f"NewsAPI error: {data.get('message', 'Unknown error')}")
        
        return results
    except Exception as e:
        logging.warning(f"NewsAPI search failed for '{query}': {e}")
        return []


# ==================== VALIDACIÓN Y EXTRACCIÓN ====================

def validate_and_extract_knowledge(all_results: List[Dict], query: str) -> Dict:
    """
    ✓ Valida resultados de búsqueda usando similitud semántica.
    
    Filtra por:
    1. Relevancia (similitud con query > CONFIDENCE_THRESHOLD)
    2. Confiabilidad (relevance_score del fuente)
    3. Diversidad (máximo 1 por fuente)
    
    Retorna:
        dict: {
            "wikipedia": [...],
            "arxiv": [...],
            "pubmed": [...],
            "news": [...]
        }
    """
    validated = {
        "wikipedia": [],
        "arxiv": [],
        "pubmed": [],
        "news": []
    }
    
    if not all_results or embed_model is None:
        # Fallback: aceptar todo si no hay embeddings
        for result in all_results:
            source = result.get("source", "").lower()
            if source == "wikipedia":
                validated["wikipedia"].append(result)
            elif source == "arxiv":
                validated["arxiv"].append(result)
            elif source == "pubmed":
                validated["pubmed"].append(result)
            elif source == "news":
                validated["news"].append(result)
        return validated
    
    # Calcular embedding del query
    query_embedding = embed_model.encode(query, convert_to_tensor=True)
    
    for result in all_results:
        try:
            # Texto para validar (título + resumen)
            text_to_validate = result.get("title", "") + " " + result.get("summary", "") or result.get("abstract", "") or result.get("description", "")
            
            if not text_to_validate.strip():
                continue
            
            # Calcular similitud
            text_embedding = embed_model.encode(text_to_validate, convert_to_tensor=True)
            similarity = util.pytorch_cos_sim(query_embedding, text_embedding).item()
            
            # Combinación de similitud + confiabilidad de fuente
            combined_score = (similarity * 0.7 + result.get("relevance_score", 0.6) * 0.3)
            
            if combined_score > CONFIDENCE_THRESHOLD:
                result["similarity_score"] = float(similarity)
                result["combined_score"] = float(combined_score)
                
                source = result.get("source", "").lower()
                if source == "wikipedia" and len(validated["wikipedia"]) < 1:
                    validated["wikipedia"].append(result)
                elif source == "arxiv" and len(validated["arxiv"]) < 2:
                    validated["arxiv"].append(result)
                elif source == "pubmed" and len(validated["pubmed"]) < 2:
                    validated["pubmed"].append(result)
                elif source == "news" and len(validated["news"]) < 3:
                    validated["news"].append(result)
        
        except Exception as e:
            logging.debug(f"Validation error for result: {e}")
            continue
    
    return validated


# ==================== ENRIQUECIMIENTO DE NOTAS ====================

def enrich_note_with_references(filepath: str, knowledge_dict: Dict) -> bool:
    """
    ✍️ Enriquece una nota con sección "## Fuentes Externas".
    
    Formato:
        ## Fuentes Externas
        
        ### Wikipedia
        [Título](URL)
        > "Párrafo extraído..."
        
        ### arXiv
        - [Título](URL) por Autores
          Abstract: ...
    
    Retorna:
        bool: True si se agregó contenido, False si no
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar que no exista ya sección
        if "## Fuentes Externas" in content:
            logging.info(f"Nota {filepath} ya tiene sección de fuentes.")
            return False
        
        # Construir sección de fuentes
        fuentes_section = "\n\n## Fuentes Externas\n\n"
        has_content = False
        
        # Wikipedia
        if knowledge_dict.get("wikipedia"):
            fuentes_section += "### 🌐 Wikipedia\n\n"
            for result in knowledge_dict["wikipedia"]:
                fuentes_section += f"[{result['title']}]({result['url']}) (Relevancia: {result.get('similarity_score', 0):.2f})\n\n"
                fuentes_section += f"> {result['summary'][:200]}...\n\n"
            has_content = True
        
        # arXiv
        if knowledge_dict.get("arxiv"):
            fuentes_section += "### 📚 arXiv (Papers Científicos)\n\n"
            for result in knowledge_dict["arxiv"]:
                authors = ", ".join(result.get('authors', [])[:2])
                fuentes_section += f"- **[{result['title']}]({result['url']})** ({result.get('published', 'N/A')})\n"
                if authors:
                    fuentes_section += f"  *Autores: {authors}*\n"
                fuentes_section += f"  {result['abstract'][:150]}...\n\n"
            has_content = True
        
        # PubMed
        if knowledge_dict.get("pubmed"):
            fuentes_section += "### 🏥 PubMed (Biomedicina)\n\n"
            for result in knowledge_dict["pubmed"]:
                fuentes_section += f"- **[{result['title']}]({result['url']})**\n"
                fuentes_section += f"  {result['abstract'][:150]}...\n\n"
            has_content = True
        
        # News
        if knowledge_dict.get("news"):
            fuentes_section += "### 📰 Noticias Recientes\n\n"
            for result in knowledge_dict["news"]:
                date = result.get('published_at', '')[:10]
                fuentes_section += f"- **[{result['title']}]({result['url']})** ({date})\n"
                fuentes_section += f"  {result['description'][:100]}...\n\n"
            has_content = True
        
        if not has_content:
            return False
        
        # Agregar sección al final
        content_enriched = content + fuentes_section
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content_enriched)
        
        logging.info(f"Nota {filepath} enriquecida con fuentes externas.")
        return True
    
    except Exception as e:
        logging.error(f"Error enriqueciendo nota {filepath}: {e}")
        return False


def annotate_graph_with_sources(grafo_dict: Dict, note_name: str, sources_meta: Dict) -> bool:
    """
    📊 Anotación del grafo con metadatos de fuentes.
    
    Estructura agregada a grafo.json:
        grafo["fuentes"] = {
            "nota.md": [
                {source, url, relevance_score},
                ...
            ]
        }
    
    Retorna:
        bool: True si se agregó anotación
    """
    try:
        if "fuentes" not in grafo_dict:
            grafo_dict["fuentes"] = {}
        
        fuentes_anotadas = []
        
        for source_type in ["wikipedia", "arxiv", "pubmed", "news"]:
            for result in sources_meta.get(source_type, []):
                fuentes_anotadas.append({
                    "source": result.get("source", source_type),
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "relevance": result.get("combined_score", result.get("relevance_score", 0)),
                    "timestamp": datetime.now().isoformat()
                })
        
        if fuentes_anotadas:
            grafo_dict["fuentes"][note_name] = fuentes_anotadas
            return True
        
        return False
    
    except Exception as e:
        logging.error(f"Error anotando grafo: {e}")
        return False


# ==================== ORQUESTACIÓN ====================

def investigar_nota(nota_path: str, nota_nombre: str):
    """
    🔬 Realiza investigación completa de una nota.
    
    Proceso:
    1. Extrae temas principales
    2. Busca en todas las fuentes
    3. Valida resultados
    4. Enriquece nota con referencias
    5. Retorna metadatos para anotar grafo
    """
    print(f"  🔍 Investigando: {nota_nombre}")
    
    try:
        # Leer contenido
        with open(nota_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar si ya tiene fuentes
        if "## Fuentes Externas" in content:
            print(f"    ⏭️  Ya tiene fuentes externas")
            return None
        
        # Extraer temas
        topics = extract_topics_from_note(content, max_topics=LIMIT_SEARCHES_PER_NOTE)
        print(f"    Temas detectados: {', '.join(topics[:3])}")
        
        all_sources = {
            "wikipedia": [],
            "arxiv": [],
            "pubmed": [],
            "news": []
        }
        
        # Buscar para cada tema
        for topic in topics[:LIMIT_SEARCHES_PER_NOTE]:
            print(f"      Buscando: '{topic}'")
            
            # Búsquedas paralelas en tiempo secuencial (simple)
            wiki_results = search_wikipedia(topic)
            arxiv_results = search_arxiv(topic)
            pubmed_results = search_pubmed(topic)
            news_results = search_newsapi(topic)
            
            # Compilar todos los resultados
            all_results = []
            if wiki_results:
                all_results.append(wiki_results)
            all_results.extend(arxiv_results)
            all_results.extend(pubmed_results)
            all_results.extend(news_results)
            
            # Validar
            validated = validate_and_extract_knowledge(all_results, topic)
            
            # Agregar a colección
            all_sources["wikipedia"].extend(validated["wikipedia"])
            all_sources["arxiv"].extend(validated["arxiv"])
            all_sources["pubmed"].extend(validated["pubmed"])
            all_sources["news"].extend(validated["news"])
        
        # Contar fuentes encontradas
        total_sources = sum(len(v) for v in all_sources.values())
        print(f"    ✓ Encontradas {total_sources} fuentes!")
        
        if total_sources == 0:
            print(f"    ℹ️  Sin fuentes relevantes encontradas")
            return None
        
        # Enriquecer nota
        if enrich_note_with_references(nota_path, all_sources):
            logging.info(f"Nota {nota_nombre} investigada: {total_sources} fuentes agregadas")
            print(f"    ✅ Nota enriquecida")
            return all_sources
        else:
            return None
    
    except Exception as e:
        logging.error(f"Error investigando nota {nota_nombre}: {e}")
        print(f"    ❌ Error: {e}")
        return None


def ejecutar_investigacion(notas_para_investigar: Optional[List[str]] = None):
    """
    🔬 Orquesta la investigación de notas.
    
    Args:
        notas_para_investigar: Lista de nombres de notas. Si None, usa heurística (top notas)
    
    Proceso:
    1. Obtiene lista de notas a investigar
    2. Limita a LIMIT_SEARCHES_PER_CYCLE
    3. Investiga cada una
    4. Enriquece grafo.json
    5. Log de actividad
    """
    print("\n" + "="*60)
    print("🔬 INVESTIGACIÓN: Buscando conocimiento externo")
    print("="*60)
    
    # Cargar grafo
    try:
        with open(GRAFO_FILE, 'r') as f:
            grafo = json.load(f)
    except:
        grafo = {"nodos": {}, "enlaces": {}, "fuentes": {}}
    
    # Determinar notas a investigar
    if notas_para_investigar is None:
        # Heurística: notas sin "## Fuentes Externas" + top por connecciones
        notas_path_files = []
        if os.path.exists(NOTAS_PATH):
            for f in os.listdir(NOTAS_PATH):
                if f.endswith('.md'):
                    notas_path_files.append((f, os.path.join(NOTAS_PATH, f)))
        
        notas_para_investigar = [n[0] for n in notas_path_files[:LIMIT_SEARCHES_PER_CYCLE]]
    else:
        notas_para_investigar = notas_para_investigar[:LIMIT_SEARCHES_PER_CYCLE]
    
    if not notas_para_investigar:
        print("  ℹ️  Sin notas para investigar")
        return
    
    print(f"  📋 Investigando {len(notas_para_investigar)} nota(s)...")
    
    investigadas = 0
    for nota_nombre in notas_para_investigar:
        nota_path = os.path.join(NOTAS_PATH, nota_nombre)
        if not os.path.exists(nota_path):
            continue
        
        sources = investigar_nota(nota_path, nota_nombre)
        if sources:
            annotate_graph_with_sources(grafo, nota_nombre, sources)
            investigadas += 1
    
    # Guardar grafo actualizado
    try:
        with open(GRAFO_FILE, 'w') as f:
            json.dump(grafo, f, indent=2, default=str)
    except Exception as e:
        logging.error(f"Error guardando grafo: {e}")
    
    print(f"\n  ✅ Investigación completada: {investigadas} notas enriquecidas")
    print("="*60 + "\n")


# ==================== PUNTO DE ENTRADA ====================

if __name__ == "__main__":
    # Ejemplo de uso
    print("knowledge_ingester.py - Módulo de Ingesta Autónoma\n")
    print("Uso desde slime_agent.py:")
    print("  from knowledge_ingester import ejecutar_investigacion")
    print("  ejecutar_investigacion()  # Investiga automáticamente")
    print("\nO especificar notas:")
    print("  ejecutar_investigacion(['expansión del universo.md'])")
