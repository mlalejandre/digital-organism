# 🧬 Organismo Digital — Computación Orgánica y Morfogénesis Autónoma

> **Arquitectura de Agentes IA Pluricelulares con Diferenciación Jerárquica, Sandboxing en Docker y Sistema Inmunológico Adversarial.**

[![Licencia](https://img.shields.io/badge/licencia-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/docker-sandboxed-2496ED)](https://www.docker.com/)

---

## 🌟 La Visión: De la Célula Madre al Organismo Pluricelular

Los sistemas multi-agente tradicionales se enfrentan a un dilema irresoluble:
1. **El Agente Monolítico:** Trata de abarcarlo todo en un solo contexto; colapsa por alucinaciones y saturación de tokens.
2. **El Enjambre Plano:** Decenas de agentes conversando en un chat común; la comunicación escala a O(N^2), devorando tokens en ruido y cortesías.

**Organismo Digital** resuelve este cuello de botella aplicando la solución que la biología descubrió hace mil millones de años: **la pluricelularidad jerárquica y fractal**.

El sistema no pre-programa agentes para cada tarea:
Inicia como una **Célula Madre Totipotente** en estado de *Tabula Rasa*. Al recibir un estímulo o directiva, ejecuta una **Cascada Cognitiva** que delibera qué macro-órgano y tejido deben actuar. Si no existe una célula especializada competente, la Célula Madre engendra una nueva célula mediante **morfogénesis en caliente**, compila código determinista en Python, lo valida en un contenedor Docker efímero y lo integra en la anatomía viva del organismo.

```text
               [ NÚCLEO: Célula Madre Totipotente ]
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       [ ÓRGANO: Macro-Dominio ]       [ ÓRGANO: Macro-Dominio ]
               │                               │
       ┌───────┴───────┐                       │
       ▼               ▼                       ▼
   [ TEJIDO ]      [ TEJIDO ]              [ TEJIDO ]
       │               │                       │
   ┌───┴───┐       ┌───┴───┐               ┌───┴───┐
   ▼       ▼       ▼       ▼               ▼       ▼
 [CÉLULA][CÉLULA] [CÉLULA][CÉLULA]       [CÉLULA][CÉLULA]
  (Tools + Tests en Sandbox Docker)       (Tools + Tests en Sandbox Docker)
```

---

## ⚡ Pilares del Sistema

### 1. La Cascada Cognitiva
Ante cualquier directiva o problema entrante:
* **El Núcleo** clasifica el macro-dominio y selecciona (o engendra) el **Órgano** correspondiente.
* **El Órgano** selecciona el **Tejido** funcional idóneo.
* **El Tejido** evalúa su catálogo de células:
  * Si una célula existente cubre la operación de forma exacta, **se reutiliza de inmediato**.
  * Si la tarea es nueva o requiere composición secuencial multietapa, se declara **«Morfogénesis requerida»** y la Célula Madre crea una célula especializada.

### 2. Primacía del Runtime (IEEE 754 vs Alucinación)
* **Prohibida la aritmética mental:** Los modelos de lenguaje son probabilísticos e imprecisos para el cálculo flotante exacto.
* **Python es la única fuente de verdad:** Toda operación matemática, científica o cuantitativa se ejecuta mediante scripts en Python con estándar IEEE 754.
* **Sandboxing Aislado en Docker:** Cada ejecución corre en un contenedor efímero (`nikolaik/python-nodejs`), con sistema de archivos protegido (`--read-only`), límites de memoria (`2g`), CPU (`2.0`) y sin riesgo de contaminar el entorno host.

### 3. Sistema Inmunológico y Homeostasis Tisular
* **Auditoría Adversarial:** Un sistema de estrés destructivo (*red-teaming*) que examina al organismo en cuatro frentes: Casos Límite, Estrés de Escala, Alta Precisión (8 decimales) y Problemas Compuestos.
* **Memoria de Antígenos:** Cada fallo detectado en una auditoría se almacena con su contraejemplo exacto.
* **Poda Tisular Consciente (`/remodelar`):** La Célula Madre audita la anatomía, lee los antígenos y fusiona células redundantes o frágiles en herramientas universales paramétricas, preservando el principio de no regresión funcional.

### 4. Tabula Rasa Reversible
* El organismo puede ser reseteado en cualquier instante a su estado de **Célula Madre Totipotente virginal**, purgando los tejidos específicos pero conservando intacto su genoma, su servidor y su capacidad de auto-construcción para cualquier nuevo dominio (medicina, finanzas, derecho, ingeniería).

---

## 📂 Estructura del Repositorio

```text
organismo-digital/
├── aprendizaje/                # Suite de especialización y estrés adversarial
│   ├── aprende_matematicas.py  # Currículo progresivo (de fundamentos a doctorado)
│   ├── auditor_matematico.py   # Auditor adversarial en 4 dimensiones de estrés
│   └── entrenador_adversarial.py # Entrenador inmunitario de auto-reparación en Docker
├── body/                       # El cuerpo físico del organismo
│   ├── memory/                 # Estado biológico, hipocampo y contratos
│   ├── organos/                # Anatomía pluricelular viva (Órganos ➜ Tejidos ➜ Células)
│   ├── planner/                # Hojas de ruta primordiales
│   ├── tools/                  # Órganos basales (búsqueda web, lectura profunda)
│   └── autoprompt.txt          # Genoma del agente
├── experiment/                 # Zona de telemetría y auditoría externa del host
│   ├── backups/                # Respaldos comprimidos (.tar.gz) automáticos
│   └── reasoning/              # Trazas de razonamiento CoT por iteración
├── scripts/                    # Operaciones de ciclo vital y mantenimiento
│   ├── diferenciar.py          # Inductor CLI de especialización
│   ├── desdiferenciar.py       # Factores de Yamanaka (retorno a Tabula Rasa)
│   ├── ordenar.py              # Inyector de directivas en tiempo real
│   └── resetear_organismo.py   # Purgado anatómico completo a Célula Madre
├── src/                        # Motor cognitivo del organismo
│   ├── organismo/
│   │   ├── anatomia.py         # Clases estructurales (Organo, Tejido, Celula)
│   │   ├── celula_madre.py     # Núcleo totipotente y leyes de síntesis
│   │   ├── gpu_manager.py      # Conector SSH y control de VRAM
│   │   ├── motor.py            # Orquestador de cascada cognitiva y homeostasis
│   │   ├── perfeccionamiento.py# Bucle de auto-reparación en Docker
│   │   └── servidor.py         # API REST y servidor HTTP integrado
│   ├── body.py                 # Gestor seguro de archivos
│   ├── config.py               # Configuración central de rutas y endpoints
│   ├── executor.py             # Ejecutor Docker multi-lenguaje e inline
│   ├── llm_client.py           # Cliente LLM con streaming y rescate de acciones
│   └── main.py                 # Bucle autónomo clásico CLI
├── web/
│   └── index.html              # Dashboard visual con telemetría y visor CoT en vivo
├── exe_servidor.py             # Lanzador del Servidor y Dashboard
├── exe_estructura.py           # Exportador de estructura para auditorías
├── exe_limpieza.py             # Limpiador seguro de residuos temporales
├── prompt_inmutable.txt        # Ley fundamental y principios cognitivos inviolables
└── requirements.txt            # Dependencias del host
```

---

## 🚀 Puesta en Marcha Rápida

### Requisitos Previos
* **Docker Desktop** activo (para el músculo ejecutor aislado).
* **Python 3.10+**.
* **Endpoint LLM compatible con OpenAI API:**  
  Probado y optimizado con `llama-server` corriendo **Nail-Qwen-35B-A3B** (o cualquier modelo abierto como Qwen 2.5 32B/72B, Llama 3 o DeepSeek).

### 1. Instalación
```bash
# Crear entorno virtual e instalar dependencias del host
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Descargar la imagen de ejecución universal para Docker
docker pull nikolaik/python-nodejs:python3.11-nodejs20
```

### 2. Iniciar el Organismo Digital
Inicia el servidor interactivo:
```bash
python3 exe_servidor.py
```

Abre tu navegador en `http://localhost:8888` para interactuar con el **Dashboard visual en vivo**:
* Envía estímulos o problemas complejos.
* Observa la cascada cognitiva deliberar en tiempo real.
* Mira el visor de razonamiento (*Chain-of-Thought*) en streaming directo desde la GPU.
* Inspecciona la anatomía de órganos, tejidos y células palpitando según su estado biológico (*Reposo, Actividad, Aprendiendo o Fallo*).

---

## 🧪 Pruebas Adversariales y Auto-Evolución

Para evaluar la solidez del organismo frente a trampas numéricas complejas (casos límite, alta precisión a 8 decimales, problemas compuestos de varias etapas):

```bash
# Ejecutar auditoría adversarial ciega
python3 aprendizaje/auditor_matematico.py --muestras 1

# Ejecutar el entrenador inmunitario autónomo (auto-reparación guiada)
python3 aprendizaje/entrenador_adversarial.py
```

---

## 🛡️ Seguridad y Sandboxing

* **Cero ejecución en el Host:** Ningún código generado por el modelo se ejecuta en tu máquina anfitriona; todo corre dentro de contenedores Docker efímeros creados al vuelo con permisos restringidos (`--read-only`, límites estrictos de CPU y RAM).
* **Auditoría Inmutable:** Cada llamada a `DELETE` o `EXECUTE` queda asentada en `experiment/logs/audit.jsonl`.

---

## 📄 Licencia

Distribuido bajo la Licencia MIT. Consulta el archivo LICENSE para más información.
