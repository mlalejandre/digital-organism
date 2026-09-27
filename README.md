cat << 'EOF' > README.md
# 🧬 Nail-StemCell — Autonomous AI Stem Cell Architecture

> **Fase Tres:** De la *Tabula Rasa* al Organismo Digital.  
> Framework de agentes autónomos auto-evolutivos con diferenciación terminal bajo demanda, testing por invariantes deterministas, aislamiento en Docker y desdiferenciación reversible.

---

## 🌟 La Visión: Computación Orgánica y Morfogénesis

Los sistemas multi-agente tradicionales se enfrentan a un dilema irresoluble:
1. **El Agente Monolítico:** Trata de abarcarlo todo; colapsa por alucinaciones y saturación de contexto.
2. **El Enjambre Plano:** Decenas de agentes hablando en un chat común; la comunicación escala a O(N²), devorando tokens en ruido y cortesías.

**Nail-StemCell** resuelve este cuello de botella aplicando la solución que la biología descubrió hace mil millones de años: **la pluricelularidad jerárquica y fractal**.

El proyecto no pre-programa agentes para cada tarea: inicia como una **Célula Madre Totipotente** (*tabula rasa*), recibe una directiva de especialización (`diferenciar.py`), investiga la literatura de consenso, programa sus propias herramientas deterministas en Python, las valida en entornos Docker efímeros y sella un contrato MCP (*Model Context Protocol*). 

---

## ⚡ Características del Sistema

1. **Diferenciación Terminal Reversible:**
   - `python3 diferenciar.py <especialidad> <mision>`: Induce la diferenciación hacia cualquier dominio (ej. Nefrología, Farmacocinética, Finanzas Cuantitativas).
   - `python3 desdiferenciar.py`: Aplica el equivalente digital a los **Factores de Yamanaka**, empaquetando al subagente adulto en un `.tar.gz` reutilizable y devolviendo la memoria y el cuerpo a la Iteración 0 totipotente.
2. **Interacción en Tiempo Real con el Orquestador:**
   - `python3 ordenar.py "<caso o tarea>"`: Inyecta casos clínicos o problemas en caliente al subagente sin detener el bucle de ejecución.
3. **Principio de Primacía de Runtime & Testing por Invariantes:**
   - Prohíbe taxativamente la aritmética mental flotante dentro del pensamiento.
   - Python (IEEE 754) es la única fuente de verdad: los tests unitarios validan monotonía (si x sube, y baja), condiciones de borde y rangos plausibles, eliminando falsos positivos por redondeo.
4. **Ejecutor Seguro en Docker (Músculo Aislado):**
   - Cada acción EXECUTE corre en un contenedor efímero con red bridge, permisos root (--user 0:0) y soporte para Shebangs universales (python3, bash, node).
   - Soporta **evaluación inline** (`python3 -c "..."`), evitando la creación innecesaria de archivos temporales.
5. **Resiliencia Extrema en Inferencia:**
   - **Ventana de 8.192 tokens:** Espacio holgado para razonamiento profundo (Chain of Thought).
   - **Auto-reparación de JSON truncado:** Si la generación se corta por tokens al final de un script, el parser cierra comillas y llaves automáticamente y rescata la acción.
   - **Filtro Anti-Bucles 3x:** Detecta repeticiones patológicas reales sin sabotear la redacción de código.
   - **Poda de Contexto (_clip):** Evita desbordamientos de buffer HTTP 400 recortando salidas masivas de búsqueda web.

---

## 🔄 El Ciclo Vital de Maduración (4 Fases)

```text
       [ Célula Madre Totipotente ]
                    │
           1. INVESTIGAR (web_search / researcher)
                    │
           2. MEMORIZAR (knowledge_base)
                    │
           3. SINTETIZAR Y VERIFICAR (tools/ + tests/ en Docker)
                    │
           4. COMPROMISO TERMINAL (interface_generator -> MCP)
                    │
                    ▼
       [ Subagente Experto Maduro ] ──(desdiferenciar.py)──> [ Retorno a Célula Madre ]
```

1. **INVESTIGAR:** La célula madre usa `tools/web_search.py` y `tools/researcher.py` para descubrir ecuaciones y consensos públicos (máximo 2-3 rondas, anti-parálisis de paywalls).
2. **MEMORIZAR:** Almacena constantes numéricas y reglas en `memory/knowledge.json`.
3. **SINTETIZAR Y VERIFICAR:** Programa las herramientas en `tools/` y sus tests en `tools/tests/`. Ejecuta los tests en Docker hasta obtener 100% de éxito.
4. **COMPROMISO TERMINAL Y CONTRATO:** Genera el contrato `memory/interface.json` (MCP), sobrescribe su identidad permanente en `autoprompt.txt` y actualiza `memory/state.json` a `"fase": "maduro_listo_para_orquestador"`.

---

## 📂 Estructura del Repositorio

```text
celula madre/
├── body/                       # Espacio físico del agente (montado en /body en Docker)
│   ├── memory/                 # Estado, hipocampo (knowledge.json) y contrato MCP (interface.json)
│   ├── planner/                # Hojas de ruta y metas activas (goals.json)
│   ├── tools/                  # Órganos basales e instrumental programado por el agente
│   │   └── tests/              # Batería de pruebas unitarias deterministas
│   └── autoprompt.txt          # Genoma del agente (instrucciones evolutivas persistentes)
├── experiment/                 # Fuera del alcance del agente (auditoría del anfitrión)
│   ├── backups/                # Archivos biológicos comprimidos (.tar.gz) de subagentes
│   ├── logs/                   # Historial append-only de iteraciones y auditoría
│   └── reasoning/              # Trazas de razonamiento CoT guardadas por iteración
├── src/                        # Motor del bucle evolutivo y cliente LLM
│   ├── body.py                 # Gestor de sistema de archivos seguro
│   ├── config.py               # Configuración de red, tokens y rutas
│   ├── executor.py             # Ejecutor Docker multi-lenguaje e inline
│   ├── llm_client.py           # Cliente HTTP OpenAI-compatible con streaming y CoT
│   └── main.py                 # Orquestador del bucle iterativo
├── diferenciar.py              # Inductor de especialización
├── ordenar.py                  # Inyector de casos/tareas en tiempo real con catálogo de tools
├── desdiferenciar.py           # Factores de Yamanaka (regreso a célula madre)
├── prompt_inmutable.txt        # Ley fundamental y principios cognitivos inviolables
└── requirements.txt            # Dependencias del anfitrión
```

---

## 🚀 Requisitos y Puesta en Marcha

### Requisitos Previos
- Docker Desktop o daemon compatible (`docker run`).
- Python 3.10+.
- Endpoint LLM compatible con OpenAI API (ej. llama-server en local o remoto, vLLM, Ollama o MLX).

### Instalación Rápida

```bash
# 1. Crear entorno virtual e instalar dependencias
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Descargar la imagen de ejecución universal para Docker
docker pull nikolaik/python-nodejs:python3.11-nodejs20
```

---

## 📖 Guía de Uso

### 1. Inducir la Diferenciación
Para transformar la célula madre virgen en un especialista:

```bash
# Ejemplo: Especialización en Nefrología Clínica
python3 diferenciar.py "nefrologia" "Especialízate en calculadoras clínicas de nefrología para resolver problemas clínicos reales"

# Ejemplo: Especialización en Finanzas Cuantitativas
python3 diferenciar.py "finanzas_cuantitativas" "Especialízate en cálculo de Black-Scholes, griegas y modelos de Valor en Riesgo (VaR)"
```

### 2. Enviar Tareas o Casos en Tiempo Real
Con el bucle corriendo en una terminal, abre otra pestaña para enviar una orden:

```bash
python3 ordenar.py "Varón de 68 años con insuficiencia cardíaca y furosemida. Na 132, K 5.7, Urea 95, Cr 2.3. Orina: Na 25, K 18, Urea 180, Cr 45, Osm 350. Evalúa CKD-EPI 2021, determina si es prerrenal mediante FEUrea y calcula el TTKG."
```

### 3. Desdiferenciación (Regreso a Célula Madre)
Cuando desees reutilizar la célula madre para una nueva misión sin perder el trabajo previo:

```bash
# Detén el bucle (Ctrl + C) y ejecuta:
python3 desdiferenciar.py
```
- Empaqueta el subagente actual en `experiment/backups/subagente_<especialidad>_<fecha>.tar.gz`.
- Purga las herramientas especializadas y restaura el estado a la **Iteración 0 totipotente**.

---

## 🛡️ Seguridad y Sandboxing

- Cada ejecución se realiza en un contenedor Docker con sistema de archivos de solo lectura (`--read-only`), límite de memoria (`2g`), CPU (`2.0`) y límite de procesos (`--pids-limit 128`).
- El agente solo tiene acceso de lectura/escritura a la carpeta `/body` montada como volumen.
- Las acciones sensibles (`DELETE` y `EXECUTE`) se registran en un log de auditoría inmutable (`experiment/logs/audit.jsonl`).

---

## 📄 Licencia

Distribuido bajo la Licencia MIT. Consulta el archivo `LICENSE` para más información.
EOF
