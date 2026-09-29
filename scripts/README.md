# 📁 Scripts y Operaciones del Organismo Digital

Este directorio agrupa los scripts operativos, de ciclo vital y de mantenimiento del sistema, clasificados por su función biológica:

---

## 🧬 1. Ciclo Vital del Subagente (Modo CLI)

* **`diferenciar.py`**:
  * **Función:** Induce la diferenciación terminal de la Célula Madre totipotente hacia una especialidad médica, cuantitativa o técnica.
  * **Uso:**
    ```bash
    python3 scripts/diferenciar.py <especialidad> "<misión>"
    ```

* **`desdiferenciar.py`**:
  * **Función:** Aplica los *Factores de Yamanaka* digitales. Empaqueta el subagente maduro en un backup comprimido (`experiment/backups/`) y devuelve la Célula Madre a la Iteración 0 virginal.
  * **Uso:**
    ```bash
    python3 scripts/desdiferenciar.py
    ```

---

## ⚡ 2. Interacción en Tiempo Real

* **`ordenar.py`**:
  * **Función:** Inyecta un caso clínico o directiva en caliente al subagente sin detener el bucle del motor evolutivo.
  * **Uso:**
    ```bash
    python3 scripts/ordenar.py "<descripción del caso o cálculo>"
    ```

---

## 🛠️ 3. Mantenimiento y Homeostasis

* **`resetear_organismo.py`**:
  * **Función:** Purga completamente la anatomía pluricelular (`body/organos/`), crea un backup de seguridad y restaura el estado a Tabula Rasa.
  * **Uso:**
    ```bash
    python3 scripts/resetear_organismo.py --force
    ```
