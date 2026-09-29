from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import tarfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from body import Body
from executor import Executor

from .anatomia import Celula, EstadoBiologico, Organo, Tejido
from .celula_madre import CelulaMadreTotipotente, asegurar_omnipresencia_celular
from .gpu_manager import consultar_gpu_4090, is_remote_health_ok
from .perfeccionamiento import (
    ejecutar_bucle_autoperfeccionamiento,
    reparar_json_raw,
    sanitizar_argumentos_cli,
)


class OrganismoDigital:
    """Motor Cognitivo y Homeostático Pluricelular.
    Ejecuta todo código sintetizado dentro del Sandbox Executor (Docker).
    """

    def __init__(self, root_dir: Path):
        self.root = root_dir
        self.estado = EstadoBiologico.REPOSO
        self.organos: Dict[str, Organo] = {}
        self.celula_madre = CelulaMadreTotipotente(root_dir)
        self.historial_eventos: List[Dict[str, Any]] = []
        self.ultimo_resultado: str = "Organismo Digital en reposo basal. Esperando directiva."
        self._llm_streaming = False
        self._llm_stream_kind = "idle"
        self._llm_stream_reasoning = ""
        self._llm_stream_content = ""
        self.ultimo_prompt: str = ""

        self._lock = threading.Lock()
        self._processing_lock = threading.Lock()

        self.body = Body(root_dir / "body")
        self.executor = Executor(self.body)

        self._cargar_organos_existentes()

    def _auditar_conformidad(self, prompt: str, resultado: dict) -> str:
        prompt_lower = prompt.lower()

        # 1. Pluralidad trigonométrica
        trig_solicitadas = [f for f in ('seno', 'coseno', 'tangente', 'sin', 'cos', 'tan') if f in prompt_lower]
        if len(trig_solicitadas) >= 2:
            claves_resultado = [k.lower() for k in resultado.keys() if any(t in k.lower() for t in ('sin', 'sen', 'cos', 'tan'))]
            if len(claves_resultado) < 2:
                return "Discrepancia: La directiva solicitó múltiples funciones trigonométricas, pero la herramienta solo devolvió una."

        # 2. Solicitud dual de MCD y MCM
        if (
            ('mcd' in prompt_lower or 'máximo común divisor' in prompt_lower or 'maximo comun divisor' in prompt_lower) and
            ('mcm' in prompt_lower or 'mínimo común múltiplo' in prompt_lower or 'minimo comun multiplo' in prompt_lower)
        ):
            tiene_mcd = any('mcd' in k.lower() or 'gcd' in k.lower() or 'divisor' in k.lower() for k in resultado.keys())
            tiene_mcm = any('mcm' in k.lower() or 'lcm' in k.lower() or 'multiplo' in k.lower() or 'múltiplo' in k.lower() for k in resultado.keys())
            if not (tiene_mcd and tiene_mcm):
                return "Discrepancia: La directiva solicitó tanto MCD como MCM. Debe calcular ambos."

        # 3. Operaciones compuestas de descuento e IVA
        if ('descuento' in prompt_lower or 'rebaja' in prompt_lower) and ('iva' in prompt_lower or 'impuesto' in prompt_lower):
            claves = [k.lower() for k in resultado.keys()]
            if not any('final' in k or 'total' in k or 'precio' in k or 'iva' in k or 'presupuesto' in k for k in claves):
                return "Discrepancia: La directiva requiere aplicar un descuento y posteriormente un IVA. Falta el precio final."

        # 4. Solicitud de porcentaje / tanto por ciento vs proporción decimal
        if ('tanto por ciento' in prompt_lower or 'porcentaje' in prompt_lower or '%' in prompt_lower) and any(w in prompt_lower for w in ('probabilidad', 'bayes', 'tasa')):
            for k, v in resultado.items():
                if isinstance(v, (int, float)) and 0.0 < v <= 1.0:
                    return f"Discrepancia: La directiva solicitó el resultado en tanto por ciento (%), pero '{k}'={v} está en tanto por uno (<= 1.0). Debe incluir el porcentaje multiplicado por 100."

        # 5. Funciones analíticas dinámicas vs herramientas fijas en integración
        m_func = re.search(r'f\(x\)\s*=\s*([^entre]+?)\s+entre', prompt, re.IGNORECASE)
        if m_func:
            func_pedida = m_func.group(1).strip().replace(" ", "").lower()
            for k in ('funcion', 'function'):
                if k in resultado and isinstance(resultado[k], str):
                    func_ejecutada = resultado[k].replace(" ", "").lower()
                    if func_pedida not in func_ejecutada and func_ejecutada not in func_pedida:
                        return f"Discrepancia: La directiva solicitó f(x) = {func_pedida}, pero la herramienta ejecutó '{resultado[k]}'. Se requiere una función dinámica."

        # 6. Truncamiento excesivo a cero en integrales de amplitud positiva
        if 'integral' in prompt_lower or 'simpson' in prompt_lower:
            for k, v in resultado.items():
                if isinstance(v, (int, float)) and v == 0.0:
                    if 'sin(' in prompt_lower or 'exp(' in prompt_lower:
                        return f"Discrepancia: El valor devuelto '{k}' es 0.0, lo que indica pérdida de precisión o truncamiento prematuro. Utiliza más decimales o notación científica."

        # 7. Operaciones compuestas de suma y potencia
        if 'y el resultado de elevarlo' in prompt_lower or 'al cuadrado' in prompt_lower:
            claves = [k.lower() for k in resultado.keys()]
            if not any(w in k for w in ('potencia', 'cuadrado', 'elevado') for k in claves):
                return "Discrepancia: La directiva solicitó calcular la suma y además el resultado de elevarlo a la potencia 2. Falta el cálculo de la potencia."

        # 8. Parámetros angulares pisados
        m_ang = re.search(r'(?:angulo|ángulo|de)\s+(\d+(?:[.,]\d+)?)\s*(?:grados|deg|rad|sexagesimal)', prompt_lower)
        if m_ang:
            val_esperado = float(m_ang.group(1).replace(',', '.'))
            for k in ('angulo', 'angle', 'input'):
                if k in resultado and isinstance(resultado[k], (int, float)):
                    if abs(resultado[k] - val_esperado) > 0.01:
                        return f"Discrepancia: El parámetro '{k}' calculado ({resultado[k]}) no coincide con el especificado ({val_esperado})."

        return ""

    def _safe_release_lock(self) -> None:
        """Libera _processing_lock de forma segura evitando excepciones si ya está libre."""
        if self._processing_lock.locked():
            try:
                self._processing_lock.release()
            except RuntimeError:
                pass

    def _on_llm_token(self, kind: str, token: str) -> None:
        with self._lock:
            self._llm_streaming = True
            self._llm_stream_kind = kind
            if kind == 'reasoning':
                self._llm_stream_reasoning += token
                if len(self._llm_stream_reasoning) > 16000:
                    self._llm_stream_reasoning = self._llm_stream_reasoning[-16000:]
            else:
                self._llm_stream_content += token
                if len(self._llm_stream_content) > 16000:
                    self._llm_stream_content = self._llm_stream_content[-16000:]

    def _reset_llm_stream(self) -> None:
        with self._lock:
            self._llm_streaming = True
            self._llm_stream_kind = 'iniciando'
            self._llm_stream_reasoning = ''
            self._llm_stream_content = ''

    def _finalizar_llm_stream(self) -> None:
        with self._lock:
            self._llm_streaming = False
            self._llm_stream_kind = 'completado'

    def esta_ocupado(self) -> bool:
        return self._processing_lock.locked() or self.estado != EstadoBiologico.REPOSO

    def registrar_evento(self, emisor: str, mensaje: str, estado: EstadoBiologico) -> None:
        evento = {
            "timestamp": dt.datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "emisor": emisor,
            "mensaje": mensaje,
            "estado": estado.value,
        }
        with self._lock:
            self.historial_eventos.append(evento)
            if len(self.historial_eventos) > 300:
                self.historial_eventos.pop(0)

    def _cargar_organos_existentes(self) -> None:
        base = self.root / "body" / "organos"
        if not base.exists():
            return

        for org_d in sorted(base.iterdir()):
            if not org_d.is_dir():
                continue

            meta_f = org_d / "meta.json"
            meta = json.loads(meta_f.read_text(encoding="utf-8")) if meta_f.exists() else {}
            org_id = meta.get("id", org_d.name)
            nombre = meta.get("nombre", org_d.name.replace("_", " ").title())
            sistema = meta.get("sistema", "Sistema Fisiológico")

            org = Organo(id=org_id, nombre=nombre, sistema=sistema)
            self.organos[org_id] = org

            tej_base = org_d / "tejidos"
            if tej_base.exists():
                for tej_d in tej_base.iterdir():
                    if not tej_d.is_dir():
                        continue
                    tej_meta = json.loads((tej_d / "meta.json").read_text(encoding="utf-8")) if (tej_d / "meta.json").exists() else {}
                    tej_id = tej_meta.get("id", tej_d.name)
                    tej_nombre = tej_meta.get("nombre", tej_d.name.replace("_", " ").title())
                    tej_func = tej_meta.get("funcion", "Función Tisular")

                    tej = Tejido(id=tej_id, nombre=tej_nombre, funcion=tej_func)
                    org.agregar_tejido(tej)

                    cel_base = tej_d / "celulas"
                    if cel_base.exists():
                        for cel_d in cel_base.iterdir():
                            if not cel_d.is_dir():
                                continue
                            c_meta = json.loads((cel_d / "meta.json").read_text(encoding="utf-8")) if (cel_d / "meta.json").exists() else {}
                            c = Celula(
                                id=c_meta.get("id", cel_d.name),
                                nombre=c_meta.get("nombre", cel_d.name),
                                especialidad=c_meta.get("especialidad", ""),
                                herramientas=c_meta.get("herramientas", []),
                                ruta_dir=str(cel_d.relative_to(self.root)),
                            )
                            tej.agregar_celula(c)

    def _deliberar_organo(self, prompt: str) -> dict:
        self.registrar_evento("Organismo Digital", "🧠 Deliberando en la GPU qué Órgano debe gestionar la directiva...", EstadoBiologico.ACTIVIDAD)
        catalogo = [{"id": o.id, "nombre": o.nombre, "sistema": o.sistema} for o in self.organos.values()]

        system_prompt = (
            "Eres el Núcleo Coordinador del Organismo Digital.\n"
            "Tu misión es analizar la directiva del usuario y decidir qué ÓRGANO debe gestionarla.\n\n"
            f"CATÁLOGO DE ÓRGANOS EXISTENTES:\n{json.dumps(catalogo, ensure_ascii=False, indent=2)}\n\n"
            "PRINCIPIOS DE JERARQUÍA MACROSCÓPICA (OBLIGATORIOS):\n"
            "1. UN ÓRGANO ES UN GRAN SISTEMA DE CONOCIMIENTO (Macro-Dominio): Debe ser lo bastante amplio para albergar múltiples familias de tejidos.\n"
            "   - Ejemplos válidos: 'Órgano de Ciencias Matemáticas y Cálculo', 'Órgano de Nefrología y Medicina Interna', 'Órgano de Finanzas y Mercados Cuantitativos'.\n"
            "   - PROHIBIDO usar nombres estrechos para un solo cálculo ni términos de software como 'Módulo', 'Script', 'Función' o 'Servicio'.\n"
            "   - Nomenclatura obligatoria: 'Órgano de <Macro-Dominio>'.\n"
            "2. REUTILIZAR ÓRGANO ('existente'): Si alguno de tus órganos cubre este gran dominio temático, SELECCIÓNALO.\n"
            "3. NUEVO ÓRGANO ('nuevo'): SOLO si es un dominio completamente ajeno a los que ya existen o el cuerpo está vacío.\n\n"
            "Responde ÚNICAMENTE en JSON: {\"decision\": \"existente\" o \"nuevo\", \"organo_id\": \"org_<dominio>\", \"organo_nombre\": \"Órgano de <Macro-Dominio>\", \"organo_sistema\": \"...\"}"
        )

        content, _, _ = consultar_gpu_4090(system_prompt, f"Directiva: {prompt}", on_token=self._on_llm_token)
        data = reparar_json_raw(content)

        org_id = data.get("organo_id", "ORG_001")
        raw_on = str(data.get("organo_nombre") or "").strip()
        raw_on = re.sub(r'^(Módulo|Modulo|Sistema|Module)\s+(de\s+)?', 'Órgano de ', raw_on, flags=re.I)
        if not raw_on.lower().startswith("órgano de "):
            raw_on = f"Órgano de {raw_on}"
        org_nombre = raw_on
        org_sis = data.get("organo_sistema", "Sistema Fisiológico")

        for o in self.organos.values():
            if o.id == org_id or o.nombre.strip().lower() == org_nombre.strip().lower():
                self.registrar_evento("Organismo Digital", f"➜ Órgano existente: '{o.nombre}'.", EstadoBiologico.ACTIVIDAD)
                return {"decision": "existente", "organo": o}

        nuevo_org = Organo(id=org_id, nombre=org_nombre, sistema=org_sis)
        self.organos[org_id] = nuevo_org
        org_dir = self.root / "body" / "organos" / org_id
        org_dir.mkdir(parents=True, exist_ok=True)
        (org_dir / "meta.json").write_text(json.dumps({"id": org_id, "nombre": org_nombre, "sistema": org_sis}, indent=2, ensure_ascii=False), encoding="utf-8")

        self.registrar_evento("Organismo Digital", f"➜ Nuevo Órgano creado: '{org_nombre}'.", EstadoBiologico.APRENDIENDO)
        return {"decision": "nuevo", "organo": nuevo_org}

    def _deliberar_tejido(self, organo: Organo, prompt: str) -> dict:
        self.registrar_evento(organo.nombre, "🔬 Deliberando en la GPU qué Tejido especializado debe actuar...", EstadoBiologico.ACTIVIDAD)
        catalogo = [{"id": t.id, "nombre": t.nombre, "funcion": t.funcion} for t in organo.tejidos.values()]

        system_prompt = (
            f"Eres el Órgano '{organo.nombre}' ({organo.sistema}).\n"
            "Tu misión es decidir qué TEJIDO especializado debe gestionar la directiva.\n\n"
            f"TUS TEJIDOS EXISTENTES:\n{json.dumps(catalogo, ensure_ascii=False, indent=2)}\n\n"
            "PRINCIPIOS DE JERARQUÍA Y ASIGNACIÓN TISULAR (OBLIGATORIOS):\n"
            "1. UN TEJIDO ES UNA FAMILIA FUNCIONAL / SUBDOMINIO: Representa una rama temática especializada DENTRO de tu gran órgano.\n"
            "   - PROHIBIDO LLAMARSE IGUAL QUE EL ÓRGANO: El tejido debe ser una subespecialización temática más fina.\n"
            "   - Ejemplos: Si el órgano es 'Órgano de Ciencias Matemáticas', sus tejidos son: 'Tejido de Aritmética Fundamental', 'Tejido de Álgebra y Ecuaciones', 'Tejido de Geometría y Medidas', 'Tejido de Estadística y Azar'.\n"
            "   - Nomenclatura obligatoria: 'Tejido de <Familia Funcional>'.\n"
            "2. REUTILIZAR TEJIDO ('existente'): Si la directiva pertenece a la misma familia conceptual de un tejido existente, SELECCIÓNALO para que aloje a una nueva célula hermana y el tejido crezca pluricelularmente.\n"
            "3. NUEVO TEJIDO ('nuevo'): SOLO si la directiva pertenece a una familia o subdominio distinto que aún no tienes.\n"
            "4. PROHIBIDO USAR 'N/A' O 'GENERAL'.\n\n"
            "Responde ÚNICAMENTE en JSON: {\"decision\": \"existente\" o \"nuevo\", \"tejido_id\": \"tej_<familia>\", \"tejido_nombre\": \"Tejido de <Familia>\", \"tejido_funcion\": \"...\"}"
        )

        content, _, _ = consultar_gpu_4090(system_prompt, f"Directiva: {prompt}", on_token=self._on_llm_token)
        data = reparar_json_raw(content)

        tej_id = str(data.get("tejido_id") or f"TEJ_{len(organo.tejidos)+1:03d}").strip()
        raw_tn = str(data.get("tejido_nombre") or "").strip()
        tej_nombre = raw_tn if raw_tn and raw_tn.upper() not in ("N/A", "NONE", "NULL", "UNDEFINED") else f"Tejido de {organo.nombre}"
        tej_func = str(data.get("tejido_funcion") or prompt[:60]).strip()

        for t in organo.tejidos.values():
            if t.id == tej_id or t.nombre.strip().lower() == tej_nombre.strip().lower():
                self.registrar_evento(organo.nombre, f"➜ Tejido existente: '{t.nombre}'.", EstadoBiologico.ACTIVIDAD)
                return {"decision": "existente", "tejido": t}

        nuevo_tej = Tejido(id=tej_id, nombre=tej_nombre, funcion=tej_func)
        organo.agregar_tejido(nuevo_tej)
        tej_dir = self.root / "body" / "organos" / organo.id / "tejidos" / tej_id
        tej_dir.mkdir(parents=True, exist_ok=True)
        (tej_dir / "meta.json").write_text(json.dumps({"id": tej_id, "nombre": tej_nombre, "funcion": tej_func}, indent=2, ensure_ascii=False), encoding="utf-8")

        self.registrar_evento(organo.nombre, f"➜ Nuevo Tejido creado: '{tej_nombre}'.", EstadoBiologico.APRENDIENDO)
        return {"decision": "nuevo", "tejido": nuevo_tej}

    def _deliberar_celula(self, organo: Organo, tejido: Tejido, prompt: str) -> dict:
        self.registrar_evento(tejido.nombre, "🧬 Evaluando en GPU competencia celular determinista...", EstadoBiologico.ACTIVIDAD)
        catalogo = [
            {"id": c.id, "nombre": c.nombre, "especialidad": c.especialidad, "herramientas": c.herramientas}
            for c in tejido.celulas.values()
        ]

        system_prompt = (
            f"Eres el Tejido '{tejido.nombre}' en '{organo.nombre}'.\n"
            "Evalúa si alguna de tus CÉLULAS ya programadas puede resolver ÍNTEGRAMENTE la directiva con su herramienta determinista.\n\n"
            f"CÉLULAS DISPONIBLES EN ESTE TEJIDO:\n{json.dumps(catalogo, ensure_ascii=False, indent=2)}\n\n"
            "CRITERIOS DE DISCRIMINACIÓN (UNIVERSALES):\n"
            "1. REUTILIZAR ('existente'): SOLO si una célula existente cubre exactamente toda la operación.\n"
            "2. COMPOSICIÓN SECUENCIAL: Si la directiva encadena varias etapas ('primero... después', 'luego', 'con el resultado'), "
            "   ninguna célula atómica simple es competente. Responde obligatoriamente 'decision': 'morfogenesis' para crear una célula compuesta.\n"
            "3. PRECISIÓN Y DECIMALES: Si la directiva solicita decimales específicos (ej. 8 decimales), inclúyelos en 'args' (--decimales o --precision).\n"
            "4. MORFOGÉNESIS ('morfogenesis'): Si la directiva pide una tarea distinta o fórmula no implementada, responde 'morfogenesis'.\n\n"
            "FORMATOS DE RESPUESTA (ÚNICAMENTE JSON):\n"
            "- Célula competente existente: {\"decision\": \"existente\", \"celula_id\": \"<id_exacto>\", \"tool_file\": \"<archivo>\", \"args\": {\"param\": \"valor\"}}\n"
            "- Se requiere nueva célula: {\"decision\": \"morfogenesis\", \"motivo\": \"Razón de incompetencia actual\"}"
        )

        content, _, _ = consultar_gpu_4090(system_prompt, f"Directiva: {prompt}", on_token=self._on_llm_token)
        data = reparar_json_raw(content)

        decision = data.get("decision", "morfogenesis")
        cel_id = data.get("celula_id")

        # Guardrail determinista: Directivas compuestas multietapa
        es_compuesta = bool(re.search(
            r'(\bprimero\b.*(\bdespu[eé]s\b|\bluego\b|\ba continuaci[oó]n\b|\busando\b|\bcon el resultado\b)|'
            r'\by el resultado de\b|'
            r'\bcon (ese|este|el) resultado\b|'
            r'\busando (ese|este|las|los) (resultado|ra[ií]ces|t[eé]rmino)\b|'
            r'\by (despu[eé]s|luego|posteriormente)\b)',
            prompt, re.IGNORECASE | re.DOTALL
        ))
        if es_compuesta and decision == "existente" and cel_id in tejido.celulas:
            c_cand = tejido.celulas[cel_id]
            if not any(k in c_cand.nombre.lower() or k in c_cand.especialidad.lower() for k in ("compuest", "pipeline", "integrad", "secuencial")):
                self.registrar_evento(tejido.nombre, f"⚡ Directiva compuesta detectada: '{c_cand.nombre}' es atómica. Forzando morfogénesis...", EstadoBiologico.APRENDIENDO)
                decision = "morfogenesis"

        if decision == "existente" and cel_id in tejido.celulas:
            celula = tejido.celulas[cel_id]
            tool_file = data.get("tool_file") or (celula.herramientas[0] if celula.herramientas else "tool.py")
            args = sanitizar_argumentos_cli(data.get("args", {}))
            self.registrar_evento(tejido.nombre, f"➜ Célula existente competente: '{celula.nombre}'.", EstadoBiologico.ACTIVIDAD)
            return {"decision": "existente", "celula": celula, "tool_file": tool_file, "args": args}

        self.registrar_evento(tejido.nombre, "➜ Morfogénesis requerida. Invocando Célula Madre...", EstadoBiologico.APRENDIENDO)
        return {
            "decision": "morfogenesis",
            "motivo": data.get("motivo", "Célula no disponible para esta directiva")
        }

    def procesar_prompt(self, prompt: str) -> str:
        if not self._processing_lock.acquire(blocking=False):
            return "⚠️ El Organismo Digital ya está ocupado procesando otra directiva en este instante."

        try:
            self.ultimo_prompt = prompt
            self._reset_llm_stream()
            self.estado = EstadoBiologico.ACTIVIDAD
            self.registrar_evento("Organismo Digital", f"Directiva recibida: '{prompt[:50]}...'", EstadoBiologico.ACTIVIDAD)

            res_org = self._deliberar_organo(prompt)
            organo: Organo = res_org["organo"]
            organo.estado = EstadoBiologico.ACTIVIDAD

            res_tej = self._deliberar_tejido(organo, prompt)
            tejido: Tejido = res_tej["tejido"]
            tejido.estado = EstadoBiologico.ACTIVIDAD

            res_cel = self._deliberar_celula(organo, tejido, prompt)

            if res_cel["decision"] == "existente":
                celula: Celula = res_cel["celula"]
                tool_file: str = res_cel["tool_file"]
                args: list = sanitizar_argumentos_cli(res_cel["args"])
                self.registrar_evento("Organismo Digital", f"⚡ Reutilización celular: {celula.nombre}.", EstadoBiologico.ACTIVIDAD)
            else:
                self.celula_madre.estado = EstadoBiologico.APRENDIENDO
                self.registrar_evento("Célula Madre", f"Iniciando diferenciación terminal para resolver directiva...", EstadoBiologico.APRENDIENDO)

                temp_slug = re.sub(r'[^a-zA-Z0-9]+', '_', prompt[:25].lower()).strip('_') or "especialista"
                candidate_id = f"cel_{temp_slug}"
                counter = 1
                while candidate_id in tejido.celulas:
                    counter += 1
                    candidate_id = f"cel_{temp_slug}_{counter}"

                info = {
                    "organo_id": organo.id,
                    "organo_nombre": organo.nombre,
                    "organo_sistema": organo.sistema,
                    "tejido_id": tejido.id,
                    "tejido_nombre": tejido.nombre,
                    "tejido_funcion": tejido.funcion,
                    "celula_id": candidate_id,
                    "celula_nombre": "Nueva Célula Especializada",
                    "celula_especialidad": prompt[:60],
                }

                celula, tool_file, raw_args = self.celula_madre.sintetizar_herramienta_y_diferenciar(
                    info, prompt, executor=self.executor, log_cb=self.registrar_evento, on_token=self._on_llm_token
                )
                args = sanitizar_argumentos_cli(raw_args)
                tejido.agregar_celula(celula)
                self.celula_madre.estado = EstadoBiologico.REPOSO
                self.registrar_evento("Célula Madre", f"Morfogénesis completada: '{celula.nombre}' integrada en {tejido.nombre}.", EstadoBiologico.REPOSO)

            celula.estado = EstadoBiologico.ACTIVIDAD
            self.registrar_evento(celula.nombre, f"Ejecutando en Sandbox Docker: {tool_file} {args}", EstadoBiologico.ACTIVIDAD)

            rel_tool = f"organos/{organo.id}/tejidos/{tejido.id}/celulas/{celula.id}/tools/{tool_file}"
            rel_test = f"organos/{organo.id}/tejidos/{tejido.id}/celulas/{celula.id}/tests/test_{tool_file}"

            res_exec = self.executor.execute(rel_tool, args)
            salida_raw = (res_exec.get("stdout") or "").strip()
            hubo_error = not res_exec.get("success", False)

            if not hubo_error and not salida_raw:
                hubo_error = True
                salida_raw = "Error: La herramienta finalizó sin imprimir ningún resultado JSON en stdout."

            if not hubo_error and salida_raw:
                try:
                    j_check = json.loads(salida_raw)
                    if "error" in j_check:
                        hubo_error = True
                        salida_raw = str(j_check["error"])
                    else:
                        fallo_conformidad = self._auditar_conformidad(prompt, j_check)
                        if fallo_conformidad:
                            hubo_error = True
                            salida_raw = fallo_conformidad
                except Exception:
                    pass

            if hubo_error:
                celula.estado = EstadoBiologico.APRENDIENDO
                err_msg = res_exec.get("stderr") or salida_raw or "Fallo en ejecución determinista"
                self.registrar_evento(celula.nombre, f"⚠️ Error o Discrepancia: {err_msg[:60]}...", EstadoBiologico.APRENDIENDO)

                ok_heal, res_heal = ejecutar_bucle_autoperfeccionamiento(
                    celula_nombre=celula.nombre,
                    tool_rel_path=rel_tool,
                    test_rel_path=rel_test,
                    executor=self.executor,
                    args=args,
                    error_origen=err_msg,
                    log_cb=self.registrar_evento,
                )
                if ok_heal:
                    salida_raw = res_heal
                else:
                    celula.estado = EstadoBiologico.FALLO
                    raise RuntimeError(res_heal)

            resultado_texto = (
                f"### 🧬 INFORME DETERMINISTA DEL ORGANISMO DIGITAL\n\n"
                f"**Aislamiento:** `{res_exec.get('sandbox', 'docker')}`\n"
                f"**Cascada Cognitiva:** `{organo.nombre}` ➜ `{tejido.nombre}` ➜ `{celula.nombre}`\n\n"
                f"**Resultado de la Ejecución Determinista:**\n"
                f"```json\n{salida_raw}\n```"
            )

            self.ultimo_resultado = resultado_texto
            self.registrar_evento(celula.nombre, "Cálculo determinista completado con éxito.", EstadoBiologico.ACTIVIDAD)
            self.registrar_evento("Organismo Digital", "Respuesta final entregada al usuario.", EstadoBiologico.ACTIVIDAD)
            return resultado_texto

        except Exception as e:
            self.estado = EstadoBiologico.FALLO
            self.registrar_evento("Organismo Digital", f"Fallo en cascada cognitiva: {e}", EstadoBiologico.FALLO)
            err = f"❌ Error en cascada: {type(e).__name__} - {e}"
            self.ultimo_resultado = err
            return err

        finally:
            self._poner_en_reposo()
            self._finalizar_llm_stream()
            self._safe_release_lock()

    def remodelar_anatomia(self) -> str:
        if not self._processing_lock.acquire(blocking=False):
            return "El Organismo Digital ya está ocupado procesando otra tarea."

        try:
            self.estado = EstadoBiologico.APRENDIENDO
            self.celula_madre.estado = EstadoBiologico.APRENDIENDO
            self.registrar_evento("Célula Madre", "Iniciando ciclo de Homeostasis y Remodelado Tisular Consciente...", EstadoBiologico.APRENDIENDO)

            censo_celulas = []
            for org in self.organos.values():
                for tej in org.tejidos.values():
                    for cel in tej.celulas.values():
                        censo_celulas.append({
                            "organo_id": org.id,
                            "organo_nombre": org.nombre,
                            "tejido_id": tej.id,
                            "tejido_nombre": tej.nombre,
                            "celula_id": cel.id,
                            "celula_nombre": cel.nombre,
                            "especialidad": cel.especialidad,
                            "herramientas": cel.herramientas
                        })

            if len(censo_celulas) < 2:
                msg = "El organismo cuenta con 1 o menos células. Se requieren al menos 2 células para ejecutar una poda tisular."
                self.registrar_evento("Célula Madre", msg, EstadoBiologico.REPOSO)
                self.ultimo_resultado = msg
                return msg

            self.registrar_evento("Célula Madre", f"Auditando {len(censo_celulas)} células distribuidas en {len(self.organos)} órgano(s)...", EstadoBiologico.APRENDIENDO)
            # Recopilar antígenos (fallos adversariales recientes para inmunización homeostática)
            antigenos = []
            dir_auditoria = self.root / "logs" / "auditoria"
            if dir_auditoria.exists():
                jsonl_files = sorted(dir_auditoria.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
                if jsonl_files:
                    try:
                        with jsonl_files[0].open("r", encoding="utf-8") as jf:
                            for line in jf:
                                if line.strip():
                                    r = json.loads(line)
                                    if not r.get("ok", False):
                                        antigenos.append({
                                            "tema": r.get("tema"),
                                            "prompt": r.get("prompt"),
                                            "faltantes": r.get("faltantes")
                                        })
                    except Exception:
                        pass

            backups_dir = self.root / "experiment" / "backups"
            backups_dir.mkdir(parents=True, exist_ok=True)
            stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backups_dir / f"poda_pre_remodelado_{stamp}.tar.gz"
            with tarfile.open(backup_path, "w:gz") as tar:
                org_dir = self.root / "body" / "organos"
                if org_dir.exists():
                    tar.add(org_dir, arcname="organos_pre_poda")
            self.registrar_evento("Célula Madre", f"Respaldo previo creado: {backup_path.name}", EstadoBiologico.APRENDIENDO)

            system_prompt = (
                "Eres la Célula Madre en función de Arquitecto y Homeóstato Biológico.\n"
                "Tu misión es auditar la anatomía del organismo, detectar redundancias y fragmentaciones, "
                "y proponer una anatomía LIMPIA, COMPACTA y GENERALIZADA.\n\n"
                "PRINCIPIO DE NO REGRESIÓN FUNCIONAL (ESTRICTAMENTE OBLIGATORIO):\n"
                "1. NUNCA elimines una capacidad funcional que las células originales ya poseían.\n"
                "2. Cada herramienta unificada debe implementar un despachador completo (--op <operacion>) que preserve "
                "   todas las opciones anteriores sin mutilar la lógica.\n"
                "3. El test unitario ('test_code') debe incluir aserciones para cada una de las capacidades unificadas.\n\n"
                "Responde ÚNICAMENTE en JSON:\n"
                "{\n"
                '  "resumen_remodelado": "Explicación breve de la consolidación efectuada",\n'
                '  "organos_consolidados": [\n'
                "    {\n"
                '      "id": "...",\n'
                '      "nombre": "...",\n'
                '      "sistema": "...",\n'
                '      "tejidos": [\n'
                "        {\n"
                '          "id": "...",\n'
                '          "nombre": "...",\n'
                '          "funcion": "...",\n'
                '          "celulas": [\n'
                "            {\n"
                '              "id": "...",\n'
                '              "nombre": "...",\n'
                '              "especialidad": "...",\n'
                '              "tool_file": "nombre.py",\n'
                '              "tool_code": "código completo python con main y parseo",\n'
                '              "test_file": "test_nombre.py",\n'
                '              "test_code": "código test unittest"\n'
                "            }\n"
                "          ]\n"
                "        }\n"
                "      ]\n"
                "    }\n"
                "  ]\n"
                "}"
            )

            antigenos_texto = ""
            if antigenos:
                antigenos_texto = (
                    "\n\n============================================================\n"
                    "MEMORIA INMUNOLÓGICA - CONTRAEJEMPLOS FALLIDOS EN AUDITORÍA:\n"
                    "============================================================\n"
                    "Las siguientes directivas revelaron fallos por falta de parámetros dinámicos (--func),\n"
                    "redondeo prematuro o ausencia de banderas CLI. Las herramientas unificadas DEBEN resolverlas:\n"
                    + json.dumps(antigenos[:8], ensure_ascii=False, indent=2) + "\n"
                )
            prompt_usuario = (
                f"CENSO CELULAR ACTUAL:\n{json.dumps(censo_celulas, ensure_ascii=False, indent=2)}"
                f"{antigenos_texto}\n\n"
                "Realiza la consolidación tisular y devuelve el JSON optimizado garantizando herramientas universales y paramétricas."
            )

            self.registrar_evento("Célula Madre", "Deliberando en la RTX 4090 el mapa de remodelación tisular...", EstadoBiologico.APRENDIENDO)
            content, _, _ = consultar_gpu_4090(system_prompt, prompt_usuario, on_token=self._on_llm_token)
            data = reparar_json_raw(content)

            organos_nuevos = data.get("organos_consolidados", [])
            if not organos_nuevos:
                raise ValueError("La GPU no generó un plan válido de órganos consolidados.")

            resumen = data.get("resumen_remodelado", "Remodelación completada.")

            base_org = self.root / "body" / "organos"
            shutil.rmtree(base_org, ignore_errors=True)
            base_org.mkdir(parents=True, exist_ok=True)

            self.organos.clear()
            celulas_total = 0

            for o_data in organos_nuevos:
                o_id = str(o_data.get("id") or "ORG_001").strip()
                o_nom = str(o_data.get("nombre") or "Órgano Consolidado").strip()
                o_sis = str(o_data.get("sistema") or "Sistema Biológico").strip()

                org = Organo(id=o_id, nombre=o_nom, sistema=o_sis)
                org_dir = base_org / o_id
                org_dir.mkdir(parents=True, exist_ok=True)
                (org_dir / "meta.json").write_text(json.dumps({"id": o_id, "nombre": o_nom, "sistema": o_sis}, indent=2, ensure_ascii=False), encoding="utf-8")

                for t_data in o_data.get("tejidos", []):
                    t_id = str(t_data.get("id") or "TEJ_001").strip()
                    t_nom = str(t_data.get("nombre") or "Tejido Unificado").strip()
                    t_func = str(t_data.get("funcion") or "Función Tisular").strip()

                    tej = Tejido(id=t_id, nombre=t_nom, funcion=t_func)
                    tej_dir = org_dir / "tejidos" / t_id
                    tej_dir.mkdir(parents=True, exist_ok=True)
                    (tej_dir / "meta.json").write_text(json.dumps({"id": t_id, "nombre": t_nom, "funcion": t_func}, indent=2, ensure_ascii=False), encoding="utf-8")

                    for c_data in t_data.get("celulas", []):
                        c_id = str(c_data.get("id") or f"CEL_{celulas_total+1:03d}").strip()
                        c_nom = str(c_data.get("nombre") or "Célula Consolidada").strip()
                        c_esp = str(c_data.get("especialidad") or "").strip()
                        tool_file = str(c_data.get("tool_file") or "tool.py").strip()
                        if not tool_file.endswith(".py"): tool_file += ".py"
                        test_file = f"test_{tool_file}"
                        tool_code = c_data.get("tool_code", "")
                        test_code = c_data.get("test_code", "")

                        cel_dir = tej_dir / "celulas" / c_id
                        tools_dir = cel_dir / "tools"
                        tests_dir = cel_dir / "tests"
                        tools_dir.mkdir(parents=True, exist_ok=True)
                        tests_dir.mkdir(parents=True, exist_ok=True)

                        inyector = (
                            "# === [ORGANISMO_DIGITAL_PATH_INJECTOR] ===\n"
                            "import sys, os\n"
                            "from pathlib import Path\n"
                            "_cur = Path(__file__).resolve()\n"
                            "_cel_dir = _cur.parent.parent\n"
                            "_tools_dir = str(_cel_dir / 'tools')\n"
                            "_cel_str = str(_cel_dir)\n"
                            "for _p in (_tools_dir, _cel_str):\n"
                            "    if _p not in sys.path:\n"
                            "        sys.path.insert(0, _p)\n"
                            "# =========================================\n\n"
                        )
                        if "ORGANISMO_DIGITAL_PATH_INJECTOR" not in test_code:
                            test_code = inyector + test_code
                        if "unittest.main" not in test_code:
                            test_code += "\n\nif __name__ == '__main__':\n    import unittest\n    unittest.main()\n"

                        (tools_dir / tool_file).write_text(tool_code, encoding="utf-8")
                        (tests_dir / test_file).write_text(test_code, encoding="utf-8")
                        asegurar_omnipresencia_celular(cel_dir, tool_file)

                        meta_cel = {
                            "id": c_id,
                            "nombre": c_nom,
                            "especialidad": c_esp,
                            "herramientas": [tool_file],
                            "consolidada": True,
                            "creado": dt.datetime.now().isoformat(),
                        }
                        (cel_dir / "meta.json").write_text(json.dumps(meta_cel, indent=2, ensure_ascii=False), encoding="utf-8")

                        rel_tool = f"organos/{o_id}/tejidos/{t_id}/celulas/{c_id}/tools/{tool_file}"
                        rel_test = f"organos/{o_id}/tejidos/{t_id}/celulas/{c_id}/tests/{test_file}"
                        res_test = self.executor.execute(rel_test, [])

                        if not res_test.get("success", False):
                            self.registrar_evento("Célula Madre", f"🔧 Autoperfeccionando célula consolidada '{c_nom}'...", EstadoBiologico.APRENDIENDO)
                            ejecutar_bucle_autoperfeccionamiento(
                                celula_nombre=c_nom,
                                tool_rel_path=rel_tool,
                                test_rel_path=rel_test,
                                executor=self.executor,
                                args=[],
                                error_origen=res_test.get("stderr") or "Fallo en validación de test consolidado",
                                log_cb=self.registrar_evento,
                            )

                        cel = Celula(
                            id=c_id,
                            nombre=c_nom,
                            especialidad=c_esp,
                            herramientas=[tool_file],
                            descripcion=c_esp,
                            ruta_dir=str(cel_dir.relative_to(self.root))
                        )
                        tej.agregar_celula(cel)
                        celulas_total += 1
                        self.registrar_evento("Célula Madre", f"Célula consolidada: '{c_nom}'", EstadoBiologico.ACTIVIDAD)

                    org.agregar_tejido(tej)

                self.organos[o_id] = org

            msg_final = (
                f"### INFORME DE HOMEOSTASIS Y REMODELADO TISULAR\n\n"
                f"**Resumen:** {resumen}\n\n"
                f"**Métricas de la Poda:**\n"
                f"- Células iniciales: `{len(censo_celulas)}`\n"
                f"- Células consolidadas finales: `{celulas_total}`\n"
                f"- Órganos optimizados: `{len(self.organos)}`\n"
                f"- Respaldo previo: `{backup_path.name}`\n\n"
                f"El catálogo anatómico ha sido simplificado preservando todas las capacidades funcionales."
            )

            self.ultimo_resultado = msg_final
            self.registrar_evento("Organismo Digital", "Homeostasis completada con éxito.", EstadoBiologico.ACTIVIDAD)
            return msg_final

        except Exception as e:
            self.estado = EstadoBiologico.FALLO
            err_msg = f"Error durante el remodelado tisular: {type(e).__name__} - {e}"
            self.registrar_evento("Célula Madre", err_msg, EstadoBiologico.FALLO)
            self.ultimo_resultado = err_msg
            return err_msg

        finally:
            self._poner_en_reposo()
            self._safe_release_lock()

    def reiniciar_tabula_rasa(self) -> str:
        if not self._processing_lock.acquire(blocking=False):
            return "El organismo está ocupado procesando otra directiva."
        try:
            self.estado = EstadoBiologico.APRENDIENDO
            self.registrar_evento("Organismo Digital", "🌱 Iniciando secuencia de Tabula Rasa (Reseteo a Célula Madre)...", EstadoBiologico.APRENDIENDO)

            backups_dir = self.root / "experiment" / "backups"
            backups_dir.mkdir(parents=True, exist_ok=True)
            stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backups_dir / f"organismo_pre_tabula_rasa_{stamp}.tar.gz"
            with tarfile.open(backup_path, "w:gz") as tar:
                body_dir = self.root / "body"
                if body_dir.exists():
                    tar.add(body_dir, arcname="body")

            org_dir = self.root / "body" / "organos"
            if org_dir.exists():
                shutil.rmtree(org_dir)
            org_dir.mkdir(parents=True, exist_ok=True)
            self.organos.clear()

            mem_dir = self.root / "body" / "memory"
            mem_dir.mkdir(parents=True, exist_ok=True)
            state_initial = {
                "identidad": "celula_madre_totipotente",
                "fase": "tabula_rasa",
                "estado": "reposo",
                "organos_activos": [],
                "iteracion": 0,
                "ultima_modificacion": dt.datetime.now().isoformat(),
            }
            (mem_dir / "state.json").write_text(json.dumps(state_initial, indent=2, ensure_ascii=False), encoding="utf-8")
            (mem_dir / "knowledge.json").write_text(json.dumps({"entries": []}, indent=2), encoding="utf-8")
            for extra in ("interface.json", "informe_caso.txt", "caso_actual.txt"):
                p = mem_dir / extra
                if p.exists(): p.unlink()
            res_dir = mem_dir / "research"
            if res_dir.exists(): shutil.rmtree(res_dir)

            plan_dir = self.root / "body" / "planner"
            plan_dir.mkdir(parents=True, exist_ok=True)
            goals = {
                "objetivo_primordial": "Organismo Digital: Morfogénesis Autónoma y Computación Determinista",
                "estado": "tabula_rasa",
                "active_goals": [
                    {"id": "BIO_001", "desc": "Mantener Célula Madre Totipotente lista para recibir directivas", "status": "active"},
                    {"id": "BIO_002", "desc": "Inducir morfogénesis de órganos y tejidos bajo demanda usando la RTX 4090", "status": "standby"},
                    {"id": "BIO_003", "desc": "Validar herramientas con tests unitarios deterministas (IEEE 754)", "status": "standby"}
                ]
            }
            (plan_dir / "goals.json").write_text(json.dumps(goals, indent=2, ensure_ascii=False), encoding="utf-8")

            msg = f"🌱 Organismo reseteado a Tabula Rasa virgen. Respaldo creado en {backup_path.name}."
            self.ultimo_resultado = msg
            self.registrar_evento("Organismo Digital", msg, EstadoBiologico.REPOSO)
            return msg
        except Exception as e:
            self.estado = EstadoBiologico.FALLO
            err = f"Error en reset a Tabula Rasa: {e}"
            self.registrar_evento("Organismo Digital", err, EstadoBiologico.FALLO)
            self.ultimo_resultado = err
            return err
        finally:
            self._poner_en_reposo()
            self._safe_release_lock()

    def _poner_en_reposo(self) -> None:
        self.estado = EstadoBiologico.REPOSO
        self.celula_madre.estado = EstadoBiologico.REPOSO
        for org in self.organos.values():
            org.estado = EstadoBiologico.REPOSO
            for tej in org.tejidos.values():
                tej.estado = EstadoBiologico.REPOSO
                for cel in tej.celulas.values():
                    cel.estado = EstadoBiologico.REPOSO

    def obtener_estado_completo(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "gpu_online": is_remote_health_ok(),
                "sandbox_docker": self.executor.docker_available,
                "organismo_estado": self.estado.value,
                "celula_madre_estado": self.celula_madre.estado.value,
                "ultimo_resultado": self.ultimo_resultado,
                "ultimo_prompt": self.ultimo_prompt,
                "organos": [o.to_dict() for o in self.organos.values()],
                "eventos": self.historial_eventos[-60:],
                "llm_live": {
                    "streaming": self._llm_streaming,
                    "kind": self._llm_stream_kind,
                    "reasoning": self._llm_stream_reasoning,
                    "content": self._llm_stream_content,
                },
            }

    def obtener_diagnostico_completo(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "meta": {
                    "timestamp": dt.datetime.now().isoformat(),
                    "gpu_rtx_4090_online": is_remote_health_ok(),
                    "docker_sandbox_active": self.executor.docker_available,
                    "python_version": sys.version,
                    "platform": sys.platform,
                },
                "estado_organismo": self.estado.value,
                "ultimo_resultado": self.ultimo_resultado,
                "arbol_organos": [o.to_dict() for o in self.organos.values()],
                "telemetria": self.historial_eventos,
            }
