# ⚙️ Guía de Configuración - Physarum-Mind

Documento de referencia rápida para configurar el sistema por primera vez.

---

## 📋 Checklist de Setup (5 minutos)

- [ ] Fork/Clone el repositorio
- [ ] Crear `GEMINI_API_KEY`
- [ ] Agregar secrets a GitHub
- [ ] Verificar workflow en Actions
- [ ] Crear primeras ideas
- [ ] Activar GitHub Pages

---

## 1️⃣ Crear API Keys

### Gemini API Key (Requerido)

```bash
1. Ir a https://ai.google.dev
2. Click "Get API Key"
3. Seleccionar proyecto de Google Cloud
4. Copiar la key (empieza con "AIza...")
5. Guardarla en lugar seguro
```

**Límites gratuitos:**
- 60 solicitudes/minuto
- Generación de síntesis: ~1-2 segundos cada una

### HuggingFace Token (Opcional)

```bash
1. Ir a https://huggingface.co/settings/tokens
2. Create new token (read permission)
3. Copiar el token
```

*Opcional: Los embeddings funcionan sin esto, pero token acelera descargas*

---

## 2️⃣ Agregar Secrets a GitHub

```
GitHub → Repositorio → Settings → Secrets and variables → Actions
```

**Crear estos secrets:**

| Secret | Valor | Requerido |
|--------|-------|-----------|
| `GEMINI_API_KEY` | Tu API key de Google AI | ✅ Sí |
| `HF_TOKEN` | Token de HuggingFace | ⭕ Opcional |
| `GITHUB_TOKEN` | Automático (no hacer nada) | ✅ Auto |

**Cómo agregar:**
1. Click `New repository secret`
2. Name: `GEMINI_API_KEY`
3. Value: `AIza...` (tu key completa)
4. Click `Add secret`

---

## 3️⃣ Configurar Ejecución Automática

### Cambiar Frecuencia

Editar `.github/workflows/main.yml`:

```yaml
on:
  schedule:
    # Opción 1: Cada HORA (recomendado - 24 veces/día)
    - cron: '0 * * * *'
   
    # Opción 2: Cada 2 HORAS (12 veces/día)
    # - cron: '0 */2 * * *'
    
    # Opción 3: Cada 6 HORAS (4 veces/día)
    # - cron: '0 */6 * * *'
```

**Especificación Cron Rápida:**
```
Minuto  Hora  Día  Mes  Día_Semana
'0      *     *    *    *'
         ↑    ↑    ↑
       cada cada día
       hora  todos
```

- `0 * * * *` = 00:00, 01:00, 02:00... (cada hora)
- `0 */6 * * *` = 00:00, 06:00, 12:00, 18:00 (cada 6 horas)
- `*/30 * * * *` = cada 30 minutos

### Ejecutar Manualmente

GitHub Actions → Latido del Slime Mold → `Run workflow` → `Run`

---

## 4️⃣ Activar Dashboard Web

### Paso 1: Habilitar GitHub Pages

```
Repositorio → Settings → Pages
├─ Source: Deploy from a branch
├─ Branch: main
└─ Folder: /docs
```

### Paso 2: Esperar

- GitHub construye la página en 1-3 minutos
- Se publica en: `https://username.github.io/physarum-mind`

### Verificar Estado

```
Settings → Pages → "Your site is live at..."
```

---

## 5️⃣ Parámetros Ajustables

### En `slime_agent.py`

```python
# Biología del Sistema
EVAPORATION_RATE = 0.91
# ├─ 0.90 = Olvido rápido (más creativo, menos memoria)
# └─ 0.99 = Olvido lento (más memoria, menos novedad)

THRESHOLD_CONECTAR = 0.6
# ├─ 0.50 = Muy sensible (conecta casi todo)
# └─ 0.80 = Muy selectivo (solo conexiones claras)

THRESHOLD_SINTESIS = 1.5
# ├─ 1.0 = Generar síntesis frecuentemente
# └─ 2.0 = Solo conexiones muy fuertes
```

**Recomendaciones:**
- Principiante: Valores por defecto
- Creativo: ↓ EVAPORATION, ↓ THRESHOLD
- Riguroso: ↑ EVAPORATION, ↑ THRESHOLD

---

## 6️⃣ Estructura de Archivos

```
physarum-mind/
├── notas/
│   ├── expansión acelerada.md         # Notas iniciales
│   ├── expansión del universo.md
│   ├── idea_1_Tu_primera_idea.md      # Importadas desde issues
│   └── Sintesis_*.md                  # Autogeneradas
│
├── grafo.json                          # Estado persistente
├── .synthesis_published                # Log de síntesis publicadas
│
├── docs/
│   └── index.html                      # Dashboard (se regenera cada ciclo)
│
├── slime_agent.py                      # Motor principal
├── github_issues_manager.py            # Puente GitHub
├── dashboard_generator.py              # Visualización
│
├── .github/workflows/main.yml          # Configuración de ejecución
├── requirements.txt                    # Dependencias
└── README.md                           # Documentación
```

---

## 🔒 Variables de Entorno (Opcional - Usar en Local)

```bash
# Para ejecutar manualmente:
export GEMINI_API_KEY="AIza..."
export GITHUB_TOKEN="ghp_..."
export HF_TOKEN="hf_..."

# Luego ejecutar:
python slime_agent.py
python github_issues_manager.py --import
python github_issues_manager.py --publish
python dashboard_generator.py
```

---

## 🧪 Test Local

```bash
# 1. Instalar
pip install -r requirements.txt

# 2. Crear archivo de prueba
echo "# Test idea" > notas/test.md

# 3. Ejecutar ciclo
python slime_agent.py

# 4. Verificar grafo.json
cat grafo.json
```

---

## 📊 Monitorear Ejecución

### Ver Logs en GitHub

```
Repositorio → Actions → "Latido del Slime Mold"
  ├─ Workflow run
  ├─ Descargar repositorio
  ├─ Instalar dependencias
  ├─ Ejecutar Agente de Pensamiento
  ├─ Procesar Issues
  ├─ Publicar Síntesis
  └─ Generar Dashboard
```

### Ver Cambios

```
Repositorio → Commits
├─ Nuevos archivos en /notas/
├─ Actualización de grafo.json
└─ Dashboard en docs/index.html
```

---

## ❌ Solucionar Problemas

### "El workflow no ejecuta"
```
✓ Verificar Settings → Actions → General
✓ Confirmar que los workflows están habilitados
✓ Revisar que no hay archivos subidos del mismo nombre
```

### "Error 401: Invalid API Key"
```
✓ Copiar key completa (sin espacios)
✓ Verificar en GitHub Secrets → GEMINI_API_KEY
✓ Key debe empezar con "AIza"
```

### "No se generan síntesis"
```
✓ Verificar que hay 2+ notas
✓ Ver que similitud > 0.6 en logs
✓ Confirmar GEMINI_API_KEY en Secrets
```

### "Dashboard no se actualiza"
```
✓ Esperar 5 minutos (build de GitHub Pages)
✓ Hard refresh: Ctrl+Shift+R (Windows) o Cmd+Shift+R (Mac)
✓ Verificar Settings → Pages → rama main + carpeta /docs
```

---

## 📚 Recursos Adicionales

- [Documentación Gemini](https://ai.google.dev/docs)
- [Sentence Transformers](https://www.sbert.net/)
- [GitHub Actions Cron](https://crontab.guru/)
- [D3.js (Dashboard)](https://d3js.org/)

---

## 🎯 Próximos Pasos

1. **Agregar primeras ideas** → Issues con label `idea`
2. **Observar ciclos** → Actions tab
3. **Ver dashboard** → GitHub Pages
4. **Ajustar parámetros** → `slime_agent.py`
5. **Expandir** → Agregar más notas

---

<sub>¿Preguntas? Abre un [Issue](../../issues)</sub>
