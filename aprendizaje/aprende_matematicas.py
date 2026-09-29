#!/usr/bin/env python3
"""
scripts/curriculum_matematicas.py - Entrenador Autonomo y Desatendido del Organismo Digital (v2).

Mejoras respecto a la v1
------------------------
1. Currículo ampliado de lo más simple a lo más complejo: 7 niveles, ~55 temas
   (Fundamentos -> Primaria -> Secundaria -> Bachillerato -> Universidad -> Master -> Doctorado).
2. Retos PARAMETRIZADOS: cada tema es un generador con semilla, así que cada ejecución
   produce problemas nuevos (evita memorizar la respuesta de un enunciado fijo).
3. VERIFICACIÓN INDEPENDIENTE: la respuesta correcta se calcula en Python (stdlib) y se
   comprueba contra los números de la respuesta del organismo. Ya no se da por bueno
   un reto solo porque el texto no contiene "❌ Error".
4. DOMINIO POR NIVEL: no se asciende hasta superar un umbral (por defecto 70 %), con
   rondas de refuerzo (nuevas variantes de los temas fallados).
5. REPASO ESPACIADO: al terminar cada nivel se re-examinan temas de niveles anteriores
   para detectar olvido (retención).
6. Reintentos por reto con pista de autoverificación.
7. Corrección de una condición de carrera: tras enviar un prompt o una poda, el organismo
   aún puede figurar en 'reposo' unos instantes, y la v1 podía leer un resultado antiguo.
8. Registro JSONL de cada intento y resumen final por nivel.
9. Modo --dry-run (sin servidor) y --listar para inspeccionar el currículo.

Uso
---
    python curriculum_matematicas.py                       # currículo completo
    python curriculum_matematicas.py --nivel secundaria    # solo un nivel
    python curriculum_matematicas.py --desde bachillerato  # de ese nivel hacia arriba
    python curriculum_matematicas.py --variantes 3 --umbral 0.8 --refuerzos 2
    python curriculum_matematicas.py --dry-run --semilla 7 # ver prompts y respuestas esperadas
    python curriculum_matematicas.py --listar
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
from fractions import Fraction
from functools import reduce
from pathlib import Path
from statistics import NormalDist
from typing import Callable

API_BASE = "http://localhost:8888/api"

NIVELES = [
    ("fundamentos", "0. Fundamentos"),
    ("primaria", "1. Primaria"),
    ("secundaria", "2. Secundaria"),
    ("bachillerato", "3. Bachillerato"),
    ("universidad", "4. Universidad"),
    ("master", "5. Master"),
    ("doctorado", "6. Doctorado"),
]
NOMBRE_NIVEL = dict(NIVELES)

DEC = " Redondea a 4 decimales."
PISTA = " Verifica el resultado con un segundo metodo independiente antes de responder."


# =============================================================================
# REGISTRO DE RETOS (cada tema es un generador parametrizado)
# =============================================================================
@dataclass(frozen=True)
class Reto:
    nivel: str
    tema: str
    generar: Callable  # (random.Random) -> (prompt: str, esperados: list)
    tol: float = 1e-3


CURRICULUM: list[Reto] = []


def reto(nivel: str, tema: str, tol: float = 1e-3):
    def deco(fn):
        CURRICULUM.append(Reto(nivel, tema, fn, tol))
        return fn
    return deco


# ----------------------------- utilidades matematicas ------------------------
def mcd(*n): return reduce(math.gcd, n)
def mcm(*n): return reduce(lambda a, b: a * b // math.gcd(a, b), n)
def pct(x): return (x, x * 100)  # acepta 0.1611 o 16.11 (%)
def distinto_de_cero(r, lo, hi): return r.choice([v for v in range(lo, hi + 1) if v])


def expr(coefs, mons):
    s = ""
    for c, m in zip(coefs, mons):
        if c == 0:
            continue
        mag = abs(c)
        cuerpo = str(mag) if not m else (m if mag == 1 else f"{mag}*{m}")
        if not s:
            s = ("-" if c < 0 else "") + cuerpo
        else:
            s += (" - " if c < 0 else " + ") + cuerpo
    return s or "0"


def pol(coefs, var="x"):
    n = len(coefs) - 1
    return expr(coefs, [("" if p == 0 else var if p == 1 else f"{var}^{p}") for p in range(n, -1, -1)])


def det2(M): return M[0][0] * M[1][1] - M[0][1] * M[1][0]


def det3(M):
    return (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
            - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
            + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))


def matmul(A, B):
    return [[sum(A[i][k] * B[k][j] for k in range(len(B))) for j in range(len(B[0]))] for i in range(len(A))]


def simpson(f, a, b, n):
    h = (b - a) / n
    s = f(a) + f(b) + sum((4 if i % 2 else 2) * f(a + i * h) for i in range(1, n))
    return s * h / 3


def rk4(f, x0, y0, h, n):
    x, y = x0, y0
    for _ in range(n):
        k1 = f(x, y)
        k2 = f(x + h / 2, y + h * k1 / 2)
        k3 = f(x + h / 2, y + h * k2 / 2)
        k4 = f(x + h, y + h * k3)
        y += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
        x += h
    return y


def autovalores_sim3(A):
    """Autovalores de una matriz simetrica 3x3 (metodo trigonometrico)."""
    p1 = A[0][1] ** 2 + A[0][2] ** 2 + A[1][2] ** 2
    q = (A[0][0] + A[1][1] + A[2][2]) / 3
    if p1 == 0:
        return sorted(float(A[i][i]) for i in range(3))
    p2 = sum((A[i][i] - q) ** 2 for i in range(3)) + 2 * p1
    p = math.sqrt(p2 / 6)
    B = [[(A[i][j] - (q if i == j else 0)) / p for j in range(3)] for i in range(3)]
    phi = math.acos(max(-1.0, min(1.0, det3(B) / 2))) / 3
    e1 = q + 2 * p * math.cos(phi)
    e3 = q + 2 * p * math.cos(phi + 2 * math.pi / 3)
    return sorted([e1, 3 * q - e1 - e3, e3])


def ec_suma(P, Q, a, p):
    if P is None: return Q
    if Q is None: return P
    (x1, y1), (x2, y2) = P, Q
    if x1 == x2 and (y1 + y2) % p == 0:
        return None
    if P == Q:
        lam = (3 * x1 * x1 + a) * pow(2 * y1, -1, p) % p
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (lam * lam - x1 - x2) % p
    return (x3, (lam * (x1 - x3) - y1) % p)


# =============================================================================
# NIVEL 0: FUNDAMENTOS
# =============================================================================
@reto("fundamentos", "Suma")
def _suma(r):
    a, b = r.randint(100, 9999), r.randint(100, 9999)
    return f"Calcula {a} + {b}", [a + b]


@reto("fundamentos", "Resta")
def _resta(r):
    a = r.randint(1000, 9999); b = r.randint(100, a - 1)
    return f"Calcula {a} - {b}", [a - b]


@reto("fundamentos", "Multiplicacion")
def _mult(r):
    a, b = r.randint(12, 99), r.randint(12, 99)
    return f"Calcula {a} * {b}", [a * b]


@reto("fundamentos", "Division con resto")
def _div(r):
    b = r.randint(7, 19); a = r.randint(100, 999)
    return f"Divide {a} entre {b} y devuelve el cociente entero y el resto", [a // b, a % b]


@reto("fundamentos", "Jerarquia de operaciones")
def _jerarquia(r):
    a, b, c, e, k = r.randint(2, 9), r.randint(2, 9), r.randint(2, 9), r.randint(2, 6), r.randint(2, 9)
    return (f"Evalua la expresion ({a} + {b}) * {c} - {e * k} / {e} respetando la jerarquia de operaciones",
            [(a + b) * c - k])


@reto("fundamentos", "Potencias")
def _potencias(r):
    b, n = r.randint(2, 9), r.randint(2, 6)
    return f"Calcula {b}^{n}", [b ** n]


@reto("fundamentos", "Numeros negativos")
def _negativos(r):
    a, b, c, d = r.randint(2, 12), r.randint(2, 12), r.randint(2, 30), r.randint(2, 30)
    return f"Calcula (-{a}) * {b} + {c} - (-{d})", [-a * b + c + d]


@reto("fundamentos", "Decimales")
def _decimales(r):
    a, b = r.randint(11, 999) / 10, r.randint(11, 999) / 10
    return f"Calcula {a:.1f} + {b:.1f} y luego {a:.1f} - {b:.1f}", [round(a + b, 1), round(a - b, 1)]


# =============================================================================
# NIVEL 1: PRIMARIA
# =============================================================================
@reto("primaria", "MCD y MCM")
def _mcd_mcm(r):
    g = r.choice([2, 3, 4, 6, 8, 12])
    nums = [g * m for m in r.sample([2, 3, 4, 5, 6, 7, 9, 10, 15], 3)]
    return (f"Calcula el Maximo Comun Divisor (MCD) y el Minimo Comun Multiplo (MCM) de {nums[0]}, {nums[1]} y {nums[2]}",
            [mcd(*nums), mcm(*nums)])


@reto("primaria", "Factores Primos")
def _factores(r):
    primos = [2, 3, 5, 7, 11, 13]
    fs = [r.choice(primos) for _ in range(r.randint(3, 5))]
    n = math.prod(fs)
    return f"Descompon en factores primos el numero {n}", sorted(set(fs))


@reto("primaria", "Aritmetica de Fracciones")
def _fracciones(r):
    def frac():
        d = r.choice([2, 3, 4, 5, 6, 7, 8, 10, 12, 14])
        return Fraction(r.randint(1, d - 1), d), d
    (f1, d1), (f2, d2), (f3, d3) = frac(), frac(), frac()
    res = f1 + f2 - f3
    txt = lambda f: f"{f.numerator}/{f.denominator}" if f.denominator == 1 or f.numerator else "0"
    return (f"Calcula {f1.numerator}/{f1.denominator} + {f2.numerator}/{f2.denominator} - {f3.numerator}/{f3.denominator} y devuelve el resultado "
            f"como fraccion irreducible y como decimal.{DEC}", [float(res)])


@reto("primaria", "Porcentajes y descuentos")
def _porcentajes(r):
    precio = r.randint(4, 40) * 10; d = r.choice([10, 15, 20, 25, 30, 40])
    return (f"Un articulo cuesta {precio} euros. Se le aplica un descuento del {d}% y despues un IVA del 21%. "
            f"Calcula el precio final en euros.", [round(precio * (1 - d / 100) * 1.21, 2)])


@reto("primaria", "Regla de tres")
def _regla_tres(r):
    n1, n2 = r.randint(3, 9), r.randint(10, 20)
    p = r.choice([0.5, 0.75, 1.25, 1.5, 2.5, 3.2])
    return (f"Si {n1} cuadernos cuestan {n1 * p:.2f} euros, cuanto cuestan {n2} cuadernos?", [round(n2 * p, 2)])


@reto("primaria", "Areas y perimetros")
def _areas(r):
    rad = r.randint(2, 12); b, h = r.randint(3, 20), r.randint(3, 20)
    return (f"Calcula el area de un circulo de radio {rad} y el perimetro de un rectangulo de {b} por {h}.{DEC}",
            [math.pi * rad ** 2, 2 * (b + h)])


@reto("primaria", "Conversion de unidades")
def _unidades(r):
    v = r.choice([36, 54, 72, 90, 108, 126, 144])
    return f"Convierte {v} km/h a metros por segundo", [v / 3.6]


# =============================================================================
# NIVEL 2: SECUNDARIA
# =============================================================================
@reto("secundaria", "Ecuaciones lineales")
def _lineal(r):
    x = distinto_de_cero(r, -9, 9); a = r.randint(2, 9); c = r.randint(1, a - 1); b = r.randint(-9, 9)
    d = b + (a - c) * x
    return f"Resuelve la ecuacion {a}x + ({b}) = {c}x + ({d})", [x]


@reto("secundaria", "Ecuaciones Cuadraticas")
def _cuadratica(r):
    while True:
        a = r.choice([1, 2, 3]); r1 = distinto_de_cero(r, -6, 6)
        p = r.choice([v for v in range(-9, 10) if v and math.gcd(v, a) == 1])
        if r1 * a != p:
            break
    return (f"Resuelve la ecuacion cuadratica {pol([a, -(a * r1 + p), r1 * p])} = 0 y devuelve sus raices ordenadas.{DEC}",
            sorted([r1, p / a]))


@reto("secundaria", "Sistemas Lineales 2x2")
def _sistema(r):
    x, y = r.randint(-6, 6), r.randint(-6, 6)
    while True:
        a, b, c, d = (r.randint(-5, 5) for _ in range(4))
        if a * d - b * c != 0:
            break
    return (f"Resuelve el sistema lineal {expr([a, b], ['x', 'y'])} = {a * x + b * y} y "
            f"{expr([c, d], ['x', 'y'])} = {c * x + d * y} devolviendo los valores exactos de x e y", [x, y])


@reto("secundaria", "Geometria de Heron")
def _heron(r):
    while True:
        a, b, c = sorted(r.randint(4, 20) for _ in range(3))
        if a + b > c:
            break
    s = (a + b + c) / 2
    area = math.sqrt(s * (s - a) * (s - b) * (s - c))
    return (f"Calcula el area y el perimetro de un triangulo cuyos lados miden a={a}, b={b} y c={c} "
            f"usando la formula de Heron.{DEC}", [area, a + b + c])


@reto("secundaria", "Raices y potencias")
def _raices(r):
    n = r.choice([v for v in range(2, 200) if int(math.sqrt(v)) ** 2 != v]); m = r.randint(3, 15)
    return f"Calcula la raiz cuadrada de {n} y el cubo de {m}.{DEC}", [math.sqrt(n), m ** 3]


@reto("secundaria", "Progresion aritmetica")
def _prog_arit(r):
    a1, d, n = r.randint(-5, 10), r.randint(2, 7), r.randint(10, 30)
    return (f"En una progresion aritmetica con primer termino {a1} y diferencia {d}, calcula el termino n={n} "
            f"y la suma de los primeros {n} terminos", [a1 + (n - 1) * d, n * (2 * a1 + (n - 1) * d) // 2])


@reto("secundaria", "Progresion geometrica")
def _prog_geo(r):
    a1, q, n = r.randint(1, 5), r.choice([2, 3]), r.randint(5, 9)
    return (f"En una progresion geometrica con primer termino {a1} y razon {q}, calcula el termino n={n} "
            f"y la suma de los primeros {n} terminos", [a1 * q ** (n - 1), a1 * (q ** n - 1) // (q - 1)])


@reto("secundaria", "Estadistica descriptiva")
def _estadistica(r):
    datos = [r.randint(1, 30) for _ in range(r.randint(9, 11))]
    return (f"Dado el conjunto de datos {datos}, calcula la media, la mediana y la desviacion tipica poblacional.{DEC}",
            [statistics.mean(datos), statistics.median(datos), statistics.pstdev(datos)])


@reto("secundaria", "Combinatoria")
def _combinatoria(r):
    n, k = r.randint(6, 12), r.randint(2, 4)
    return (f"De {n} elementos, cuantas formas hay de elegir {k} sin importar el orden y cuantas de ordenar {k} de ellos?",
            [math.comb(n, k), math.perm(n, k)])


@reto("secundaria", "Probabilidad sin reposicion")
def _prob_urna(r):
    R, B = r.randint(3, 8), r.randint(3, 8)
    p = Fraction(R, R + B) * Fraction(R - 1, R + B - 1)
    return (f"Una urna tiene {R} bolas rojas y {B} azules. Se extraen 2 sin reposicion. Calcula la probabilidad "
            f"de que ambas sean rojas (fraccion irreducible y decimal).{DEC}", [pct(float(p))])


# =============================================================================
# NIVEL 3: BACHILLERATO
# =============================================================================
@reto("bachillerato", "Derivadas")
def _derivadas(r):
    a, b, c, d = r.randint(1, 4), r.randint(-5, 5), r.randint(-6, 6), r.randint(-6, 6)
    x0 = distinto_de_cero(r, -3, 3)
    return (f"Dada f(x) = {pol([a, b, c, d])}, calcula f'({x0}) y f''({x0})",
            [3 * a * x0 ** 2 + 2 * b * x0 + c, 6 * a * x0 + 2 * b])


@reto("bachillerato", "Limites")
def _limites(r):
    a, b, c, d = r.randint(1, 9), r.randint(-5, 5), r.randint(1, 9), r.randint(-5, 5)
    return (f"Calcula el limite cuando x tiende a infinito de ({pol([a, b, 0])}) / ({pol([c, 0, d])}).{DEC}", [a / c])


@reto("bachillerato", "Optimizacion de funciones")
def _optimizacion(r):
    a, b, c = r.randint(1, 5), r.randint(2, 12), r.randint(-5, 10)
    return (f"Halla el maximo de f(x) = {expr([-a, b, c], ['x^2', 'x', ''])}: devuelve el valor de x y el valor maximo de f.{DEC}",
            [b / (2 * a), c + b * b / (4 * a)])


@reto("bachillerato", "Integral definida polinomica")
def _integral(r):
    a, b, c = r.randint(1, 5), r.randint(-4, 6), r.randint(-5, 5); lo, hi = r.randint(-2, 1), r.randint(2, 4)
    F = lambda x: a * x ** 3 / 3 + b * x ** 2 / 2 + c * x
    return (f"Calcula la integral definida de f(x) = {pol([a, b, c])} entre x={lo} y x={hi}.{DEC}", [F(hi) - F(lo)])


@reto("bachillerato", "Integracion Numerica")
def _simpson(r):
    opciones = [
        ("x^2 * sin(x)", lambda x: x * x * math.sin(x), 0, math.pi, "x=0 y x=pi"),
        ("x * exp(x)", lambda x: x * math.exp(x), 0, 1, "x=0 y x=1"),
        ("exp(-x^2)", lambda x: math.exp(-x * x), 0, 2, "x=0 y x=2"),
        ("1 / (1 + x^2)", lambda x: 1 / (1 + x * x), 0, 1, "x=0 y x=1"),
    ]
    desc, f, a, b, txt = r.choice(opciones); n = r.choice([50, 100, 200])
    return (f"Calcula la integral definida de f(x) = {desc} entre {txt} usando la regla de Simpson 1/3 "
            f"con {n} intervalos.{DEC}", [simpson(f, a, b, n)])


@reto("bachillerato", "Algebra Vectorial 3D")
def _vectores(r):
    u = [r.randint(-4, 5) for _ in range(3)]; v = [r.randint(-4, 5) for _ in range(3)]
    cruz = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    return (f"Dados los vectores u={u} y v={v}, calcula su producto escalar, su producto vectorial u x v "
            f"y el modulo del vector resultante.{DEC}",
            [sum(a * b for a, b in zip(u, v)), *cruz, math.sqrt(sum(c * c for c in cruz))])


@reto("bachillerato", "Determinante 3x3")
def _det3(r):
    M = [[r.randint(-4, 6) for _ in range(3)] for _ in range(3)]
    return f"Calcula el determinante de la matriz A = {M}", [det3(M)]


@reto("bachillerato", "Matriz inversa 2x2")
def _inversa(r):
    while True:
        M = [[r.randint(-5, 6) for _ in range(2)] for _ in range(2)]
        if det2(M) != 0:
            break
    d = det2(M)
    inv = [M[1][1] / d, -M[0][1] / d, -M[1][0] / d, M[0][0] / d]
    return f"Calcula la matriz inversa de A = {M}.{DEC}", inv


@reto("bachillerato", "Distribucion Normal")
def _normal(r):
    mu, sigma = r.randint(50, 100), r.randint(5, 15)
    x = round(mu + r.choice([-1.5, -1, -0.5, 0.5, 1, 1.5, 2]) * sigma, 1); conf = r.choice([90, 95, 99])
    return (f"Sea X normal con media {mu} y desviacion tipica {sigma}. Calcula P(X <= {x}) y el valor critico Z "
            f"bilateral para un nivel de confianza del {conf}%.{DEC}",
            [pct(NormalDist(mu, sigma).cdf(x)), NormalDist().inv_cdf(0.5 + conf / 200)])


@reto("bachillerato", "Logaritmos y exponenciales")
def _logaritmos(r):
    a, b = r.choice([2, 3, 5, 10]), r.randint(20, 500)
    return f"Resuelve la ecuacion exponencial {a}^x = {b} y devuelve x.{DEC}", [math.log(b) / math.log(a)]


@reto("bachillerato", "Trigonometria")
def _trigo(r):
    h, alfa = r.randint(5, 30), r.choice(range(20, 75, 5))
    return (f"Un triangulo rectangulo tiene hipotenusa {h} y un angulo agudo de {alfa} grados. "
            f"Calcula la longitud de ambos catetos.{DEC}",
            [h * math.sin(math.radians(alfa)), h * math.cos(math.radians(alfa))])


@reto("bachillerato", "Numeros complejos")
def _complejos(r):
    while True:
        a, b, c, d = (r.randint(-5, 5) for _ in range(4))
        if (a or b) and (c or d):
            break
    return (f"Calcula el producto ({a}{b:+d}i)*({c}{d:+d}i) y el modulo de ({a}{b:+d}i).{DEC}",
            [a * c - b * d, a * d + b * c, math.hypot(a, b)])


# =============================================================================
# NIVEL 4: UNIVERSIDAD
# =============================================================================
@reto("universidad", "Newton-Raphson")
def _newton(r):
    c = r.randint(2, 12); x = 3.0
    for _ in range(100):
        dx = (x ** 3 - x - c) / (3 * x * x - 1); x -= dx
        if abs(dx) < 1e-14:
            break
    return f"Halla con Newton-Raphson, partiendo de x0=3, la raiz de f(x) = x^3 - x - {c}.{DEC}", [x]


@reto("universidad", "Ecuaciones Diferenciales (RK4)")
def _rk4(r):
    edos = [("y - x^2 + 1", lambda x, y: y - x * x + 1, 0.5), ("x + y", lambda x, y: x + y, 1.0),
            ("-2*y + x", lambda x, y: -2 * y + x, 1.0)]
    desc, f, y0 = r.choice(edos); xf = r.choice([1.0, 1.5, 2.0])
    return (f"Resuelve la ecuacion diferencial dy/dx = {desc} con y(0) = {y0} usando Runge-Kutta 4 con paso h=0.1 "
            f"y devuelve y({xf}).{DEC}", [rk4(f, 0.0, y0, 0.1, round(xf / 0.1))])


@reto("universidad", "EDO lineal de primer orden")
def _edo_lineal(r):
    k, c, y0, t = r.choice([0.5, 1, 2]), r.randint(1, 6), r.randint(-3, 3), r.choice([0.5, 1, 2])
    return (f"Resuelve analiticamente y' + {k}*y = {c} con y(0) = {y0} y evalua y({t}).{DEC}",
            [c / k + (y0 - c / k) * math.exp(-k * t)])


@reto("universidad", "Autovalores y Autovectores")
def _autovalores(r):
    A = [[0] * 3 for _ in range(3)]
    for i in range(3):
        A[i][i] = r.randint(1, 6)
        for j in range(i + 1, 3):
            A[i][j] = A[j][i] = r.randint(0, 3)
    return (f"Calcula los autovalores y el determinante de la matriz simetrica A = {A}.{DEC}",
            [*autovalores_sim3(A), det3(A)])


@reto("universidad", "Descomposicion LU")
def _lu(r):
    nz = [-3, -2, -1, 1, 2, 3]
    l21, l31, l32 = (r.choice(nz) for _ in range(3))
    u11, u22, u33 = (r.choice([-2, -1, 1, 2, 3, 4]) for _ in range(3))
    u12, u13, u23 = (r.choice(nz) for _ in range(3))
    L = [[1, 0, 0], [l21, 1, 0], [l31, l32, 1]]; U = [[u11, u12, u13], [0, u22, u23], [0, 0, u33]]
    return (f"Calcula la descomposicion LU sin pivoteo (L con diagonal unitaria) de la matriz A = {matmul(L, U)} "
            f"y devuelve las matrices L y U", [l21, l31, l32, u11, u12, u13, u22, u23, u33])


@reto("universidad", "Series de Taylor")
def _taylor(r):
    fn, n = r.choice([("exp", 4), ("exp", 5), ("exp", 6), ("sin", 3), ("sin", 5), ("sin", 7), ("cos", 2), ("cos", 4), ("cos", 6)])
    x = r.choice([0.5, 1.0, 1.5, 2.0])
    if fn == "exp":
        v, nom = sum(x ** k / math.factorial(k) for k in range(n + 1)), "e^x"
    elif fn == "sin":
        v, nom = sum((-1) ** k * x ** (2 * k + 1) / math.factorial(2 * k + 1) for k in range((n - 1) // 2 + 1)), "sin(x)"
    else:
        v, nom = sum((-1) ** k * x ** (2 * k) / math.factorial(2 * k) for k in range(n // 2 + 1)), "cos(x)"
    return f"Calcula el polinomio de Taylor de grado {n} de {nom} en torno a 0, evaluado en x={x}.{DEC}", [v]


@reto("universidad", "Minimos cuadrados")
def _minimos_cuadrados(r):
    m, b = r.choice([-3, -2, -1, 1, 2, 3]), r.randint(-5, 5)
    xs = list(range(1, 7)); ys = [round(m * x + b + r.uniform(-1, 1), 1) for x in xs]
    n = len(xs); sx, sy = sum(xs), sum(ys); sxy = sum(x * y for x, y in zip(xs, ys)); sxx = sum(x * x for x in xs)
    pend = (n * sxy - sx * sy) / (n * sxx - sx ** 2)
    return (f"Ajusta una recta y = m*x + n por minimos cuadrados a los puntos x={xs}, y={ys}. Devuelve m y n.{DEC}",
            [pend, (sy - pend * sx) / n])


@reto("universidad", "Teorema de Bayes")
def _bayes(r):
    prev, sens, esp = r.choice([0.01, 0.02, 0.05]), r.choice([0.9, 0.95, 0.99]), r.choice([0.9, 0.95, 0.98])
    post = prev * sens / (prev * sens + (1 - prev) * (1 - esp))
    return (f"Una enfermedad tiene prevalencia {prev * 100:g}%. La prueba tiene sensibilidad {sens * 100:g}% y "
            f"especificidad {esp * 100:g}%. Si una persona da positivo, cual es la probabilidad de estar enferma?{DEC}",
            [pct(post)])


@reto("universidad", "Integral doble")
def _integral_doble(r):
    a, b, c = r.randint(1, 4), r.randint(1, 4), r.randint(1, 5)
    return (f"Calcula la integral doble de f(x,y) = x*y + {c} sobre el rectangulo [0,{a}] x [0,{b}].{DEC}",
            [(a * a / 2) * (b * b / 2) + c * a * b])


@reto("universidad", "Intervalo de confianza")
def _ic(r):
    xb, s, n = r.randint(50, 150), r.randint(5, 20), r.choice([25, 36, 49, 64, 100])
    e = 1.96 * s / math.sqrt(n)
    return (f"Una muestra de tamano {n} tiene media {xb} y la desviacion tipica poblacional conocida es {s}. "
            f"Calcula el intervalo de confianza del 95% para la media usando z=1.96.{DEC}", [xb - e, xb + e])


@reto("universidad", "Congruencias modulares")
def _congruencias(r):
    a, b, m = r.randint(3, 50), r.randint(20, 200), r.choice([101, 103, 107, 109, 113, 127, 131])
    return (f"Calcula {a}^{b} mod {m} y el inverso multiplicativo de {a} modulo {m}",
            [pow(a, b, m), pow(a, -1, m)])


# =============================================================================
# NIVEL 5: MASTER
# =============================================================================
@reto("master", "Valores singulares (SVD 2x2)")
def _svd(r):
    while True:
        a, b, c, d = (r.randint(-4, 5) for _ in range(4))
        if a * d - b * c != 0:
            break
    t = a * a + b * b + c * c + d * d; dt_ = (a * d - b * c) ** 2
    disc = math.sqrt(max(0.0, t * t - 4 * dt_))
    return (f"Calcula los valores singulares de la matriz A = {[[a, b], [c, d]]}.{DEC}",
            [math.sqrt((t + disc) / 2), math.sqrt(max(0.0, (t - disc) / 2))])


@reto("master", "Descenso de gradiente")
def _gradiente(r):
    a, c, b, k = distinto_de_cero(r, -5, 5), distinto_de_cero(r, -5, 5), r.choice([1, 2, 3]), r.choice([10, 20, 30])
    x = y = 0.0
    for _ in range(k):
        x -= 0.1 * 2 * (x - a); y -= 0.1 * 2 * b * (y - c)
    return (f"Aplica {k} iteraciones de descenso de gradiente con tasa 0.1, partiendo de (0,0), a "
            f"f(x,y) = ({expr([1, -a], ['x', ''])})^2 + {b}*({expr([1, -c], ['y', ''])})^2 y devuelve el punto final.{DEC}",
            [x, y])


@reto("master", "Cadenas de Markov")
def _markov(r):
    P = []
    for _ in range(3):
        a = r.randint(1, 7); b = r.randint(1, 9 - a)
        P.append([a / 10, b / 10, round(1 - (a + b) / 10, 1)])
    pi = [1 / 3] * 3
    for _ in range(5000):
        pi = [sum(pi[i] * P[i][j] for i in range(3)) for j in range(3)]
    return (f"Cadena de Markov de 3 estados con matriz de transicion P = {P} (filas suman 1). "
            f"Calcula la distribucion estacionaria pi tal que pi*P = pi.{DEC}", pi)


@reto("master", "Ecuacion del calor")
def _calor(r):
    al, t = r.choice([0.01, 0.02, 0.05, 0.1]), r.choice([0.5, 1.0, 2.0])
    return (f"Resuelve u_t = {al}*u_xx en [0,1] con u(0,t)=u(1,t)=0 y u(x,0)=sin(pi*x). Calcula u(0.5, {t}).{DEC}",
            [math.exp(-math.pi ** 2 * al * t)])


@reto("master", "RSA")
def _rsa(r):
    while True:
        p, q = r.sample([11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61], 2)
        phi = (p - 1) * (q - 1); es = [e for e in (5, 7, 11, 13, 17, 19) if math.gcd(e, phi) == 1]
        if es:
            break
    e = r.choice(es); n = p * q; m = r.randint(2, n - 1)
    return (f"RSA de juguete con p={p}, q={q}, e={e}. Calcula n, phi(n), la clave privada d y el cifrado "
            f"de m={m} (c = m^e mod n)", [n, phi, pow(e, -1, phi), pow(m, e, n)])


@reto("master", "Multiplicadores de Lagrange")
def _lagrange(r):
    a, b, c = r.randint(1, 4), r.randint(1, 4), r.randint(1, 12); s = a * a + b * b
    return (f"Con multiplicadores de Lagrange, minimiza f(x,y) = x^2 + y^2 sujeto a {a}x + {b}y = {c}. "
            f"Devuelve el punto optimo y el valor minimo.{DEC}", [a * c / s, b * c / s, c * c / s])


@reto("master", "Entropia de Shannon")
def _entropia(r):
    cuts = sorted(r.sample(range(1, 10), 3)); w = [cuts[0], cuts[1] - cuts[0], cuts[2] - cuts[1], 10 - cuts[2]]
    p = [x / 10 for x in w]
    return (f"Calcula la entropia de Shannon en bits de la distribucion de probabilidad {p}.{DEC}",
            [-sum(x * math.log2(x) for x in p)])


# =============================================================================
# NIVEL 6: DOCTORADO / INVESTIGACION
# =============================================================================
@reto("doctorado", "Criptografia de Curva Eliptica")
def _curva_eliptica(r):
    while True:
        p, a, b = r.choice([97, 101, 103, 107, 109, 113]), r.randint(1, 10), r.randint(1, 10)
        if (4 * a ** 3 + 27 * b * b) % p == 0:
            continue
        cand = [(x, y) for x in range(p) for y in range(1, p) if (y * y - (x ** 3 + a * x + b)) % p == 0]
        if len(cand) < 4:
            continue
        P, Q = r.sample(cand, 2)
        if P[0] == Q[0]:
            continue
        S, D = ec_suma(P, Q, a, p), ec_suma(P, P, a, p)
        if S and D:
            break
    return (f"En la curva eliptica y^2 = {expr([1, a, b], ['x^3', 'x', ''])} sobre el campo finito F_{p}, dados los "
            f"puntos P={P} y Q={Q}, calcula la suma de puntos P + Q y el doble 2P", [S[0], S[1], D[0], D[1]])


@reto("doctorado", "Calculo Estocastico (GBM)", tol=1e-3)
def _gbm(r):
    S0, mu, sg, T = r.choice([50, 100, 150]), r.choice([0.05, 0.08, 0.1]), r.choice([0.2, 0.25, 0.3]), r.choice([1, 2])
    media = S0 * math.exp(mu * T); var = S0 ** 2 * math.exp(2 * mu * T) * (math.exp(sg ** 2 * T) - 1)
    return (f"Para un Movimiento Browniano Geometrico (SDE dS = mu*S*dt + sigma*S*dW) con S0={S0}, mu={mu}, "
            f"sigma={sg}, calcula analiticamente la esperanza y la varianza de S_T en T={T} ano(s).{DEC}", [media, var])


@reto("doctorado", "Black-Scholes", tol=2e-3)
def _black_scholes(r):
    S, K, rr, sg, T = r.choice([80, 100, 120]), r.choice([90, 100, 110]), r.choice([0.03, 0.05]), r.choice([0.2, 0.3]), r.choice([0.5, 1])
    d1 = (math.log(S / K) + (rr + sg * sg / 2) * T) / (sg * math.sqrt(T)); d2 = d1 - sg * math.sqrt(T)
    N = NormalDist().cdf; call = S * N(d1) - K * math.exp(-rr * T) * N(d2); put = call - S + K * math.exp(-rr * T)
    return (f"Precio Black-Scholes de una opcion call y una put europeas con S={S}, K={K}, r={rr}, sigma={sg}, "
            f"T={T} anos.{DEC}", [call, put])


@reto("doctorado", "Proceso de Ornstein-Uhlenbeck")
def _ou(r):
    th, mu, sg, x0, t = r.choice([0.5, 1, 2]), r.choice([0, 1, 2]), r.choice([0.3, 0.5, 1]), r.choice([3, 4]), r.choice([0.5, 1, 2])
    return (f"Para el proceso dX = {th}*({mu} - X)dt + {sg}*dW con X0={x0}, calcula la esperanza y la varianza de X_t en t={t}.{DEC}",
            [mu + (x0 - mu) * math.exp(-th * t), sg ** 2 / (2 * th) * (1 - math.exp(-2 * th * t))])


@reto("doctorado", "Ruina del jugador")
def _ruina(r):
    p, N = r.choice([0.4, 0.45, 0.55, 0.6]), r.choice([10, 12, 15]); i = r.randint(3, 8); rho = (1 - p) / p
    gana = (1 - rho ** i) / (1 - rho ** N)
    return (f"Un jugador con capital inicial {i} apuesta 1 unidad en cada ronda, ganando con probabilidad {p}. "
            f"Se detiene al llegar a 0 (ruina) o a {N}. Calcula la probabilidad de ruina.{DEC}", [pct(1 - gana)])


@reto("doctorado", "Pozo de potencial infinito")
def _pozo(r):
    L = r.choice([1, 2])
    return (f"Para el hamiltoniano H = -(1/2) d^2/dx^2 en [0,{L}] con condiciones de Dirichlet nulas "
            f"(hbar = m = 1), calcula los tres primeros niveles de energia E_1, E_2 y E_3.{DEC}",
            [n * n * math.pi ** 2 / (2 * L * L) for n in (1, 2, 3)])


# =============================================================================
# COMUNICACION CON EL ORGANISMO
# =============================================================================
def peticion_get(endpoint: str) -> dict:
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def peticion_post(endpoint: str, data: dict | None = None) -> tuple[int, dict]:
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    req = urllib.request.Request(url, data=json.dumps(data or {}).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")

    def parsear(content: str) -> dict:
        try:
            return json.loads(content) if content else {}
        except json.JSONDecodeError:
            return {"raw": content}

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
    """Espera a que el organismo vuelva al estado 'reposo' (True) o detecte 'fallo' / timeout (False)."""
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
    """Como esperar_reposo, pero primero espera a que el organismo ARRANQUE (salga de 'reposo' o
    cambie su ultimo_resultado). Evita leer un resultado antiguo por una condicion de carrera."""
    t0 = time.time()
    while time.time() - t0 < gracia_s:
        est = estado_seguro()
        if est.get("organismo_estado") != "reposo":
            break
        if previo is not None and (est.get("ultimo_resultado") or "") != previo:
            break
        time.sleep(0.5)
    return esperar_reposo(timeout_s)


# =============================================================================
# VERIFICACION INDEPENDIENTE DE RESPUESTAS
# =============================================================================
_NUM_RE = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?")
_FRAC_RE = re.compile(r"(-?\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)")
_LATEX_FRAC_RE = re.compile(r"\\frac\{(-?\d+)\}\{(\d+)\}")
_MILES_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+)(?!\d)")


def extraer_numeros(texto: str) -> list[float]:
    t = (texto or "").replace("\u2212", "-")
    nums: list[float] = []
    for m in _MILES_RE.finditer(t):
        nums.append(float(m.group(1).replace(",", "")))
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
    for a, b in _FRAC_RE.findall(t) + _LATEX_FRAC_RE.findall(t):
        if float(b) != 0:
            nums.append(float(a) / float(b))
    return nums


def _coincide(nums: list[float], esperado, tol: float) -> bool:
    alternativas = esperado if isinstance(esperado, (list, tuple)) else (esperado,)
    for a in alternativas:
        margen = 1e-6 if isinstance(a, int) else max(tol * abs(a), tol)  # enteros: exactos
        if any(abs(x - a) <= margen for x in nums):
            return True
    return False


def verificar(texto: str, esperados: list, tol: float) -> tuple[bool, list]:
    nums = extraer_numeros(texto)
    faltan = [e for e in esperados if not _coincide(nums, e, tol)]
    return (not faltan), faltan


# =============================================================================
# ENTRENADOR
# =============================================================================
@dataclass
class Resultado:
    nivel: str
    tema: str
    variante: int
    ronda: int
    tipo: str  # "leccion" | "repaso"
    prompt: str
    esperados: list
    ok: bool = False
    intentos: int = 0
    duracion: float = 0.0
    faltantes: list = field(default_factory=list)
    respuesta: str = ""


class Entrenador:
    def __init__(self, args):
        self.a = args
        self.contador = 0
        self.ultima_poda = 0
        self.resumen_niveles: list[dict] = []
        self.repasos: list[tuple[str, int, int]] = []
        self.log_path: Path | None = None
        if not args.dry_run:
            Path(args.log_dir).mkdir(parents=True, exist_ok=True)
            self.log_path = Path(args.log_dir) / f"curriculum_{dt.datetime.now():%Y%m%d_%H%M%S}.jsonl"

    # ---------------------------------------------------------------- conexion
    def conectar(self) -> bool:
        try:
            est = peticion_get("estado")
            if not est.get("gpu_online"):
                print("⚠️ Aviso: La GPU no responde todavía en el servidor.")
            print(f"➜ Organismo conectado. Órganos activos: {len(est.get('organos', []))}")
            return True
        except Exception as e:
            print(f"❌ Error: No se puede conectar a {API_BASE}. Asegúrate de ejecutar 'exe_servidor.py'. Error: {e}")
            return False

    def enviar(self, prompt: str) -> tuple[bool, str, float]:
        if not esperar_reposo(30):
            print("   ⏳ Esperando a que el organismo vuelva a reposo (reset)...")
            peticion_post("reset")
            time.sleep(2)
        previo = estado_seguro().get("ultimo_resultado") or ""
        status, _ = peticion_post("prompt", {"prompt": prompt})
        for _ in range(3):
            if status != 409:
                break
            print("   ⚠️ Organismo ocupado. Reintentando...")
            esperar_reposo(30)
            status, _ = peticion_post("prompt", {"prompt": prompt})
        if not 200 <= status < 300:
            return False, f"❌ Error HTTP {status} al enviar el prompt", 0.0
        t0 = time.time()
        ok = esperar_ciclo(self.a.timeout, previo=previo)
        return ok, estado_seguro().get("ultimo_resultado") or "", time.time() - t0

    # ------------------------------------------------------------------ retos
    def resolver(self, rt: Reto, variante: int, ronda: int, tipo: str = "leccion") -> Resultado:
        rng = random.Random(f"{self.a.semilla}|{rt.tema}|{variante}|{ronda}")
        prompt, esperados = rt.generar(rng)
        res = Resultado(rt.nivel, rt.tema, variante, ronda, tipo, prompt, esperados)
        etiqueta = "🔁 Repaso" if tipo == "repaso" else "🧪 Tema"
        print(f"\n   {etiqueta}: {rt.tema} (variante {variante}{', refuerzo ' + str(ronda) if ronda else ''})")
        print(f"      Directiva: \"{prompt[:90]}{'...' if len(prompt) > 90 else ''}\"")

        if self.a.dry_run:
            print(f"      Esperado : {[round(e, 6) if isinstance(e, float) else e for e in esperados]}")
            res.ok = True
            return res

        for intento in range(1, self.a.reintentos + 2):
            ok_ciclo, texto, dur = self.enviar(prompt if intento == 1 else prompt + PISTA)
            res.intentos, res.respuesta = intento, texto
            res.duracion += dur
            verificado, res.faltantes = verificar(texto, esperados, rt.tol)
            res.ok = ok_ciclo and verificado and "❌ Error" not in texto
            if res.ok:
                break
            if intento <= self.a.reintentos:
                print(f"      ↻ Intento {intento} fallido (faltan {res.faltantes}). Reintentando con pista...")

        if res.ok:
            print(f"      ✅ Superado en {res.duracion:.1f}s ({res.intentos} intento/s)")
            for linea in [l for l in res.respuesta.splitlines() if l.strip()][-3:]:
                print(f"         {linea[:110]}")
        else:
            print(f"      ❌ Fallo tras {res.duracion:.1f}s. Faltan en la respuesta: {res.faltantes}")
            print(f"         {res.respuesta[:120].strip()}...")

        self.registrar(res)
        self.contador += 1
        if self.a.poda and self.contador % self.a.poda == 0:
            self.podar()
        time.sleep(1)
        return res

    def registrar(self, res: Resultado):
        if self.log_path:
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": dt.datetime.now().isoformat(timespec="seconds"), **asdict(res)},
                                    ensure_ascii=False, default=str) + "\n")

    # ------------------------------------------------------------ homeostasis
    def podar(self):
        if self.a.dry_run or self.contador == self.ultima_poda:
            return
        self.ultima_poda = self.contador
        print("\n   🧹 [HOMEOSTASIS]: Ejecutando Poda Tisular Consciente...")
        esperar_reposo(20)
        status, _ = peticion_post("remodelar")
        if status != 200:
            print(f"   ⚠️ La poda no se pudo iniciar (HTTP {status}).")
            return
        if esperar_ciclo(180, gracia_s=5):
            diag = estado_seguro()
            total = sum(len(t.get("celulas", [])) for o in diag.get("organos", []) for t in o.get("tejidos", []))
            print(f"   ✨ Poda completada. Anatomía consolidada en {total} célula(s) versátiles.")
        else:
            print("   ⚠️ Aviso: Tiempo de espera de poda excedido.")
        time.sleep(3)

    # ---------------------------------------------------------------- niveles
    def ejecutar_nivel(self, clave: str, retos: list[Reto]) -> tuple[float, float]:
        final: dict[tuple[str, int], Resultado] = {}
        primera = 0.0
        for ronda in range(self.a.refuerzos + 1):
            if ronda == 0:
                pendientes = [(rt, v) for rt in retos for v in range(self.a.variantes)]
            else:
                pendientes = [(rt, v) for rt in retos for v in range(self.a.variantes)
                              if not final[(rt.tema, v)].ok]
                if not pendientes:
                    break
                print(f"\n   🔧 REFUERZO {ronda}/{self.a.refuerzos}: {len(pendientes)} reto(s) con nuevas variantes")
            for rt, v in pendientes:
                final[(rt.tema, v)] = self.resolver(rt, v, ronda)
            tasa = sum(r.ok for r in final.values()) / len(final)
            if ronda == 0:
                primera = tasa
            print(f"\n   📊 Dominio del nivel tras ronda {ronda}: {tasa * 100:.1f}% (umbral {self.a.umbral * 100:.0f}%)")
            if tasa >= self.a.umbral:
                break
        tasa_final = sum(r.ok for r in final.values()) / len(final)
        self.resumen_niveles.append({"nivel": NOMBRE_NIVEL[clave], "retos": len(final), "primera": primera,
                                     "final": tasa_final, "ok": sum(r.ok for r in final.values())})
        return primera, tasa_final

    def repasar(self, clave_actual: str, previos: list[Reto]):
        if not self.a.repaso or not previos:
            return
        rng = random.Random(f"{self.a.semilla}|repaso|{clave_actual}")
        muestra = rng.sample(previos, min(self.a.repaso, len(previos)))
        print(f"\n   🔁 REPASO ESPACIADO: {len(muestra)} tema(s) de niveles anteriores")
        oks = [self.resolver(rt, 1000 + i, 0, tipo="repaso").ok for i, rt in enumerate(muestra)]
        self.repasos.append((NOMBRE_NIVEL[clave_actual], sum(oks), len(oks)))

    def niveles_seleccionados(self):
        claves = [k for k, _ in NIVELES]
        if self.a.nivel:
            return [n for n in NIVELES if n[0] == self.a.nivel]
        if self.a.desde:
            return NIVELES[claves.index(self.a.desde):]
        return NIVELES

    def entrenar(self):
        print("=" * 72)
        print("🎓 INICIANDO CURRÍCULO AUTÓNOMO DE ESPECIALIZACIÓN MATEMÁTICA (v2)")
        print("=" * 72)
        if not self.a.dry_run and not self.conectar():
            return
        niveles = self.niveles_seleccionados()
        total_retos = sum(1 for r in CURRICULUM if r.nivel in {k for k, _ in niveles})
        print(f"➜ Niveles: {len(niveles)} | Temas: {total_retos} | Variantes por tema: {self.a.variantes}")
        print(f"➜ Semilla: {self.a.semilla} (usa --semilla {self.a.semilla} para reproducir)")
        print(f"➜ Umbral de dominio: {self.a.umbral * 100:.0f}% | Refuerzos: {self.a.refuerzos} | "
              f"Reintentos por reto: {self.a.reintentos}")
        print(f"➜ Homeostasis: poda cada {self.a.poda or '—'} retos y al terminar cada nivel")
        if self.log_path:
            print(f"➜ Registro: {self.log_path}")
        print("-" * 72)

        try:
            for i, (clave, nombre) in enumerate(niveles):
                retos = [r for r in CURRICULUM if r.nivel == clave]
                print(f"\n{'=' * 56}\n📘 ASCENSO DE CURSO: {nombre.upper()}  ({len(retos)} temas)\n{'=' * 56}")
                _, dominio = self.ejecutar_nivel(clave, retos)
                self.podar()
                previos = [r for r in CURRICULUM if r.nivel in {k for k, _ in niveles[:i]}]
                self.repasar(clave, previos)
                if dominio < self.a.umbral and not self.a.continuar and not self.a.dry_run:
                    print(f"\n⛔ Dominio insuficiente en {nombre} ({dominio * 100:.1f}% < {self.a.umbral * 100:.0f}%). "
                          f"Se detiene el ascenso. Usa --continuar para forzarlo.")
                    break
        except KeyboardInterrupt:
            print("\n⏹️ Interrumpido por el usuario. Resumen parcial:")
        self.resumen()

    def resumen(self):
        print("\n" + "=" * 72)
        print("🎓 RESUMEN DEL ORGANISMO MATEMÁTICO")
        print("=" * 72)
        if self.a.dry_run:
            print("   (dry-run: no se ha evaluado nada)")
            return
        for n in self.resumen_niveles:
            print(f"   {n['nivel']:<18} 1er intento {n['primera'] * 100:5.1f}% | tras refuerzo {n['final'] * 100:5.1f}% "
                  f"| {n['ok']}/{n['retos']} retos")
        if self.repasos:
            ok = sum(r[1] for r in self.repasos); tot = sum(r[2] for r in self.repasos)
            print(f"   Retención (repaso espaciado): {ok}/{tot} = {ok / tot * 100:.1f}%")
        tot = sum(n["retos"] for n in self.resumen_niveles)
        if tot:
            ok = sum(n["ok"] for n in self.resumen_niveles)
            print(f"   ➜ Éxitos: {ok} | Fallos: {tot - ok}")
            print(f"   ➜ Tasa de Competencia: {ok / tot * 100:.1f}%")
        print("=" * 72)


# =============================================================================
# CLI
# =============================================================================
def listar():
    for clave, nombre in NIVELES:
        temas = [r.tema for r in CURRICULUM if r.nivel == clave]
        print(f"\n{nombre}  ({len(temas)} temas)")
        for t in temas:
            print(f"   • {t}")
    print(f"\nTotal: {len(CURRICULUM)} temas")


def main():
    claves = [k for k, _ in NIVELES]
    p = argparse.ArgumentParser(description="Currículo Autónomo de Matemáticas (de lo simple a lo complejo).")
    p.add_argument("--nivel", choices=claves, help="Ejecutar solo este nivel.")
    p.add_argument("--desde", choices=claves, help="Ejecutar desde este nivel hacia arriba.")
    p.add_argument("--poda", type=int, default=3, help="Homeostasis cada N retos (0 = solo entre niveles).")
    p.add_argument("--variantes", type=int, default=1, help="Variantes generadas por tema (default: 1).")
    p.add_argument("--reintentos", type=int, default=1, help="Reintentos por reto fallido (default: 1).")
    p.add_argument("--umbral", type=float, default=0.7, help="Dominio mínimo para ascender, 0-1 (default: 0.7).")
    p.add_argument("--refuerzos", type=int, default=1, help="Rondas de refuerzo por nivel (default: 1).")
    p.add_argument("--repaso", type=int, default=2, help="Temas de niveles previos a repasar tras cada nivel.")
    p.add_argument("--continuar", action="store_true", help="Ascender aunque no se alcance el umbral.")
    p.add_argument("--timeout", type=int, default=360, help="Segundos máximos por reto (default: 360).")
    p.add_argument("--semilla", type=int, default=int(time.time()) % 1_000_000, help="Semilla de los generadores.")
    p.add_argument("--log-dir", default="logs/curriculum", help="Directorio del registro JSONL.")
    p.add_argument("--dry-run", action="store_true", help="Muestra prompts y respuestas esperadas sin usar el servidor.")
    p.add_argument("--listar", action="store_true", help="Lista niveles y temas y sale.")
    args = p.parse_args()

    if args.listar:
        listar()
        return
    Entrenador(args).entrenar()


if __name__ == "__main__":
    main()