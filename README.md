# 🧠 Physarum-Mind: Agente Autónomo de Pensamiento

<div align="center">

**Un sistema de inteligencia biológica que piensa y crece solo** 🌱

*Inspirado en el comportamiento del Slime Mold (Physarum Polycephalum)*

[![GitHub Actions](https://img.shields.io/badge/Ejecutado_por-GitHub_Actions-blue?logo=github)](https://github.com/Gunther-Frager/physarum-mind/actions)
[![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)](https://www.python.org/)
[![Gemini](https://img.shields.io/badge/Gemini-1.5_Flash-red?logo=google)](https://ai.google.dev/)

</div>

---

## 🎯 Objetivo y Alcance

**Physarum-Mind** es un experimento de inteligencia artificial autónoma que simula el proceso de pensamiento biológico:

1. **Autónomo**: Piensa continuamente sin intervención humana (cada 1 hora)
2. **Persistente**: Almacena notas e ideas que crecen en una red semántica
3. **Generativo**: Crea síntesis novedosas fusionando conceptos relacionados
4. **Iterativo**: Aprende qué conexiones son valiosas y cuáles olvida

### ¿Qué Hace?

```
NOTAS INPUT    →  BÚSQUEDA DE PATRONES  →  SÍNTESIS  →  NUEVAS NOTAS
(ideas, conceptos)  (similitud semántica)   (Gemini)      (autogeneradas)
        ↑_______________|_______________|_____________↓
                    RED NEURONAL PERSISTENTE
```

El sistema actúa como un **segundo cerebro distribuido** que:
- Relaciona ideas entre sí
- Olvida conexiones débiles (evaporación)
- Refuerza patrones útiles
- Engendra pensamiento nuevo

---

## 🏗️ Arquitectura

```
physarum-mind/
├── slime_agent.py              # 🧠 Motor principal de pensamiento
├── github_issues_manager.py    # 🔄 Puente GitHub ↔ Sistema
├── dashboard_generator.py      # 📊 Visualizador web
├── notas/                      # 📖 Base de conocimiento
│   ├── expansión acelerada.md    (idea inicial)
│   ├── expansión del universo.md (idea inicial)
│   └── Sintesis_*.md             (ideas autogeneradas)
├── grafo.json                  # 🌐 Red de conexiones (persistente)
├── docs/
│   └── index.html              # 📊 Dashboard web interactivo
└── .github/workflows/
    └── main.yml                # ⏰ Configuración de ejecución automática
```

---

## 🔄 Cómo Funciona: El Ciclo de Pensamiento

Cada hora, el agente ejecuta este ciclo biológico:

### 1️⃣ **OLFATO**: Calcula Embeddings Semánticos
```python
# Cada nota se convierte en un vector de 384 dimensiones
embeddings = embed_model.encode(todas_las_notas)
```
- Modelo: `sentence-transformers/all-MiniLM-L6-v2` (33 MB, ultra-rápido)
- Captura el significado semántico de cada palabra/frase

### 2️⃣ **METABOLISMO**: Evaporación del Olvido
```python
# Las conexiones se debilitan naturalmente (olvido)
fuerza_enlace = fuerza_enlace * 0.95  # Pierde 5% por ciclo
```
- Simula cómo los recuerdos se desvanecen
- Evita que ideas obsoletas dominen

### 3️⃣ **EXPLORACIÓN**: Busca de Similitud
```python
# Similitud coseno: ¿Qué notas son semánticamente cercanas?
similitud = dot_product(emb_a, emb_b) / (norm(a) * norm(b))
```
- Si `similitud > 0.6` → registra conexión
- Se acumula con ciclos anteriores
- Threshold de síntesis: `fuerza > 1.5`

### 4️⃣ **CRECIMIENTO**: Generación de Síntesis
```
CONEXIÓN FUERTE → Llama a Gemini API
 (Nota A + Nota B) → SÍNTESIS (nueva idea)
                   → Guarda como Sintesis_*.md
```
- Prompt biológico: *"Eres un Slime Mold. Fusiona estos conceptos"*
- Máx 150 palabras
- Se publica como Issue etiquetado `#synthesis`

### 5️⃣ **INVESTIGACIÓN** ← ⭐ NUEVA FASE (v2)

```python
# Busca automáticamente en fuentes externas confiables
# para enriquecer notas con conocimiento verificado

ejecutar_investigacion()
  ├─ Para cada nota sin "## Fuentes Externas":
  │  ├─ Detecta @investigar keywords (control manual) ← PRIORITARIO
  │  ├─ Si no hay keywords → Extrae temas con n-gramas
  │  ├─ Busca en: Wikipedia, arXiv, PubMed, NewsAPI
  │  ├─ Valida CONTRA NOTA ORIGINAL (previene falsos positivos)
  │  └─ Enriquece nota con "## Fuentes Externas"
  └─ Anota grafo.json con nuevas fuentes
```

**¿Qué es Knowledge Ingester v2?**

Un módulo que enriquece notas con conocimiento verificado de fuentes confiables. 

**Problema que resuelve:**

```
Nota: "Expansión del Universo"
Contenido: "El espaciotiempo se estira..."

v1 BUG: Busca "Estira" → Wikipedia retorna "Estira (Ciudad Griega)" ❌

v2 FIX: 
  1. Usa n-gramas: "expansión acelerada", "espaciotiempo"
  2. Valida contra nota original: similitud("Ciudad", "universo") = 0.15 ❌
  3. Rechaza resultado irrelevante ✓
```

**Características:**

- ✅ **Validación POST-BÚSQUEDA** contra nota original (previene 90% falsos positivos)
- ✅ **Extracción inteligente** con n-gramas (frases, no palabras individuales)
- ✅ **Control manual** vía @investigar keywords en notas
- ✅ **Configuración centralizada** con 12+ booleans on/off
- ✅ **Fuentes confiables**: Wikipedia, arXiv, PubMed, NewsAPI (todas gratis)

**Cómo usar:**

Opción 1 - Automático:
```markdown
# Mi Nota Sobre Física

El contenido aquí...
```
→ Sistema busca automáticamente, valida resultados, enriquece

Opción 2 - Manual (Recomendado):
```markdown
# Mi Nota Sobre Física

@investigar: relatividad general, mecánica cuántica

El contenido aquí...
```
→ Sistema busca exactamente lo especificado, valida, enriquece

**Resultado:**
```markdown
# Mi Nota Sobre Física

@investigar: relatividad general, mecánica cuántica

El contenido...

## Fuentes Externas

### Wikipedia
- **Relatividad General** (relevancia: 0.82)
  https://es.wikipedia.org/wiki/Relatividad_general
  
### arXiv
- **Modern Approaches to General Relativity** (relevancia: 0.78)
  https://arxiv.org/abs/2301.12345
```

📖 **Docs completa:** Ver [KNOWLEDGE_INGESTER_V2_CHANGELOG.md](KNOWLEDGE_INGESTER_V2_CHANGELOG.md) y [KNOWLEDGE_INGESTER_ARCHITECTURE.md](KNOWLEDGE_INGESTER_ARCHITECTURE.md)

---

## 🔄 Cómo Funciona: El Ciclo de Pensamiento

### Opción 1: Crear Issues con Label `idea` ✨ (Recomendado)

1. Abre tu repo: `github.com/username/physarum-mind`
2. Ve a **Issues** → **New Issue**
3. Escribe tu idea en el cuerpo
4. **Etiqueta con `idea`** (crea el label si no existe)
5. ¡Listo! El agente la importará en el próximo ciclo

**Ejemplo**:
```
Title: Relación entre conciencia y tiempo

Body: La percepción del tiempo podría estar ligada 
a la profundidad de la conciencia. ¿Es el tiempo 
una propiedad emergente del observador?
```

→ Se guardará como `/notas/idea_XX_Relación_entre_conciencia_y_tiempo.md`

### Opción 2: Crear Notas Directamente

1. Clona el repo localmente
2. Crea nuevos `.md` en `/notas/`
3. Haz push
4. El agente los procesará automáticamente

---

## 📊 Dashboard Web

El sistema genera un dashboard interactivo en **real-time**:

```
https://username.github.io/physarum-mind
```

### Características:
- 🌐 **Red visual** (D3.js): Nodos = notas, líneas = conexiones
- 📈 **Estadísticas**: Cantidad de nodos, similitudes, síntesis generadas
- 🔗 **Top Conexiones**: Las relaciones más fuertes del momento
- ♻️ **Auto-actualización**: Cada hora

Para activarlo:
1. Ve a **Settings** → **Pages**
2. Selecciona rama: `main`
3. Carpeta: `/docs`
4. ¡Guardado! Ya está disponible en 2-3 minutos

---

## ⏰ Frecuencia de Ejecución

**Por defecto: Cada 1 hora** (24 ciclos/día de pensamiento)

### Cambiar la Frecuencia

Edita [.github/workflows/main.yml](.github/workflows/main.yml):

```yaml
on:
  schedule:
    # Descomentar la opción deseada:
    - cron: '0 * * * *'       # ← CADA HORA (24 veces/día) [ACTUAL]
    # - cron: '0 */2 * * *'   # ← Cada 2 horas (12 veces/día)
    # - cron: '0 */6 * * *'   # ← Cada 6 horas (4 veces/día)
    # - cron: '0 */12 * * *'  # ← Cada 12 horas (2 veces/día)
```

**Referencia de Cron**:
```
┌───────────── minuto           (0 - 59)
│ ┌───────────── hora           (0 - 23)
│ │ ┌───────────── día          (1 - 31)
│ │ │ ┌───────────── mes        (1 - 12)
│ │ │ │ ┌───────────── día semana (0 - 6)
│ │ │ │ │
│ │ │ │ │
* * * * *
```

- `0 * * * *` = en el minuto 0 de cada hora
- `*/6` = cada 6 unidades (6, 12, 18, 00...)

**Guardar cambios:**
```bash
git add .github/workflows/main.yml
git commit -m "⏰ Cambiar frecuencia a cada 2 horas"
git push
```

---

## 🔐 Configuración (Secrets)

El workflow necesita 3 secrets de GitHub:

### 1. `GEMINI_API_KEY` (Requerido para síntesis)
1. Ve a [ai.google.dev](https://ai.google.dev/)
2. Crea una API Key gratuita
3. En **Settings** → **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Name: `GEMINI_API_KEY`
6. Value: Tu key completa

### 2. `HF_TOKEN` (Opcional - Sentence Transformers)
1. Ve a [huggingface.co](https://huggingface.co/settings/tokens)
2. Crea token de acceso
3. Mismo proceso de arriba
4. Name: `HF_TOKEN`

### 3. `GITHUB_TOKEN` (Automático)
- ✅ Ya incluido por defecto en GitHub Actions
- Se usa para leer/escribir issues

---

## 📦 Dependencias

```txt
google-generativeai      # Gemini API
sentence-transformers   # Embeddings (384-dim. vectors)
numpy                    # Matemáticas
PyGithub                 # GitHub API
requests                 # HTTP
```

**Instalación local** (si ejecutas manualmente):
```bash
pip install -r requirements.txt
```

---

## 🚀 Uso Local

Para probar el agente en tu máquina:

```bash
# 1. Clonar
git clone https://github.com/tu-usuario/physarum-mind
cd physarum-mind

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
export GEMINI_API_KEY="tu_api_key"
export GITHUB_TOKEN="tu_github_token"

# 4. Ejecutar el ciclo completo
python slime_agent.py              # Pensar
python github_issues_manager.py --import    # Importar ideas de issues
python github_issues_manager.py --publish   # Publicar síntesis como issues
python dashboard_generator.py      # Actualizar dashboard
```

---

## 📊 Parámetros Ajustables

### slime_agent.py (Pensamiento)

En [slime_agent.py](slime_agent.py), puedes tunear:

```python
EVAPORATION_RATE = 0.95          # Olvido: 0.9 = rápido, 0.99 = lento
THRESHOLD_CONECTAR = 0.6         # Sensibilidad: 0.5 = muy sensible, 0.8 = selectivo
THRESHOLD_SINTESIS = 1.5         # Cuándo sintetizar: 1.0 = frecuente, 2.0 = raro
MODELO_EMBEDDING = 'all-MiniLM-L6-v2'  # Cambiar si necesitas mejor precisión
```

### knowledge_ingester.py (Investigación) ← NUEVO

En [knowledge_ingester.py](knowledge_ingester.py), puedes controlar:

```python
# 🎛️ ACTIVACIÓN/DESACTIVACIÓN
ENABLE_AUTOMATIC_INVESTIGATION = True       # 🤖 Investigar automáticamente
ENABLE_MANUAL_LABELS = True                 # 🏷️  Detectar labels en issues
ENABLE_KEYWORD_TRIGGERS = True              # 🔑 Detectar @investigar en notas
ENABLE_POST_SEARCH_VALIDATION = True        # ⚠️  CRÍTICO: Validar contra nota

# 🔍 EXTRACCIÓN
ENABLE_NGRAM_EXTRACTION = True              # Usar frases vs palabras individuales
NGRAM_SIZE = 2                              # Bigramas (2 palabras)

# 📊 VALIDACIÓN
CONFIDENCE_THRESHOLD = 0.65                 # Similitud mín con query
RELEVANCE_THRESHOLD_POST_SEARCH = 0.50      # Similitud mín con NOTA

# ⏱️ RATE LIMITING (APIs gratis)
LIMIT_SEARCHES_PER_CYCLE = 5                # Max 5 notas/ciclo
LIMIT_SEARCHES_PER_NOTE = 3                 # Max 3 temas/nota
LIMIT_RESULTS_PER_SOURCE = 3                # Max 3 resultados/fuente
```

**Todos los parámetros se imprimen en cada ejecución para transparencia**

---

## 🧪 Ejemplo de Flujo Completo

**Tu aportación:**
```markdown
# Issue etiquetado con "idea"
Title: ¿Y si el universo es consciente?
```

**Ciclo Automático (1 hora después):**
```
1. github_issues_manager.py lee el issue
2. Crea: /notas/idea_1_Y_si_el_universo_es_consciente.md
3. Cierra el issue con comentario: "✅ Idea importada"

4. slime_agent.py busca similitudes
5. Encuentra conexión con: "expansión del universo.md"
6. Similitud: 0.78 > 0.6 ✓
7. Fuerza acumulada: 1.82 > 1.5 ✓
8. ¡SÍNTESIS! Gemini combina ambas ideas:

   "La expansión acelerada del universo podría 
    ser la respiración de una entidad consciente..."

9. Crea: /notas/Sintesis_universo_conciencia.md
10. Crea Issue con label "synthesis"

11. dashboard_generator.py visualiza la red
12. Archivo enviado a /docs/index.html
13. Visible en: https://username.github.io/physarum-mind
```

---

## 🐛 Troubleshooting

### ❌ "No se generan síntesis"
- ✓ Verifica que tengas > 2 notas
- ✓ Confirma que GEMINI_API_KEY está en Secrets
- ✓ Revisa Logs en **Actions** tab

### ❌ "No se importan ideas desde issues"
- ✓ Asegúrate que el label sea exactamente `idea`
- ✓ Confirma que GITHUB_TOKEN está configurado
- ✓ Revisa que el issue esté en estado "open"

### ❌ "Dashboard no se actualiza"
- ✓ Anda a **Settings** → **Pages** y verifica
- ✓ Espera 2-3 minutos después del push
- ✓ Refresca con `Ctrl+Shift+R`

### ❌ "Error de API limitada"
- ✓ Gemini tiene 60 RPM gratis
- ✓ Si ejecutas mult ciclos rápido, espera un poco
- ✓ Aumenta la frecuencia del cron a > 2 horas

---

## 📈 Casos de Uso

### 💡 Investigación
Alimenta el sistema con tus papers/apuntes. El agente encontrará conexiones que quizás no viste.

### 🎓 Enseñanza
Usa para demostrar emergencia y pensamiento sistémico.

### 🧬 Biología Computacional
Experimenta con parámetros: evaporación, thresholds, embeddings.

### 📝 Escritura Creativa
Genera ideas nuevas para novelas, historias, poesía.

---

## 🔬 Inspiración Biológica

El **Slime Mold** es un organismo unicelular sin cerebro que:
- Se mueve hacia alimento (quimiotaxis)
- Trazo rastros químicos que evaporan
- Refuerza caminos útiles (estigmergia)
- Resuelve problemas complejos (laberintos óptimos)

**Physarum-Mind** replica este comportamiento con ideas:
- Búsqueda de conceptos similares (quimiotaxis semántica)
- Rastros de conexión que se debilitan (evaporación)
- Refuerzo de patrones útiles (síntesis)
- Emergencia de pensamiento nuevo

---

## 📄 Licencia

MIT License - Úsalo libremente

---

## 🤝 Contribuir

¿Sugerencias? ¿Mejoras? Abre un **Issue** o **PR**.

Ideas para expandir:
- [ ] Análisis de sentimiento en síntesis
- [ ] Exportar grafo como GraphML
- [ ] API REST para consultar red
- [ ] Multi-idioma
- [ ] Integración con Discord/Slack

---

## 📞 Soporte

Para problemas:
1. Revisa [Issues](../../issues)
2. Abre [nuevo Issue](../../issues/new)
3. Incluye logs de GitHub Actions

---

<div align="center">

**Hecho con 🧠 y 💚 por Gunther Frager**

<sub>*"Las mejores ideas surgen solas cuando se cruzan las ideas correctas"*</sub>

</div>