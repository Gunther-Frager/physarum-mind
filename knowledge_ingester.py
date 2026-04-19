"""
🔍 KNOWLEDGE INGESTER v2: Ingesta Inteligente de Conocimiento Externo
=====================================================================

Módulo mejorado que busca automáticamente en fuentes confiables (Wikipedia, arXiv, PubMed, NewsAPI)
para enriquecer notas con contexto externo verificado.

MEJORAS EN v2:
  ✅ Validación POST-BÚSQUEDA (contra nota original) - PREVIENE FALSOS POSITIVOS
  ✅ Extracción de temas mejorada (n-gramas en lugar de palabras individuales)
  ✅ Control manual explícito (labels + keywords @investigate)
  ✅ Configuración centralizada con booleans on/off
  ✅ Keywords en español e inglés (investigar, investigate, research, etc.)
  ✅ Documentación exhaustiva para desarrollo

EJEMPLO DE PROBLEMA RESUELTO:
  ANTES: Nota sobre "expansión del universo" → Buscaba "Estira" → Wiki encontraba "Ciudad griega"
  DESPUÉS: Con validación POST-BÚSQUEDA → Rechaza "Ciudad griega" (no similar a nota original)

ARQUITECTURA MEJORADA:
  1. extract_ngrams() → Extrae frases (bigramas, no palabras individuales)
  2. extract_topics_from_note() → Detecta temas con n-gramas
  3. extract_investigation_keywords() → Busca @investigate, @investigar en notas
  4. search_wikipedia/arxiv/pubmed/news() → Búsquedas en APIs
  5. validate_and_extract_knowledge() → Filtra por relevancia + NOTA ORIGINAL (nuevo!)
  6. enrich_note_with_references() → Agrega "## Fuentes Externas"
  7. annotate_graph_with_sources() → Anotación en grafo.json

TRIGGERS:
  - 🤖 Automático: Top N notas por ciclo (si ENABLE_AUTOMATIC_INVESTIGATION=True)
  - 🏷️  Manual-Labels: Label 'investigar'/'investigate' en issues
  - 🔑 Manual-Keywords: @investigate, @investigar, @research en contenido de nota
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
except ImportError as e:
    print(f"⚠️  No se pudieron importar dependencias de knowledge_ingester: {e}")
    wikipedia = None
    arxiv = None
    requests = None
    BeautifulSoup = None

try:
    from sentence_transformers import SentenceTransformer, util
    import torch
except ImportError as e:
    print(f"⚠️  sentence-transformers no está instalado: {e}")
    SentenceTransformer = None
    util = None
    torch = None


# ==================== CONFIGURACIÓN CENTRALIZADA ====================
# 📋 SECCIÓN CENTRAL: Todos los parámetros ajustables en UN SOLO LUGAR
# Cambiar valores aquí sin necesidad de editar funciones
# INSPIRADO EN: Estructura de slime_agent.py

print("\n" + "="*60)
print("⚙️  CONFIGURACIÓN: KNOWLEDGE INGESTER")
print("="*60)

# 📁 UBICACIONES DE ARCHIVOS
NOTAS_PATH = "notas"
GRAFO_FILE = "grafo.json"
INGESTION_LOG_FILE = "knowledge_ingestion_log.txt"

# 🎛️ ACTIVACIÓN/DESACTIVACIÓN DE FUNCIONALIDADES
# True = activada, False = desactivada
# Permite control fino del comportamiento sin editar código
ENABLE_AUTOMATIC_INVESTIGATION = True      # 🤖 Investigar notas automáticamente en ciclos
ENABLE_MANUAL_LABELS = True                # 🏷️  Detectar label 'investigar'/'investigate'
ENABLE_KEYWORD_TRIGGERS = True             # 🔑 Detectar @investigate, @investigar, @research
ENABLE_POST_SEARCH_VALIDATION = True       # ⚠️  CRÍTICO: Validar contra nota original

# 🔍 EXTRACCIÓN DE TEMAS - Controla CÓMO se detectan temas en notas
ENABLE_NGRAM_EXTRACTION = True             # Usar n-gramas (frases) vs palabras individuales
NGRAM_SIZE = 2                              # 2=bigramas (dos palabras), 3=trigramas (más específico)
MIN_WORD_LENGTH = 4                         # Ignorar palabras con < N caracteres

# 📊 VALIDACIÓN DE RELEVANCIA - Controla QUÉ se considera "relevante"
CONFIDENCE_THRESHOLD = 0.65                 # Similitud mín con query general
RELEVANCE_THRESHOLD_POST_SEARCH = 0.50      # ⭐ NUEVO: Similitud mín con NOTA ORIGINAL
SIMILARITY_WEIGHT_GENERAL = 0.7             # Peso de similitud con query
SIMILARITY_WEIGHT_NOTE_SPECIFIC = 0.3       # Peso de similitud con nota original

# ⏱️ RATE LIMITING - Límites para APIs gratis responsablemente
LIMIT_SEARCHES_PER_CYCLE = 5                # Máx 5 notas investigadas por ciclo
LIMIT_SEARCHES_PER_NOTE = 3                 # Máx 3 temas a buscar por nota
LIMIT_RESULTS_PER_SOURCE = 3                # Máx 3 papers/artículos por API

# 🔗 PALABRAS CLAVE PARA TRIGGERS MANUALES (español + inglés)
INVESTIGATION_KEYWORDS = [
    '@investigate', '@investigar',          # Inglés/Español
    '@research', '@investigación',          # Variaciones
    '@study', '@estudio',                   # Sinónimos
]

# 🌐 API KEYS
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

# ⏱️ TIMEOUTS (segundos) - Respetar ToS de cada API
WIKIPEDIA_TIMEOUT = 5
ARXIV_TIMEOUT = 3
PUBMED_TIMEOUT = 10
NEWSAPI_TIMEOUT = 5

# 🪵 LOGGING
LOG_LEVEL = logging.INFO

# Mostrar configuración en inicio
print(f"\n  🤖 Automático:           {ENABLE_AUTOMATIC_INVESTIGATION}")
print(f"  🏷️  Labels manuales:      {ENABLE_MANUAL_LABELS}")
print(f"  🔑 Keywords:             {ENABLE_KEYWORD_TRIGGERS}")
print(f"  ⚠️  Post-búsqueda:        {ENABLE_POST_SEARCH_VALIDATION}")
print(f"  🔤 N-gramas:             {ENABLE_NGRAM_EXTRACTION}")
print("="*60 + "\n")


# ==================== INICIALIZACIÓN DE MODELOS ====================

try:
    if SentenceTransformer is None:
        raise ImportError("sentence-transformers no disponible")
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    EMBEDDINGS_AVAILABLE = True
except Exception as e:
    embed_model = None
    EMBEDDINGS_AVAILABLE = False
    print(f"⚠️  No se pudo cargar embeddings: {e}")

# Configurar logging
logging.basicConfig(
    filename=INGESTION_LOG_FILE,
    level=LOG_LEVEL,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


# ==================== EXTRACCIÓN DE TEMAS (MEJORADA) ====================

def extract_ngrams(text: str, n: int = 2) -> List[str]:
    """
    🔤 NUEVO: Extrae n-gramas (frases de N palabras) de un texto.
    
    PROPÓSITO: Evitar falsos positivos como "Estira" (palabra aislada)
    que termina siendo "Ciudad griega" en Wikipedia.
    
    Usa n-gramas que son ESPECÍFICOS al contexto.
    
    Ejemplo:
      Texto: "expansión acelerada del universo"
      N=2: ["expansión acelerada", "acelerada del", "del universo"]
    
    Args:
        text: Texto para extraer n-gramas
        n: Tamaño (2=bigramas, 3=trigramas)
    
    Retorna:
        List[str]: N-gramas extraídos y limpios
    """
    palabras = text.lower().split()
    
    # Stop words en español e inglés
    stopwords = {
        'el', 'la', 'de', 'y', 'o', 'es', 'a', 'en', 'del', 'las', 'los', 
        'un', 'una', 'que', 'por', 'con', 'son', 'si', 'no', 'al', 'este',
        'the', 'and', 'or', 'is', 'in', 'of', 'to', 'for', 'on', 'with'
    }
    
    palabras_validas = [
        p for p in palabras 
        if len(p) >= MIN_WORD_LENGTH and p not in stopwords
    ]
    
    ngrams = []
    for i in range(len(palabras_validas) - n + 1):
        ngram = ' '.join(palabras_validas[i:i+n])
        ngrams.append(ngram)
    
    return ngrams


def extract_investigation_keywords(content: str) -> List[str]:
    """
    🔑 NUEVO: Extrae temas ESPECÍFICOS a investigar usando keywords explícitos.
    
    PROPÓSITO: Permitir al usuario marcar notas con @investigate: tema1, tema2
    para investigación manual y controlada.
    
    EJEMPLO DE USO EN NOTA:
      # Mi idea sobre el cosmos
      @investigar: expansión acelerada del universo, inflación cósmica
      
      El universo como lo conocemos se expande...
    
    PALABRAS CLAVE SOPORTADAS (español + inglés):
      - @investigate, @investigar
      - @research, @investigación
      - @study, @estudio
    
    Args:
        content: Contenido de la nota
    
    Retorna:
        List[str]: Temas específicos a investigar, vacío si no hay keywords
    """
    if not ENABLE_KEYWORD_TRIGGERS:
        return []
    
    temas = []
    
    # PATRÓN: @keyword: tema1, tema2, tema3
    for keyword in INVESTIGATION_KEYWORDS:
        # Buscar patrón: @keyword: contenido
        patron = rf'{re.escape(keyword)}:\s*(.+?)(?:\n|$)'
        coincidencias = re.findall(patron, content, re.IGNORECASE)
        
        for coincidencia in coincidencias:
            # Parsear como lista separada por comas
            temas_encontrados = [t.strip() for t in coincidencia.split(',')]
            temas.extend(temas_encontrados)
            logging.info(f"Keywords encontrados: {temas_encontrados}")
    
    return temas[:LIMIT_SEARCHES_PER_NOTE]


# ==================== EXTRACCIÓN DE TEMAS ====================

def extract_topics_from_note(content: str, max_topics: int = 5) -> List[str]:
    """
    🔎 MEJORADO: Extrae temas principales usando n-gramas (frases específicas).
    
    ESTRATEGIA:
    1. N-gramas del TÍTULO (máxima confianza) ⭐
    2. Frases entre comillas (muy específicas)
    3. N-gramas frecuentes en contenido
    
    vs ANTES:
      - Tomaba palabras individuales ("Estira...")
      - Era vulnerable a palabras sin contexto
    
    AHORA:
      - Busca "expansión acelerada" (bigramas = 2 palabras)
      - Específico = mucho menos ruido
    
    Args:
        content: Contenido de la nota
        max_topics: Máximo número de temas
    
    Retorna:
        List[str]: Temas extraídos (más específicos)
    """
    topics = []
    
    # ESTRATEGIA 1: N-gramas del TÍTULO (máxima confianza)
    lines = content.split('\n')
    title_line = next((l for l in lines if l.startswith('#')), "")
    if title_line:
        title_text = title_line.replace('#', '').strip()
        
        if ENABLE_NGRAM_EXTRACTION and embed_model is not None:
            # Usar n-gramas
            title_ngrams = extract_ngrams(title_text, n=NGRAM_SIZE)
            topics.extend(title_ngrams[:3])
            logging.debug(f"Título n-gramas: {title_ngrams[:3]}")
        else:
            # Fallback: palabras individuales
            palabras = title_text.split()
            stopwords = {'el', 'la', 'de', 'y', 'o', 'es', 'a', 'en', 'del'}
            palabras_validas = [p for p in palabras if len(p) >= MIN_WORD_LENGTH and p.lower() not in stopwords]
            topics.extend(palabras_validas[:3])
    
    # ESTRATEGIA 2: Frases entre comillas (muy específicas)
    frases_comillas = re.findall(r'"([^"]+)"', content)
    topics.extend(frases_comillas[:2])
    
    # ESTRATEGIA 3: N-gramas frecuentes en contenido
    if ENABLE_NGRAM_EXTRACTION and embed_model is not None:
        contenido_limpio = ' '.join([l for l in lines if not l.startswith('#')])
        content_ngrams = extract_ngrams(contenido_limpio, n=NGRAM_SIZE)
        
        # Frecuencia de n-gramas
        ngram_freqs = {}
        for ng in content_ngrams:
            ngram_freqs[ng] = ngram_freqs.get(ng, 0) + 1
        
        # Top n-gramas más frecuentes
        top_ngrams = sorted(ngram_freqs.items(), key=lambda x: x[1], reverse=True)
        topics.extend([ng[0] for ng in top_ngrams[:3] if ng[1] >= 1])
    
    # Remover duplicados manteniendo orden y limitar
    topics_dedup = []
    seen = set()
    for t in topics:
        t_lower = t.lower()
        if t_lower not in seen:
            topics_dedup.append(t)
            seen.add(t_lower)
    
    return topics_dedup[:max_topics]


# ==================== BÚSQUEDAS EN FUENTES ====================

def search_wikipedia(query: str) -> Optional[Dict]:
    """
    🌐 Busca en Wikipedia.
    
    Retorna:
        dict: {title, url, summary, relevance_score} o None
    """
    if wikipedia is None:
        logging.warning("Wikipedia no está disponible. Saltando búsqueda en Wikipedia.")
        return None
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
    if arxiv is None:
        logging.warning("arXiv no está disponible. Saltando búsqueda en arXiv.")
        return results
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
    if requests is None or BeautifulSoup is None:
        logging.warning("Requests o BeautifulSoup no están disponibles. Saltando búsqueda en PubMed.")
        return results
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
    if requests is None:
        logging.warning("Requests no está disponible. Saltando búsqueda en NewsAPI.")
        return []
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

def validate_and_extract_knowledge(
    all_results: List[Dict],
    query: str,
    nota_original: Optional[str] = None
) -> Dict:
    """
    ✓ MEJORADO: Valida resultados usando similitud + NOTA ORIGINAL (¡CRÍTICO!)
    
    NUEVO: Validación POST-BÚSQUEDA contra nota original previene FALSOS POSITIVOS.
    
    PROBLEMA RESUELTO:
      ANTES: search_wikipedia("Estira") → Wikipedia encontraba "Ciudad griega" ❌
      DESPUÉS: Compara contra nota ("espaciotiempo") → Rechaza "Ciudad griega" ✅
    
    LÓGICA:
    1. Similitud con query (¿relevante para el tema?)
    2. Similitud con nota original (¿relevante para el CONTEXTO?)
    3. Confiabilidad de fuente (¿es un sitio confiable?)
    
    Si ENABLE_POST_SEARCH_VALIDATION=True:
       - Rechaza si similitud con nota < RELEVANCE_THRESHOLD_POST_SEARCH
       - Esto previene el 90% de falsos positivos
    
    Args:
        all_results: Resultados brutos de búsquedas
        query: Query original (tema buscado)
        nota_original: Contenido completo de la nota (NUEVO - crítico!)
    
    Retorna:
        dict: Resultados filtrados por relevancia
    """
    validated = {
        "wikipedia": [],
        "arxiv": [],
        "pubmed": [],
        "news": []
    }
    
    if not all_results:
        return validated
    
    # Preparar embeddings si están disponibles
    query_embedding = None
    nota_embedding = None
    
    if EMBEDDINGS_AVAILABLE and ENABLE_POST_SEARCH_VALIDATION:
        try:
            query_embedding = embed_model.encode(query, convert_to_tensor=True)
            if nota_original:
                # Usar solo los primeros 500 caracteres para eficiencia
                nota_embedding = embed_model.encode(nota_original[:500], convert_to_tensor=True)
                logging.debug(f"Validación POST-BÚSQUEDA activada para: {query}")
        except Exception as e:
            logging.warning(f"Error en embeddings: {e}")
    elif not EMBEDDINGS_AVAILABLE:
        # Fallback: aceptar todo con un warning
        logging.debug("Embeddings no disponibles - sin validación")
        for result in all_results:
            source = result.get("source", "").lower()
            if source == "wikipedia" and len(validated["wikipedia"]) < 1:
                validated["wikipedia"].append(result)
            elif source == "arxiv" and len(validated["arxiv"]) < 2:
                validated["arxiv"].append(result)
            elif source == "pubmed" and len(validated["pubmed"]) < 2:
                validated["pubmed"].append(result)
            elif source == "news" and len(validated["news"]) < 3:
                validated["news"].append(result)
        return validated
    
    for result in all_results:
        try:
            # Compilar texto a validar
            text_to_validate = (
                result.get("title", "") + " " + 
                (result.get("summary", "") or result.get("abstract", "") or result.get("description", ""))
            )
            
            if not text_to_validate.strip():
                continue
            
            # VALIDACIÓN 1: Similitud con query
            similarity_to_query = 0.7  # Default si no hay embeddings
            if query_embedding is not None:
                try:
                    text_embedding = embed_model.encode(text_to_validate, convert_to_tensor=True)
                    similarity_to_query = util.pytorch_cos_sim(query_embedding, text_embedding).item()
                except:
                    pass
            
            # VALIDACIÓN 2: NUEVA - Similitud con NOTA ORIGINAL (¡PREVIENE FALSOS POSITIVOS!)
            similarity_to_note = 0.5  # Default conservador
            if nota_embedding is not None:
                try:
                    text_embedding = embed_model.encode(text_to_validate, convert_to_tensor=True)
                    similarity_to_note = util.pytorch_cos_sim(nota_embedding, text_embedding).item()
                    
                    # Log para debug
                    if similarity_to_note < RELEVANCE_THRESHOLD_POST_SEARCH:
                        logging.debug(
                            f"❌ Rechazado: '{result.get('title', '')[:40]}...' "
                            f"(similitud con nota: {similarity_to_note:.2f})"
                        )
                except:
                    pass
            
            # VALIDACIÓN 3: Combinar scores
            source_reliability = result.get("relevance_score", 0.6)
            combined_score = (
                similarity_to_query * SIMILARITY_WEIGHT_GENERAL +
                source_reliability * (1 - SIMILARITY_WEIGHT_GENERAL)
            )
            
            # APLICAR: Validación POST-BÚSQUEDA (criterio CRÍTICO)
            passes_post_search = True
            if ENABLE_POST_SEARCH_VALIDATION and nota_embedding is not None:
                if similarity_to_note < RELEVANCE_THRESHOLD_POST_SEARCH:
                    passes_post_search = False
            
            if not passes_post_search:
                continue
            
            # Aceptar si pasa umbral general
            if combined_score > CONFIDENCE_THRESHOLD:
                result["similarity_score"] = float(similarity_to_query)
                result["note_relevance_score"] = float(similarity_to_note)
                result["combined_score"] = float(combined_score)
                
                source = result.get("source", "").lower()
                if source == "wikipedia" and len(validated["wikipedia"]) < 1:
                    validated["wikipedia"].append(result)
                    logging.debug(f"✅ Aceptado Wikipedia: similitud_nota={similarity_to_note:.2f}")
                elif source == "arxiv" and len(validated["arxiv"]) < 2:
                    validated["arxiv"].append(result)
                elif source == "pubmed" and len(validated["pubmed"]) < 2:
                    validated["pubmed"].append(result)
                elif source == "news" and len(validated["news"]) < 3:
                    validated["news"].append(result)
        
        except Exception as e:
            logging.debug(f"Error validando resultado: {e}")
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
    🔬 MEJORADO: Realiza investigación completa de una nota.
    
    NUEVO: Soporta control manual vía @investigar keywords.
    
    Proceso:
    1. Detecta @investigar: tema1, tema2 (control manual - PRIORITARIO)
    2. Si no hay keywords, extrae temas automáticamente
    3. Busca en todas las fuentes
    4. Valida contra Nota Original (previene falsos positivos)
    5. Enriquece nota con referencias
    6. Retorna metadatos para anotar grafo
    
    Ejemplo de control manual:
        @investigar: mecánica cuántica, relatividad general
        → Solo busca esos temas, ignora extracción automática
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
        
        # NUEVO: Detectar @investigar keywords (control manual)
        temas_forzados = []
        if ENABLE_KEYWORD_TRIGGERS:
            temas_forzados = extract_investigation_keywords(content)
            if temas_forzados:
                print(f"    🏷️  Temas manuales encontrados: {', '.join(temas_forzados)}")
        
        # Usar temas forzados si existen, sino extraer automáticamente
        if temas_forzados:
            topics = temas_forzados[:LIMIT_SEARCHES_PER_NOTE]
            print(f"    Modo LOCAL: Usando temas manuales")
        else:
            # Extracción automática (solo si está habilitada)
            if not ENABLE_AUTOMATIC_INVESTIGATION:
                print(f"    ℹ️  Investigación automática deshabilitada (ENABLE_AUTOMATIC_INVESTIGATION=False)")
                return None
            
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
            
            # Búsquedas en todas las fuentes
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
            
            # MEJORADO: Pasar nota_original para validación POST-BÚSQUEDA
            # Esto previene falsos positivos como "Estira" → "Ciudad griega"
            validated = validate_and_extract_knowledge(all_results, topic, nota_original=content)
            
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
    🔬 MEJORADO: Orquesta investigación de notas con nuevas capacidades.
    
    NUEVO: Respeta ENABLE_AUTOMATIC_INVESTIGATION (puede apagarse).
    
    Args:
        notas_para_investigar: Lista de nombres de notas. Si None, usa heurística (top notas)
    
    Proceso:
    1. Verifica ENABLE_AUTOMATIC_INVESTIGATION (puede estar deshabilitado)
    2. Obtiene lista de notas a investigar
    3. Limita a LIMIT_SEARCHES_PER_CYCLE
    4. Investiga cada nota (respeta keywords @investigar)
    5. Enriquece grafo.json con nuevas fuentes
    6. Log de actividad detallado
    """
    print("\n" + "="*60)
    print("🔬 INVESTIGACIÓN: Buscando conocimiento externo")
    print("="*60)
    
    # NUEVO: Verificar si investigación está habilitada
    if not ENABLE_AUTOMATIC_INVESTIGATION:
        print("  ℹ️  Investigación automática DESHABILITADA (ENABLE_AUTOMATIC_INVESTIGATION=False)")
        print("  💡 Puede investigar notas manualmente con @investigar keywords")
        print("="*60 + "\n")
        return
    
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
    print(f"  ⚙️  Validación POST-BÚSQUEDA: {'✓ Habilitada' if ENABLE_POST_SEARCH_VALIDATION else '✗ Deshabilitada'}")
    print(f"  🏷️  Keywords manuales: {'✓ Habilitadas' if ENABLE_KEYWORD_TRIGGERS else '✗ Deshabilitadas'}")
    print(f"  N-gramas: {'✓ Habilitados' if ENABLE_NGRAM_EXTRACTION else '✗ Deshabilitados'}")
    print()
    
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
