#!/usr/bin/env python3
"""
scripts/auditor_adversarial.py - Auditor Adversarial del Organismo Digital.

Ataca los temas que el organismo ya superó, buscando fragilidad en cuatro frentes:
  1. BORDE       - discriminantes/determinantes casi nulos, triángulos casi
                    degenerados, probabilidades extremas, derivadas casi nulas.
  2. ESCALA      - magnitudes muy grandes (1e6+) o muy pequeñas (1e-6).
  3. PRECISION   - exige 6-8 decimales en vez de 4, exponiendo redondeos prematuros.
  4. COMPOSICION - encadena dos habilidades ya dominadas por separado.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import random
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from functools import reduce
from pathlib import Path

API_BASE = "http://localhost:8888/api"

CATEGORIAS = [
    ("borde", "Casos Límite"),
    ("escala", "Estrés de Escala"),
    ("precision", "Alta Precisión"),
    ("composicion", "Problemas Compuestos"),
]
NOMBRE_CAT = dict(CATEGORIAS)


# =============================================================================
# REGISTRO DE RETOS ADVERSARIALES
# =============================================================================
@dataclass(frozen=True)
class Reto:
    categoria: str
    tema: str
    generar: object
    tol: float = 1e-3


CURRICULUM: list[Reto] = []


def reto(categoria: str, tema: str, tol: float = 1e-3):
    def deco(fn):
        CURRICULUM.append(Reto(categoria, tema, fn, tol))
        return fn
    return deco


def mcd(*n): return reduce(math.gcd, n)
def mcm(*n): return reduce(lambda a, b: a * b // math.gcd(a, b), n)


def expr(coefs, mons):
    s = ""
    for c, m in zip(coefs, mons):
        if c == 0:
            continue
        mag = abs(c)
        cuerpo = str(mag) if not m else (m if mag == 1 else f"{mag}*{m}")
        s += (("-" if c < 0 else "") if not s else (" - " if c < 0 else " + ")) + cuerpo
    return s or "0"


def pol(coefs, var="x"):
    n = len(coefs) - 1
    return expr(coefs, [("" if p == 0 else var if p == 1 else f"{var}^{p}") for p in range(n, -1, -1)])


def simpson(f, a, b, n):
    h = (b - a) / n
    s = f(a) + f(b) + sum((4 if i % 2 else 2) * f(a + i * h) for i in range(1, n))
    return s * h / 3


# =============================================================================
# 1. BORDE
# =============================================================================
@reto("borde", "Cuadratica con raiz doble (discriminante cero)")
def _borde_raiz_doble(r):
    a, raiz = r.choice([1, 2, 3]), r.randint(-8, 8) or 1
    b, c = -2 * a * raiz, a * raiz * raiz
    return (f"Resuelve la ecuacion cuadratica {pol([a, b, c])} = 0 y devuelve sus raices. "
            f"Redondea a 4 decimales.", [raiz])


@reto("borde", "Sistema lineal casi singular", tol=5e-2)
def _borde_casi_singular(r):
    x, y = r.randint(-5, 5) or 1, r.randint(-5, 5) or 1
    a = r.randint(2, 6)
    # BLINDAJE: forzar b != a para que det = 0.01*(a-b) != 0
    b = r.choice([v for v in range(2, 7) if v != a])
    eps = 0.01
    c, d = a + eps, b + eps
    return (f"Resuelve el sistema lineal {expr([a, b], ['x', 'y'])} = {a*x+b*y} y "
            f"{expr([round(c,2), round(d,2)], ['x', 'y'])} = {round(c*x+d*y,4)} devolviendo x e y exactos.",
            [x, y])


@reto("borde", "Triangulo casi degenerado", tol=5e-2)
def _borde_triangulo_degenerado(r):
    a, b = r.randint(10, 30), r.randint(10, 30)
    c = a + b - r.choice([1, 2])
    s = (a + b + c) / 2
    area = math.sqrt(max(0.0, s * (s - a) * (s - b) * (s - c)))
    return (f"Calcula el area de un triangulo con lados a={a}, b={b}, c={c} usando la formula de Heron "
            f"(el triangulo es casi degenerado; el area sera muy pequena pero positiva). "
            f"Redondea a 4 decimales.", [area])


@reto("borde", "Probabilidad casi extrema (Bayes)", tol=5e-3)
def _borde_bayes_extremo(r):
    prev = r.choice([0.001, 0.0005, 0.0001])
    sens, esp = 0.999, 0.999
    post = prev * sens / (prev * sens + (1 - prev) * (1 - esp))
    # Acepta tanto el valor porcentual (9.08%) como en tanto por uno (0.0908)
    return (f"Una prueba diagnostica tiene sensibilidad 99.9% y especificidad 99.9%. La prevalencia de la "
            f"enfermedad es {prev*100:g}%. Si el resultado es positivo, calcula la probabilidad de estar "
            f"realmente enfermo (Teorema de Bayes), en tanto por ciento con 3 decimales.",
            [post * 100, post])


@reto("borde", "Division con derivada casi nula en Newton-Raphson", tol=1e-2)
def _borde_derivada_casi_nula(r):
    c = r.randint(20, 60)
    x = 1.0
    for _ in range(200):
        fx, dfx = x**3 - x - c, 3*x*x - 1
        if abs(dfx) < 1e-9:
            x += 0.5
            continue
        x -= fx / dfx
    return (f"Usando el metodo de Newton-Raphson partiendo de x0=1.0, halla la raiz real de "
            f"f(x) = x^3 - x - {c}. Si la derivada en algun punto es casi nula, aparta ligeramente el "
            f"punto antes de continuar. Redondea a 4 decimales.", [x])


# =============================================================================
# 2. ESCALA
# =============================================================================
@reto("escala", "Suma y potencia con numeros muy grandes")
def _escala_grande(r):
    a, b = r.randint(10**6, 9*10**6), r.randint(10**6, 9*10**6)
    return (f"Calcula {a} + {b} y el resultado de elevarlo a la potencia 2 (notacion completa)",
            [a + b, (a + b) ** 2])


@reto("escala", "Integral con funcion de amplitud muy pequena", tol=5e-2)
def _escala_pequena(r):
    amp = r.choice([1e-5, 1e-6, 5e-6])
    f = lambda x: amp * math.sin(x)
    val = simpson(f, 0, math.pi, 200)
    return (f"Calcula la integral definida de f(x) = {amp}*sin(x) entre x=0 y x=pi usando Simpson 1/3 "
            f"con 200 intervalos. Devuelve el resultado en notacion cientifica o con 8 decimales.", [val])


@reto("escala", "Interes compuesto con exponente grande")
def _escala_interes(r):
    p, tasa, n = r.randint(1000, 5000), r.choice([0.03, 0.05, 0.07]), r.randint(30, 50)
    val = p * (1 + tasa) ** n
    return (f"Un capital de {p} euros se invierte al {tasa*100:g}% de interes compuesto anual durante "
            f"{n} anos. Calcula el capital final. Redondea a 2 decimales.", [round(val, 2)])


@reto("escala", "Estadistica con outlier extremo")
def _escala_outlier(r):
    base = [r.randint(1, 10) for _ in range(8)]
    outlier = r.choice([10000, 50000, 100000])
    datos = base + [outlier]
    return (f"Dado el conjunto de datos {datos}, calcula la media y la mediana. Redondea a 4 decimales.",
            [statistics.mean(datos), statistics.median(datos)])


# =============================================================================
# 3. ALTA PRECISIÓN (exige 6-8 decimales)
# =============================================================================
@reto("precision", "Raices cuadraticas a 8 decimales", tol=1e-5)
def _precision_cuadratica(r):
    a = r.choice([1, 2, 3])
    b, c = r.randint(-9, 9) or 3, r.randint(-9, 9) or 2
    disc = b * b - 4 * a * c
    if disc < 0:
        b = 10
        disc = b * b - 4 * a * c
    sq = math.sqrt(disc)
    raices = sorted([(-b - sq) / (2 * a), (-b + sq) / (2 * a)])
    return (f"Resuelve la ecuacion cuadratica {pol([a, b, c])} = 0. Devuelve las raices con 8 decimales "
            f"exactos, sin redondeo prematuro en pasos intermedios.", raices)


@reto("precision", "Integral Simpson a 8 decimales", tol=1e-5)
def _precision_simpson(r):
    n = r.choice([200, 400])
    f = lambda x: math.exp(-x * x)
    val = simpson(f, 0, 2, n)
    return (f"Calcula la integral definida de f(x) = exp(-x^2) entre x=0 y x=2 usando Simpson 1/3 con "
            f"{n} intervalos. Devuelve el resultado con 8 decimales.", [val])


@reto("precision", "Trigonometria a 8 decimales", tol=1e-5)
def _precision_trigo(r):
    h, alfa = r.randint(5, 30), r.choice([17, 23, 41, 53, 67])
    return (f"Un triangulo rectangulo tiene hipotenusa {h} y un angulo agudo de {alfa} grados. Calcula "
            f"ambos catetos con 8 decimales de precision.",
            [h * math.sin(math.radians(alfa)), h * math.cos(math.radians(alfa))])


# =============================================================================
# 4. COMPOSICIÓN (encadena dos habilidades)
# =============================================================================
@reto("composicion", "Cuadratica -> raices como catetos -> hipotenusa", tol=1e-3)
def _comp_cuadratica_pitagoras(r):
    a_leg, b_leg = r.randint(3, 12), r.randint(3, 12)
    a, b, c = 1, -(a_leg + b_leg), a_leg * b_leg
    hip = math.hypot(a_leg, b_leg)
    return (f"Primero resuelve la ecuacion cuadratica {pol([a, b, c])} = 0 (sus dos raices son positivas). "
            f"Despues usa esas dos raices como los catetos de un triangulo rectangulo y calcula la "
            f"hipotenusa. Redondea todo a 4 decimales.", sorted([a_leg, b_leg]) + [hip])


@reto("composicion", "Factorizacion prima -> MCD y MCM de dos numeros relacionados")
def _comp_factor_mcd(r):
    primos = [2, 3, 5, 7, 11]
    fs = [r.choice(primos) for _ in range(r.randint(3, 4))]
    n1 = math.prod(fs)
    n2 = n1 * r.choice([2, 3, 5])
    return (f"Primero descompon en factores primos el numero {n1}. Despues, usando ese resultado, calcula "
            f"el Maximo Comun Divisor y el Minimo Comun Multiplo de {n1} y {n2}.",
            sorted(set(fs)) + [mcd(n1, n2), mcm(n1, n2)])


@reto("composicion", "Sistema lineal -> vector solucion -> producto escalar")
def _comp_sistema_vector(r):
    x, y = r.randint(-6, 6) or 1, r.randint(-6, 6) or 1
    while True:
        a, b, c, d = (r.randint(-5, 5) for _ in range(4))
        if a * d - b * c != 0:
            break
    p, q = r.randint(-5, 5), r.randint(-5, 5)
    dot = x * p + y * q
    return (f"Primero resuelve el sistema lineal {expr([a, b], ['x', 'y'])} = {a*x+b*y} y "
            f"{expr([c, d], ['x', 'y'])} = {c*x+d*y} para obtener x e y exactos. Despues, usando el "
            f"vector (x, y) como resultado, calcula su producto escalar con el vector ({p}, {q}).",
            [x, y, dot])


@reto("composicion", "Progresion aritmetica -> termino como radio -> area del circulo", tol=1e-3)
def _comp_progresion_area(r):
    a1, d, n = r.randint(1, 4), r.randint(1, 3), r.randint(4, 8)
    termino_n = a1 + (n - 1) * d
    area = math.pi * termino_n ** 2
    return (f"Primero calcula el termino n={n} de una progresion aritmetica con primer termino {a1} y "
            f"diferencia {d}. Despues usa ese termino como el radio de un circulo y calcula su area. "
            f"Redondea a 4 decimales.", [termino_n, area])


# =============================================================================
# COMUNICACIÓN Y VERIFICACIÓN
# =============================================================================
def peticion_get(endpoint: str) -> dict:
    req = urllib.request.Request(f"{API_BASE}/{endpoint.lstrip('/')}", headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def peticion_post(endpoint: str, data: dict | None = None) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"{API_BASE}/{endpoint.lstrip('/')}",
        data=json.dumps(data or {}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    def parsear(c):
        try:
            return json.loads(c) if c else {}
        except json.JSONDecodeError:
            return {"raw": c}
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, parsear(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        return err.code, parsear(err.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, {}


def estado_seguro() -> dict:
    try:
        return peticion_get("estado")
    except Exception:
        return {}


def esperar_reposo(timeout_s: int = 300) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        st = estado_seguro().get("organismo_estado")
        if st == "reposo":
            return True
        if st == "fallo":
            return False
        time.sleep(2.0)
    return False


def esperar_ciclo(timeout_s: int, gracia_s: float = 15.0, previo: str | None = None) -> bool:
    t0 = time.time()
    while time.time() - t0 < gracia_s:
        est = estado_seguro()
        if est.get("organismo_estado") != "reposo":
            break
        if previo is not None and (est.get("ultimo_resultado") or "") != previo:
            break
        time.sleep(0.5)
    return esperar_reposo(timeout_s)


_NUM_RE = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?")
_MILES_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+)(?!\d)")


def extraer_numeros(texto: str) -> list[float]:
    t = (texto or "").replace("\u2212", "-")
    nums: list[float] = []

    # 1. Rescatar números grandes con separador de miles antes de tocar las comas
    for m in _MILES_RE.finditer(t):
        try:
            nums.append(float(m.group(1).replace(",", "")))
        except ValueError:
            pass

    # 2. Rescatar todos los demás números (normales, decimales con punto o coma, científicos)
    for m in _NUM_RE.finditer(t):
        tok = m.group(0)
        try:
            if "," in tok:
                nums.append(float(tok.replace(",", ".")))
                nums.extend(float(p) for p in tok.split(",") if p not in ("", "-"))
            else:
                nums.append(float(tok))
        except ValueError:
            pass
    return nums


def _coincide(nums: list[float], esperado, tol: float) -> bool:
    # Soporte para alternativas numéricas (ej. porcentaje 9.08% o decimal 0.0908)
    alternativas = esperado if isinstance(esperado, (list, tuple)) else (esperado,)
    for a in alternativas:
        if (isinstance(a, int) or float(a).is_integer()) and abs(a) < 1000:
            margen = 1e-5
        else:
            # Tolerancia relativa estricta con suelo en 1e-7 (evita falsos negativos en 8 decimales)
            margen = max(tol * abs(a), 1e-7)
        if any(abs(x - a) <= margen for x in nums):
            return True
    return False


def verificar(texto: str, esperados: list, tol: float) -> tuple[bool, list]:
    nums = extraer_numeros(texto)
    faltan = [e for e in esperados if not _coincide(nums, e, tol)]
    return (not faltan), faltan


# =============================================================================
# AUDITOR
# =============================================================================
@dataclass
class Resultado:
    categoria: str
    tema: str
    muestra: int
    prompt: str
    esperados: list
    ok: bool = False
    faltantes: list = field(default_factory=list)
    respuesta: str = ""
    duracion: float = 0.0


class Auditor:
    def __init__(self, args):
        self.a = args
        self.resultados: list[Resultado] = []
        self.log_path: Path | None = None
        if not args.dry_run:
            Path(args.log_dir).mkdir(parents=True, exist_ok=True)
            self.log_path = Path(args.log_dir) / f"auditoria_{dt.datetime.now():%Y%m%d_%H%M%S}.jsonl"

    def conectar(self) -> bool:
        try:
            est = peticion_get("estado")
            print(f"➜ Organismo conectado. Órganos activos: {len(est.get('organos', []))}")
            return True
        except Exception as e:
            print(f"❌ No se puede conectar a {API_BASE}: {e}")
            return False

    def enviar(self, prompt: str) -> tuple[bool, str, float]:
        if not esperar_reposo(30):
            peticion_post("reset")
            time.sleep(2)
        previo = estado_seguro().get("ultimo_resultado") or ""
        status, _ = peticion_post("prompt", {"prompt": prompt})
        for _ in range(3):
            if status != 409:
                break
            time.sleep(5)
            status, _ = peticion_post("prompt", {"prompt": prompt})
        if not 200 <= status < 300:
            return False, f"❌ Error HTTP {status}", 0.0
        t0 = time.time()
        ok = esperar_ciclo(self.a.timeout, previo=previo)
        return ok, estado_seguro().get("ultimo_resultado") or "", time.time() - t0

    def resolver(self, rt: Reto, muestra: int) -> Resultado:
        rng = random.Random(f"{self.a.semilla}|{rt.tema}|{muestra}")
        prompt, esperados = rt.generar(rng)
        res = Resultado(rt.categoria, rt.tema, muestra, prompt, esperados)
        print(f"\n   ⚔️  [{NOMBRE_CAT[rt.categoria]}] {rt.tema} (muestra {muestra})")
        print(f"      \"{prompt[:100]}{'...' if len(prompt) > 100 else ''}\"")

        if self.a.dry_run:
            print(f"      Esperado: {[round(e, 8) if isinstance(e, float) else e for e in esperados]}")
            res.ok = True
            return res

        ok_ciclo, texto, dur = self.enviar(prompt)
        res.respuesta, res.duracion = texto, dur
        verificado, res.faltantes = verificar(texto, esperados, rt.tol)
        res.ok = ok_ciclo and verificado and "❌ Error" not in texto

        if res.ok:
            print(f"      ✅ Superado en {dur:.1f}s")
        else:
            print(f"      ❌ FRÁGIL. Faltan: {res.faltantes}")
            print(f"         {texto[:150].strip()}...")

        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": dt.datetime.now().isoformat(timespec="seconds"), **asdict(res)},
                                    ensure_ascii=False, default=str) + "\n")
        time.sleep(1)
        return res

    def podar(self):
        if self.a.dry_run:
            return
        print("\n   🧹 [HOMEOSTASIS AUTOMÁTICA]: Disparando remodelado tisular tras detectar fragilidad...")
        esperar_reposo(20)
        status, _ = peticion_post("remodelar")
        if status == 200 and esperar_ciclo(180, gracia_s=5):
            print("   ✨ Remodelado completado.")
        else:
            print("   ⚠️ El remodelado no se pudo completar a tiempo.")

    def ejecutar(self):
        print("=" * 72)
        print("⚔️  AUDITOR ADVERSARIAL DEL ORGANISMO MATEMÁTICO")
        print("=" * 72)
        if not self.a.dry_run and not self.conectar():
            return

        retos = [r for r in CURRICULUM if not self.a.categoria or r.categoria == self.a.categoria]
        print(f"➜ Retos: {len(retos)} | Muestras por reto: {self.a.muestras} | Semilla: {self.a.semilla}")
        if self.log_path:
            print(f"➜ Registro: {self.log_path}")
        print("-" * 72)

        for rt in retos:
            for m in range(self.a.muestras):
                self.resultados.append(self.resolver(rt, m))

        self.informe()

    def informe(self):
        print("\n" + "=" * 72)
        print("⚔️  INFORME DE FRAGILIDAD")
        print("=" * 72)
        if self.a.dry_run:
            print("   (dry-run: no se evaluó nada)")
            return

        por_categoria: dict[str, list[Resultado]] = {}
        for r in self.resultados:
            por_categoria.setdefault(r.categoria, []).append(r)

        total = len(self.resultados)
        if total == 0:
            print("   No se ejecutó ningún reto.")
            return

        fallos_totales = 0
        for cat_id, nombre in CATEGORIAS:
            items = por_categoria.get(cat_id, [])
            if not items:
                continue
            fallos = [r for r in items if not r.ok]
            fallos_totales += len(fallos)
            tasa_frag = len(fallos) / len(items)
            marca = "🔴" if tasa_frag > 0.4 else ("🟡" if tasa_frag > 0.15 else "🟢")
            print(f"   {marca} {nombre:<22} {len(items) - len(fallos)}/{len(items)} superados "
                  f"(fragilidad {tasa_frag*100:.1f}%)")
            for f in fallos[:3]:
                print(f"       ↳ {f.tema} — faltan {f.faltantes}")

        fragilidad_global = fallos_totales / total
        print(f"\n   ➜ Fragilidad global: {fragilidad_global*100:.1f}%  ({total - fallos_totales}/{total} superados)")
        print("=" * 72)

        if self.a.auto_remodelar and fragilidad_global > self.a.umbral_fragilidad:
            print(f"\n⚠️ Fragilidad global ({fragilidad_global*100:.1f}%) supera el umbral "
                  f"({self.a.umbral_fragilidad*100:.0f}%).")
            self.podar()
        elif fragilidad_global > self.a.umbral_fragilidad:
            print(f"\n💡 Sugerencia: fragilidad por encima del umbral. Ejecuta con --auto-remodelar "
                  f"o dispara manualmente la homeostasis del organismo.")


# =============================================================================
# CLI
# =============================================================================
def listar():
    for cat_id, nombre in CATEGORIAS:
        temas = [r.tema for r in CURRICULUM if r.categoria == cat_id]
        print(f"\n{nombre} ({cat_id})  —  {len(temas)} retos")
        for t in temas:
            print(f"   • {t}")
    print(f"\nTotal: {len(CURRICULUM)} retos adversariales")


def main():
    claves = [k for k, _ in CATEGORIAS]
    p = argparse.ArgumentParser(description="Auditor Adversarial del Organismo Matemático.")
    p.add_argument("--categoria", choices=claves, help="Auditar solo una categoría (default: todas).")
    p.add_argument("--muestras", type=int, default=1, help="Variantes por reto (default: 1).")
    p.add_argument("--umbral-fragilidad", type=float, default=0.25, dest="umbral_fragilidad",
                   help="Fragilidad global para alertar o remodelar (default 0.25).")
    p.add_argument("--auto-remodelar", action="store_true", help="Disparar /remodelar automáticamente si se supera el umbral.")
    p.add_argument("--timeout", type=int, default=360, help="Segundos máximos por reto.")
    p.add_argument("--semilla", type=int, default=int(time.time()) % 1_000_000, help="Semilla de los generadores.")
    p.add_argument("--log-dir", default="logs/auditoria", help="Directorio del registro JSONL.")
    p.add_argument("--dry-run", action="store_true", help="Muestra prompts y valores esperados sin usar el servidor.")
    p.add_argument("--listar", action="store_true", help="Lista categorías y retos y sale.")
    args = p.parse_args()

    if args.listar:
        listar()
        return
    Auditor(args).ejecutar()


if __name__ == "__main__":
    main()