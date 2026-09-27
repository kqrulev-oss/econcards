#!/usr/bin/env python3
"""Прототип генераторов карточек по физике и химии (исследование, в сборку не входит).

Запуск:
  python3 tools/research/gen_phys_chem.py            # самопроверка: 200 вариантов на тип
  python3 tools/research/gen_phys_chem.py --n 500    # другое число вариантов
  python3 tools/research/gen_phys_chem.py --sample 3 # показать по 3 карточки каждого типа (JSON)

Каждый генератор — функция rng -> карточка в формате наборов (tools/build_packs.py):
  {id, t, k, q, a, o?, e, gen:{type, exam, task}}
  k = 'num'   — числовой ответ (строка, запятая как в бланке);
  k = 'one'   — один вариант из o = [{id, t}];
  k = 'many'  — несколько вариантов, a = [id, ...] («выберите все верные», порядок не важен);
  k = 'match' — соответствие, o = {left, right}, a = {левый id: правый id}.

Константы и округления — как в КИМ ФИПИ: g = 10 м/с², R = 8,31, e = 1,6·10⁻¹⁹ Кл,
Ar — целые, кроме Cl = 35,5; Vm = 22,4 л/моль (н. у.).
Физические задачи подбирают параметры так, чтобы ответ был конечной десятичной дробью
(как в части 1 ЕГЭ), химические — округляют до указанной точности.
"""
import argparse
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter
from fractions import Fraction as Fr

# ---------------------------------------------------------------- общие помощники

G = 10


from pc_core import *  # noqa: F401,F403 — общие помощники вынесены в pc_core.py
from pc_core import Retry, card, fmt, exact, num, ru, distractors, with_options, AR, parse_formula, molar, balance, check_balance, eq_str, pretty



# ================================================================= ФИЗИКА

# ---------- ЕГЭ 1. Кинематика (коды 1.1.5, 1.1.6)

def ph_kin(rng):
    v = rng.randrange(3)
    if v == 0:
        a = Fr(rng.choice([-4, -3, -2, -1, 1, 2, 3, 4, 5]), rng.choice([1, 2]))
        dt = rng.choice([2, 4, 5, 10])
        v0 = rng.randrange(-10, 21, 2)
        ts = [0, dt, 2 * dt, 3 * dt]
        vs = [v0 + a * t for t in ts]
        if any(x.denominator != 1 for x in vs):
            raise Retry
        tab = '; '.join(f't = {t} с — {ru(x)} м/с' for t, x in zip(ts, vs))
        q = f'Проекция скорости тела на ось Ox меняется со временем так: {tab}. Определите проекцию ускорения тела ax. Ответ дайте в м/с² с учётом знака.'
        ans = exact(a)
        e = f'ax = Δvx/Δt = (({ru(vs[1])}) − ({ru(vs[0])})) / {dt} = {ans} м/с².'
        wrong = [fmt(-a), fmt(abs(a)), fmt(vs[3] / ts[3]) if ts[3] else None]
    elif v == 1:
        x0 = rng.randrange(-20, 21)
        v0 = rng.randrange(-8, 9)
        a = rng.choice([-6, -4, -2, 2, 4, 6, 8])
        t = rng.randrange(1, 7)
        vt = v0 + a * t
        sign = lambda n, first=False: (f'− {abs(n)}' if n < 0 else (f'{n}' if first else f'+ {n}'))
        q = (f'Координата тела меняется по закону x = {x0} {sign(v0)}t {sign(a // 2)}t² (все величины в СИ). '
             f'Чему равна проекция скорости тела vx в момент t = {t} с? Ответ дайте в м/с.')
        ans = exact(vt)
        e = f'Сравниваем с x = x0 + v0t + at²/2: v0 = {v0} м/с, a = {a} м/с². vx = v0 + at = {v0} + ({a})·{t} = {ans} м/с.'
        wrong = [fmt(v0 + a // 2 * t), fmt(x0 + v0 * t + a // 2 * t * t), fmt(v0)]
    else:
        v0 = rng.randrange(0, 21, 2)
        a = Fr(rng.choice([1, 2, 3, 4, 5, 6]), rng.choice([1, 2]))
        t = rng.randrange(2, 11)
        s = v0 * t + a * t * t / 2
        ans = exact(s, 1)
        if ans is None or s > 1000:
            raise Retry
        q = f'Тело, имея начальную скорость {v0} м/с, движется прямолинейно с постоянным ускорением {ru(a)} м/с², направленным вдоль скорости. Какой путь пройдёт тело за {t} с? Ответ дайте в метрах.'
        e = f's = v0t + at²/2 = {v0}·{t} + {ru(a)}·{t}²/2 = {ans} м.'
        wrong = [fmt(v0 * t + a * t * t), fmt(a * t * t / 2), fmt(v0 * t)]
    if ans is None:
        raise Retry
    return card('ph-kin', 'ЕГЭ', 1, 'phys-ege-1', q, ans, e, extra={'wrong': wrong})


# ---------- ЕГЭ 2. Динамика (1.2.4, 1.2.6–1.2.8)

def ph_dyn(rng):
    v = rng.randrange(4)
    if v == 0:
        k1, k2 = rng.sample([100, 200, 250, 300, 400, 500, 600, 800, 1000], 2)
        x2 = rng.choice([1, 2, 3, 4, 5])
        F = Fr(k2 * x2, 100)
        q = (f'Две лёгкие пружины жёсткостью k1 = {k1} Н/м и k2 = {k2} Н/м соединены последовательно; левый конец первой закреплён, '
             f'к правому концу второй приложена горизонтальная сила F, система покоится. Удлинение второй пружины {x2} см. Найдите модуль силы F. Ответ дайте в ньютонах.')
        ans = exact(F)
        e = f'При последовательном соединении сила в обеих пружинах одна и та же: F = k2·x2 = {k2}·{ru(Fr(x2, 100))} = {ans} Н.'
        wrong = [fmt(Fr(k1 * x2, 100)), fmt(Fr((k1 + k2) * x2, 100)), fmt(k2 * x2)]
    elif v == 1:
        m = rng.choice([1, 2, 3, 4, 5, 10, 20])
        mu = Fr(rng.choice([1, 2, 3, 4, 5]), 10)
        a = Fr(rng.choice([0, 1, 2, 3, 4, 5]), rng.choice([1, 2]))
        F = m * a + mu * m * G
        how = 'движется равномерно' if a == 0 else f'движется с ускорением {ru(a)} м/с²'
        q = f'Брусок массой {m} кг тянут по горизонтальной поверхности горизонтальной силой. Коэффициент трения {ru(mu)}, брусок {how}. Найдите модуль силы. Ответ дайте в ньютонах.'
        ans = exact(F)
        e = f'Второй закон Ньютона: F − μmg = ma, F = m(a + μg) = {m}·({ru(a)} + {ru(mu)}·10) = {ans} Н.'
        wrong = [fmt(m * a), fmt(m * a - mu * m * G), fmt(mu * m * G)]
    elif v == 2:
        F0 = rng.choice([4, 6, 8, 9, 12, 16, 18, 24, 36, 48, 72])
        n = rng.choice([2, 3])
        km = rng.choice([1, 2, 3])
        F1 = Fr(F0 * km, n * n)
        q = f'Два тела притягиваются друг к другу с силой {F0} мкН. Какой станет сила притяжения, если расстояние между центрами тел увеличить в {n} раза, а массу одного из тел увеличить в {km} раз(а)? Ответ дайте в мкН.'
        if km == 1:
            q = f'Два тела притягиваются друг к другу с силой {F0} мкН. Какой станет сила притяжения, если расстояние между центрами тел увеличить в {n} раза? Ответ дайте в мкН.'
        ans = exact(F1)
        e = f'F = Gm1m2/r²: F1 = F0·{km}/{n}² = {ans} мкН.'
        wrong = [fmt(Fr(F0 * km, n)), fmt(F0 * km * n * n), fmt(Fr(F0, n * n))]
    else:
        m = rng.choice([50, 60, 70, 80])
        a = rng.choice([1, 2, 3, 4])
        up = rng.random() < 0.5
        P = m * (G + a) if up else m * (G - a)
        d = 'вверх' if up else 'вниз'
        q = f'Человек массой {m} кг стоит в лифте, который движется с ускорением {a} м/с², направленным {d}. С какой силой человек давит на пол лифта? Ответ дайте в ньютонах.'
        ans = exact(P)
        e = f'N − mg = ±ma ⇒ P = N = m(g {"+" if up else "−"} a) = {m}·{G + a if up else G - a} = {ans} Н.'
        wrong = [fmt(m * G), fmt(m * (G - a) if up else m * (G + a)), fmt(m * a)]
    if ans is None:
        raise Retry
    return card('ph-dyn', 'ЕГЭ', 2, 'phys-ege-2', q, ans, e, extra={'wrong': wrong})


# ---------- ЕГЭ 3. Законы сохранения (1.4.1–1.4.8)

def ph_cons(rng):
    v = rng.randrange(4)
    if v == 0:
        s = rng.choice([10, 20, 25, 40, 50, 80, 100, 200])
        Fk = rng.choice([5, 8, 10, 12, 15, 20, 25, 40, 50])
        A = s * Fk
        q = f'Сани равномерно тянут по горизонтальному участку пути длиной {s} м горизонтальной силой, работа которой {A} Дж. Какова сила трения, действующая на сани? Ответ дайте в ньютонах.'
        ans = exact(Fr(A, s))
        e = f'Движение равномерное ⇒ F = Fтр. A = F·s ⇒ Fтр = {A}/{s} = {ans} Н.'
        wrong = [fmt(A * s), fmt(Fr(A, s * G)), '0']
    elif v == 1:
        m = Fr(rng.choice([1, 2, 4, 5, 8, 10, 20, 50]), rng.choice([1, 10]))
        vv = rng.choice([2, 3, 4, 5, 6, 10, 20])
        E = m * vv * vv / 2
        q = f'Тело массой {ru(m)} кг движется со скоростью {vv} м/с. Чему равна его кинетическая энергия? Ответ дайте в джоулях.'
        ans = exact(E)
        e = f'Ek = mv²/2 = {ru(m)}·{vv}²/2 = {ans} Дж.'
        wrong = [fmt(m * vv * vv), fmt(m * vv / 2), fmt(m * vv)]
    elif v == 2:
        m1 = rng.choice([1, 2, 3, 4, 5])
        m2 = rng.choice([1, 2, 3, 4, 5, 6])
        v1 = rng.choice([2, 3, 4, 5, 6, 8, 10])
        u = Fr(m1 * v1, m1 + m2)
        q = f'Тележка массой {m1} кг, движущаяся со скоростью {v1} м/с, сталкивается с неподвижной тележкой массой {m2} кг и сцепляется с ней. С какой скоростью движутся тележки после сцепки? Ответ дайте в м/с.'
        ans = exact(u)
        if ans is None:
            raise Retry
        e = f'Закон сохранения импульса: m1v1 = (m1 + m2)u ⇒ u = {m1}·{v1}/{m1 + m2} = {ans} м/с.'
        wrong = [fmt(Fr(m1 * v1, m2)), fmt(Fr(v1, 2)), fmt(v1)]
    else:
        h = rng.choice([5, 20, 45, 80, 125, 180])
        vv = math.isqrt(2 * G * h)
        q = f'Мяч свободно падает без начальной скорости с высоты {h} м. Какова его скорость у самой земли? Сопротивлением воздуха пренебречь. Ответ дайте в м/с.'
        ans = exact(vv)
        e = f'mgh = mv²/2 ⇒ v = √(2gh) = √(2·10·{h}) = {ans} м/с.'
        wrong = [fmt(2 * G * h), fmt(G * h), fmt(math.sqrt(G * h), 1)]
    if ans is None:
        raise Retry
    return card('ph-cons', 'ЕГЭ', 3, 'phys-ege-3', q, ans, e, extra={'wrong': wrong})


# ---------- ЕГЭ 4. Статика, колебания (1.3.x, 1.5.x)

def ph_stat_osc(rng):
    v = rng.randrange(4)
    if v == 0:
        n = rng.choice([2, 3, 4, 5])
        q = f'Груз на лёгкой пружине совершает гармонические колебания. Во сколько раз нужно увеличить массу груза, чтобы период колебаний увеличился в {n} раза?'
        ans = str(n * n)
        e = f'T = 2π√(m/k) ⇒ T ~ √m. Чтобы T выросло в {n} раза, массу увеличивают в {n}² = {ans} раз.'
        wrong = [str(n), str(2 * n), fmt(math.sqrt(n), 2)]
    elif v == 1:
        n = rng.choice([4, 9, 16, 25])
        q = f'Длину нити математического маятника увеличили в {n} раз. Во сколько раз увеличился период его малых колебаний?'
        ans = str(math.isqrt(n))
        e = f'T = 2π√(l/g) ⇒ T ~ √l, √{n} = {ans}.'
        wrong = [str(n), str(n // 2), str(n * n)]
    elif v == 2:
        V = Fr(rng.choice([1, 2, 4, 5, 8, 10, 20, 50]), rng.choice([1000, 10000]))
        liq = rng.choice([('воду', 1000), ('керосин', 800), ('спирт', 800)])
        part = rng.choice([Fr(1), Fr(1, 2)])
        F = liq[1] * G * V * part
        how = 'полностью' if part == 1 else 'наполовину'
        q = f'Тело объёмом {ru(V * 10 ** 6)} см³ {how} погружено в {liq[0]} (плотность {liq[1]} кг/м³). Найдите действующую на него силу Архимеда. Ответ дайте в ньютонах.'
        ans = exact(F)
        e = f'FА = ρжgVпогр = {liq[1]}·10·{ru(V * part)} = {ans} Н.'
        wrong = [fmt(F * 2 if part != 1 else F / 2), fmt(liq[1] * V * part), fmt(F * 10)]
    else:
        m1 = rng.choice([1, 2, 3, 4, 5, 6])
        l1 = rng.choice([10, 20, 30, 40, 60])
        l2 = rng.choice([10, 15, 20, 30, 40, 60, 80])
        m2 = Fr(m1 * l1, l2)
        if l1 == l2:
            raise Retry
        q = f'На лёгком рычаге в равновесии слева на расстоянии {l1} см от оси висит груз массой {m1} кг, справа — груз на расстоянии {l2} см от оси. Какова масса правого груза? Ответ дайте в кг.'
        ans = exact(m2)
        e = f'Правило моментов: m1l1 = m2l2 ⇒ m2 = {m1}·{l1}/{l2} = {ans} кг.'
        wrong = [fmt(Fr(m1 * l2, l1)), str(m1), fmt(Fr(m1 * l1, l2) * G)]
    if ans is None:
        raise Retry
    return card('ph-stat', 'ЕГЭ', 4, 'phys-ege-4', q, ans, e, extra={'wrong': wrong})


# ---------- ЕГЭ 7. МКТ (2.1.8–2.1.12)

def ph_mkt(rng):
    v = rng.randrange(3)
    if v == 0:
        kp = Fr(rng.choice([1, 2, 3, 4]), rng.choice([1, 2]))
        kv = Fr(rng.choice([1, 2, 3, 4]), rng.choice([1, 2, 3]))
        kt = kp * kv
        if kt <= 1 or kp == 1 and kv == 1:
            raise Retry
        dp = 'не изменилось' if kp == 1 else (f'увеличилось в {ru(kp)} раза' if kp > 1 else f'уменьшилось в {ru(1 / kp)} раза')
        dv = 'не изменился' if kv == 1 else (f'увеличился в {ru(kv)} раза' if kv > 1 else f'уменьшился в {ru(1 / kv)} раза')
        q = f'Давление постоянной массы идеального газа {dp}, а объём {dv}. Во сколько раз увеличилась абсолютная температура газа?'
        ans = exact(kt)
        e = f'pV/T = const ⇒ T2/T1 = (p2/p1)(V2/V1) = {ru(kp)}·{ru(kv)} = {ans}.'
        wrong = [fmt(kp / kv, 2), fmt(kv / kp, 2), fmt(kp + kv)]
    elif v == 1:
        T1 = rng.choice([200, 250, 300, 400, 500, 600])
        n = rng.choice([Fr(3, 2), 2, 3, Fr(1, 2), Fr(2, 3)])
        T2 = T1 * n
        if T2.denominator != 1 if isinstance(T2, Fr) else False:
            raise Retry
        q = f'Абсолютную температуру идеального одноатомного газа изменили с {T1} К до {ru(T2)} К. Во сколько раз изменилась средняя кинетическая энергия теплового движения его молекул? Ответ — отношение новой энергии к старой.'
        ans = exact(Fr(T2) / T1)
        e = f'Ēк = 3kT/2 ~ T ⇒ отношение {ru(T2)}/{T1} = {ans}.'
        wrong = [fmt(Fr(T1) / T2, 2), fmt(math.sqrt(Fr(T2) / T1), 2), fmt(Fr(T2) / T1 * Fr(3, 2), 2)]
    else:
        nu = Fr(rng.choice([1, 2, 3, 4, 5]), rng.choice([1, 2, 10]))
        T = rng.choice([200, 250, 300, 400, 500])
        V = rng.choice([Fr(1, 100), Fr(2, 100), Fr(5, 1000), Fr(1, 10)])
        p = nu * Fr(831, 100) * T / V
        ans = fmt(p / 1000, 1)
        q = f'В сосуде объёмом {ru(V * 1000)} л находится {ru(nu)} моль идеального газа при температуре {T} К. Каково давление газа? Ответ дайте в кПа, округлив до десятых. (R = 8,31 Дж/(моль·К))'
        e = f'pV = νRT ⇒ p = νRT/V = {ru(nu)}·8,31·{T}/{ru(V)} Па ≈ {ans} кПа.'
        wrong = [fmt(p, 0), fmt(nu * Fr(831, 100) * T / (V * 1000), 2), fmt(p / 1000 * 1000 / 273, 1)]
    if ans is None:
        raise Retry
    return card('ph-mkt', 'ЕГЭ', 7, 'phys-ege-7', q, ans, e, extra={'wrong': wrong})


# ---------- ЕГЭ 8. Термодинамика (2.2.4–2.2.10)

def ph_thermo(rng):
    v = rng.randrange(4)
    if v == 0:
        p = rng.choice([100, 150, 200, 250, 300, 400, 500])
        V1 = rng.choice([1, 2, 3, 4, 5, 6])
        dV = rng.choice([1, 2, 3, 4, 5])
        A = p * dV
        q = f'Идеальный газ изобарно расширяется при давлении {p} кПа от {V1} л до {V1 + dV} л. Какую работу совершает газ? Ответ дайте в джоулях.'
        ans = exact(A)
        e = f'A = pΔV = {p}·10³ Па · {dV}·10⁻³ м³ = {ans} Дж.'
        wrong = [fmt(p * (V1 + dV)), fmt(A * 1000), fmt(Fr(p * dV, 1000))]
    elif v == 1:
        Q = rng.choice([100, 200, 300, 400, 500, 600, 800, 1000])
        A = rng.choice([x for x in (50, 100, 150, 200, 250, 300, 400) if x < Q])
        q = f'Газ получил количество теплоты {Q} Дж и совершил работу {A} Дж. На сколько увеличилась его внутренняя энергия? Ответ дайте в джоулях.'
        ans = exact(Q - A)
        e = f'Первый закон термодинамики: Q = ΔU + A ⇒ ΔU = {Q} − {A} = {ans} Дж.'
        wrong = [str(Q + A), str(A - Q), str(Q)]
    elif v == 2:
        T1 = rng.choice([400, 500, 600, 800, 1000, 1200])
        T2 = rng.choice([t for t in (200, 250, 273, 300, 350, 400, 500) if t < T1])
        eta = (1 - Fr(T2, T1)) * 100
        ans = exact(eta, 1)
        if ans is None:
            raise Retry
        q = f'Температура нагревателя идеальной тепловой машины {T1} К, холодильника {T2} К. Найдите КПД машины. Ответ дайте в процентах.'
        e = f'η = 1 − Tх/Tн = 1 − {T2}/{T1} = {ans} %.'
        wrong = [fmt(Fr(T2, T1) * 100, 1), fmt(Fr(T1 - T2, T2) * 100, 1), fmt(eta / 100, 2)]
    else:
        sub = rng.choice([('воды', 4200), ('алюминия', 920), ('меди', 400), ('железа', 460), ('свинца', 140)])
        m = Fr(rng.choice([1, 2, 5, 10, 20]), rng.choice([1, 10]))
        dt = rng.choice([5, 10, 20, 25, 50, 80])
        Q = sub[1] * m * dt
        q = f'Какое количество теплоты нужно, чтобы нагреть {ru(m)} кг {sub[0]} на {dt} °C? Удельная теплоёмкость {sub[1]} Дж/(кг·°C). Ответ дайте в кДж.'
        ans = exact(Q / 1000)
        e = f'Q = cmΔt = {sub[1]}·{ru(m)}·{dt} = {ru(Q)} Дж = {ans} кДж.'
        wrong = [fmt(Q), fmt(sub[1] * m / 1000), fmt(Q / 1000 / dt, 2)]
    if ans is None:
        raise Retry
    return card('ph-thermo', 'ЕГЭ', 8, 'phys-ege-8', q, ans, e, extra={'wrong': wrong})


# ---------- ЕГЭ 11. Электростатика и постоянный ток (3.1.2, 3.2.x)

def ph_el(rng):
    v = rng.randrange(4)
    if v == 0:
        F0 = rng.choice([10, 20, 30, 40, 50, 60, 80, 90, 120])
        kq = rng.choice([1, 2, 3, 4])
        kr = rng.choice([1, 2, 3])
        if kq == 1 and kr == 1:
            raise Retry
        F1 = Fr(F0 * kq, kr * kr)
        parts = []
        if kq > 1:
            parts.append(f'заряд одного из тел увеличить в {kq} раза')
        if kr > 1:
            parts.append(f'расстояние между ними увеличить в {kr} раза')
        q = f'Два неподвижных точечных заряда взаимодействуют с силой {F0} мН. Какой станет сила взаимодействия, если {" и ".join(parts)}? Ответ дайте в мН.'
        ans = exact(F1)
        e = f'Закон Кулона F = k|q1q2|/r²: F1 = {F0}·{kq}/{kr}² = {ans} мН.'
        wrong = [fmt(Fr(F0 * kq, kr)), fmt(F0 * kq * kr * kr), fmt(F0 * kq * kq)]
    elif v == 1:
        rs = [rng.choice([1, 2, 3, 4, 5, 6, 10, 12, 15, 20]) for _ in range(rng.choice([2, 3]))]
        par = rng.random() < 0.5
        R = 1 / sum(Fr(1, r) for r in rs) if par else sum(rs)
        how = 'параллельно' if par else 'последовательно'
        q = f'Резисторы сопротивлением {", ".join(map(str, rs[:-1]))} и {rs[-1]} Ом соединены {how}. Каково общее сопротивление участка? Ответ дайте в омах.'
        ans = exact(R)
        e = ('1/R = ' + ' + '.join(f'1/{r}' for r in rs) if par else 'R = ' + ' + '.join(map(str, rs))) + f' ⇒ R = {ans or ""} Ом.'
        wrong = [fmt(sum(rs) if par else 1 / sum(Fr(1, r) for r in rs), 2), fmt(Fr(sum(rs), len(rs)), 2), fmt(max(rs))]
    elif v == 2:
        E = rng.choice([3, 4, 6, 9, 12, 24])
        r = Fr(rng.choice([1, 2, 5]), rng.choice([1, 2, 10]))
        R = rng.choice([1, 2, 3, 4, 5, 6, 10, 11])
        I = E / (R + r)
        q = f'Источник тока с ЭДС {E} В и внутренним сопротивлением {ru(r)} Ом замкнут на резистор {R} Ом. Найдите силу тока в цепи. Ответ дайте в амперах.'
        ans = exact(I)
        e = f'Закон Ома для полной цепи: I = ε/(R + r) = {E}/({R} + {ru(r)}) = {ans or ""} А.'
        wrong = [fmt(Fr(E, R), 2), fmt(E / r, 2), fmt(E * (R + r), 2)]
    else:
        U = rng.choice([2, 4, 6, 12, 20, 24, 36, 110, 220])
        R = rng.choice([2, 4, 5, 10, 20, 40, 50, 100, 200])
        P = Fr(U * U, R)
        q = f'Какая мощность выделяется в резисторе сопротивлением {R} Ом, если напряжение на нём {U} В? Ответ дайте в ваттах.'
        ans = exact(P, 1)
        e = f'P = U²/R = {U}²/{R} = {ans or ""} Вт.'
        wrong = [fmt(Fr(U, R), 2), fmt(U * R), fmt(Fr(U * U, R * R), 2)]
    if ans is None:
        raise Retry
    return card('ph-el', 'ЕГЭ', 11, 'phys-ege-11', q, ans, e, extra={'wrong': wrong})


# ---------- ЕГЭ 12. Магнитное поле, индукция (3.3.x, 3.4.x)

def ph_mag(rng):
    v = rng.randrange(3)
    if v == 0:
        B = Fr(rng.choice([1, 2, 4, 5]), rng.choice([10, 100]))
        I = rng.choice([1, 2, 4, 5, 10, 20])
        L = Fr(rng.choice([10, 20, 25, 50, 100]), 100)
        ang = rng.choice([90, 30])
        s = 1 if ang == 90 else Fr(1, 2)
        F = B * I * L * s
        q = f'Прямой проводник длиной {ru(L * 100)} см с током {I} А находится в однородном магнитном поле с индукцией {ru(B)} Тл под углом {ang}° к линиям индукции. Найдите модуль силы Ампера. Ответ дайте в ньютонах.'
        ans = exact(F, 3)
        e = f'FA = BIl·sinα = {ru(B)}·{I}·{ru(L)}·{ru(s)} = {ans or ""} Н.'
        wrong = [fmt(B * I * L), fmt(B * I * L * 100), fmt(B * I * L * Fr(1, 2) if ang == 90 else B * I * L * Fr(866, 1000), 3)]
    elif v == 1:
        dF = Fr(rng.choice([1, 2, 3, 4, 5, 6, 8, 10, 12]), rng.choice([1, 10]))
        dt = Fr(rng.choice([1, 2, 4, 5, 10, 20, 50]), 100)
        N = rng.choice([1, 1, 10, 20, 50, 100])
        eps = N * dF / 1000 / dt
        coil = 'Магнитный поток через контур' if N == 1 else f'Магнитный поток через каждый виток катушки из {N} витков'
        q = f'{coil} равномерно уменьшился на {ru(dF)} мВб за {ru(dt)} с. Найдите модуль ЭДС индукции в {"контуре" if N == 1 else "катушке"}. Ответ дайте в вольтах.'
        ans = exact(eps, 3) if eps <= 100 else None
        e = f'|ε| = N·ΔΦ/Δt = {N}·{ru(dF / 1000)}/{ru(dt)} = {ans or ""} В.'
        wrong = [fmt(dF / 1000 / dt, 3), fmt(N * dF / dt, 2), fmt(N * dF / 1000 * dt, 5)]
    else:
        L = Fr(rng.choice([1, 2, 4, 5, 10, 20, 50]), rng.choice([10, 100, 1000]))
        I = rng.choice([1, 2, 3, 4, 5, 10])
        W = L * I * I / 2
        q = f'Через катушку индуктивностью {ru(L * 1000)} мГн течёт ток {I} А. Чему равна энергия магнитного поля катушки? Ответ дайте в мДж.'
        ans = exact(W * 1000, 2) if W <= 5 else None
        e = f'W = LI²/2 = {ru(L)}·{I}²/2 = {ans or ""} мДж.'
        wrong = [fmt(L * I * I * 1000), fmt(L * I / 2 * 1000), fmt(L * I * I / 2)]
    if ans is None:
        raise Retry
    return card('ph-mag', 'ЕГЭ', 12, 'phys-ege-12', q, ans, e, extra={'wrong': wrong})


# ---------- ЕГЭ 13. ЭМ-колебания, оптика (3.5.1, 3.6.x)

def ph_opt(rng):
    v = rng.randrange(4)
    if v == 0:
        d = rng.choice([2, 3, 4, 5, 6])
        s = rng.choice([x for x in (1, 2, 3) if x < d])
        q = f'Предмет стоит перед плоским зеркалом на расстоянии {d} клеток. Его придвинули к зеркалу на {s} клетки. На сколько клеток уменьшилось расстояние между предметом и его изображением?'
        ans = str(2 * s)
        e = f'Изображение симметрично предмету: расстояние предмет — изображение 2d. Уменьшилось на 2·{s} = {ans}.'
        wrong = [str(s), str(2 * (d - s)), str(d - s)]
    elif v == 1:
        F = rng.choice([5, 10, 12, 15, 20, 24, 30])
        d = rng.choice([x for x in range(F + 1, 4 * F + 1)])
        f = Fr(d * F, d - F)
        ans = exact(f, 1)
        if ans is None or f > 300:
            raise Retry
        q = f'Предмет находится на расстоянии {d} см от тонкой собирающей линзы с фокусным расстоянием {F} см. На каком расстоянии от линзы получится изображение? Ответ дайте в сантиметрах.'
        e = f'1/F = 1/d + 1/f ⇒ f = dF/(d − F) = {d}·{F}/{d - F} = {ans} см.'
        wrong = [fmt(Fr(d * F, d + F), 1), fmt(d - F), fmt(d + F)]
    elif v == 2:
        kL = rng.choice([1, 4, 9, Fr(1, 4)])
        kC = rng.choice([1, 4, 9, 16, Fr(1, 4), Fr(1, 9)])
        if kL == 1 and kC == 1:
            raise Retry
        k = Fr(kL * kC)
        rt = Fr(math.isqrt(k.numerator), math.isqrt(k.denominator))
        if rt * rt != k:
            raise Retry
        parts = []
        if kL != 1:
            parts.append(f'индуктивность катушки {"увеличить в " + ru(kL) if kL > 1 else "уменьшить в " + ru(1 / Fr(kL))} раз(а)')
        if kC != 1:
            parts.append(f'ёмкость конденсатора {"увеличить в " + ru(kC) if kC > 1 else "уменьшить в " + ru(1 / Fr(kC))} раз(а)')
        q = f'Во сколько раз изменится период свободных колебаний в идеальном колебательном контуре, если {" и ".join(parts)}? Ответ — отношение нового периода к старому.'
        ans = exact(rt)
        e = f'T = 2π√(LC) ⇒ T2/T1 = √({ru(kL)}·{ru(kC)}) = {ans or ""}.'
        wrong = [fmt(k, 2), fmt(1 / rt, 2), fmt(1 / k, 3)]
    else:
        nu = rng.choice([1, 2, 3, 5, 6, 10, 15, 30, 50, 60, 100, 150, 300])
        lam = Fr(300, nu)
        q = f'Радиостанция работает на частоте {nu} МГц. Какова длина излучаемой волны? Скорость света 3·10⁸ м/с. Ответ дайте в метрах.'
        ans = exact(lam)
        e = f'λ = c/ν = 3·10⁸/({nu}·10⁶) = {ans or ""} м.'
        wrong = [fmt(Fr(nu, 300), 3), fmt(300 * nu), fmt(Fr(3, nu), 3)]
    if ans is None:
        raise Retry
    return card('ph-opt', 'ЕГЭ', 13, 'phys-ege-13', q, ans, e, extra={'wrong': wrong})


# ---------- ЕГЭ 16. Ядерная физика (4.2.1, 4.3.1–4.3.4)

ELEM_Z = {1: 'H', 2: 'He', 3: 'Li', 4: 'Be', 5: 'B', 6: 'C', 7: 'N', 8: 'O', 9: 'F', 10: 'Ne', 11: 'Na', 12: 'Mg', 13: 'Al',
          14: 'Si', 15: 'P', 16: 'S', 17: 'Cl', 18: 'Ar', 19: 'K', 20: 'Ca', 26: 'Fe', 27: 'Co', 28: 'Ni', 29: 'Cu', 30: 'Zn',
          36: 'Kr', 38: 'Sr', 39: 'Y', 53: 'I', 54: 'Xe', 55: 'Cs', 56: 'Ba', 81: 'Tl', 82: 'Pb', 83: 'Bi', 84: 'Po', 86: 'Rn',
          88: 'Ra', 90: 'Th', 91: 'Pa', 92: 'U', 93: 'Np', 94: 'Pu'}

# Реальные нуклиды (A, Z) и их распады: α — (A−4, Z−2), β⁻ — (A, Z+1)
NUCLIDES_ALPHA = [(238, 92), (234, 92), (235, 92), (226, 88), (222, 86), (210, 84), (218, 84), (230, 90), (232, 90), (239, 94), (241, 95)]
NUCLIDES_BETA = [(234, 90), (234, 91), (14, 6), (60, 27), (90, 38), (131, 53), (137, 55), (3, 1), (40, 19), (239, 93), (210, 83), (214, 82)]
ELEM_Z[95] = 'Am'
# Реакции с лёгкими частицами (все проверяются на баланс A и Z при самопроверке)
PARTICLES = {'n': (1, 0), 'p': (1, 1), 'α': (4, 2), 'd': (2, 1), 'γ': (0, 0), 'e': (0, -1)}
NUC_REACTIONS = [  # (мишень, снаряд, продукт, частица)
    ((14, 7), 'α', (17, 8), 'p'), ((9, 4), 'α', (12, 6), 'n'), ((27, 13), 'α', (30, 15), 'n'),
    ((7, 3), 'p', (4, 2), 'α'), ((6, 3), 'n', (3, 1), 'α'), ((10, 5), 'n', (7, 3), 'α'),
    ((14, 7), 'n', (14, 6), 'p'), ((2, 1), 'd', (3, 2), 'n'), ((3, 1), 'd', (4, 2), 'n'),
    ((6, 3), 'd', (4, 2), 'α'), ((27, 13), 'n', (24, 11), 'α'), ((23, 11), 'd', (24, 11), 'p'),
    ((19, 9), 'p', (16, 8), 'α'), ((11, 5), 'p', (8, 4), 'α'), ((26, 12), 'd', (24, 11), 'α'),
    ((59, 27), 'n', (60, 27), 'γ'), ((9, 4), 'd', (10, 5), 'n'), ((12, 6), 'd', (13, 7), 'n'),
]
PNAME = {'n': 'нейтрон', 'p': 'протон', 'α': 'α-частица', 'd': 'дейтрон', 'γ': 'γ-квант', 'e': 'электрон'}


def nucl(a, z):
    return f'{ELEM_Z[z]}-{a} (Z = {z})'


def ph_nuc(rng):
    v = rng.randrange(4)
    if v == 0:
        a, z = rng.choice(NUCLIDES_ALPHA + NUCLIDES_BETA)
        what = rng.choice(['нейтронов', 'протонов', 'нуклонов'])
        ans = str({'нейтронов': a - z, 'протонов': z, 'нуклонов': a}[what])
        q = f'Сколько {what} содержит ядро {ELEM_Z[z]}-{a}, если его зарядовое число Z = {z}?'
        e = f'A = {a} — нуклоны, Z = {z} — протоны, N = A − Z = {a - z} — нейтроны.'
        wrong = [str(a - z), str(z), str(a), str(a + z)]
        wrong = [w for w in wrong if w != ans]
        return card('ph-nuc', 'ЕГЭ', 16, 'phys-ege-16', q, ans, e, extra={'wrong': wrong})
    if v == 1:
        tgt, pr, prod, out = rng.choice(NUC_REACTIONS)
        ask = rng.choice(['A', 'Z'])
        a, z = prod
        ans = str(a if ask == 'A' else z)
        q = (f'В ядерной реакции ядро {nucl(*tgt)} захватывает частицу «{PNAME[pr]}», в результате образуются ядро X и частица «{PNAME[out]}». '
             f'Каково {"массовое" if ask == "A" else "зарядовое"} число ядра X?')
        e = (f'Сохраняются A и Z: A = {tgt[0]} + {PARTICLES[pr][0]} − {PARTICLES[out][0]} = {a}; Z = {tgt[1]} + {PARTICLES[pr][1]} − {PARTICLES[out][1]} = {z}. X — {ELEM_Z[z]}-{a}.')
        wrong = [str(tgt[0] + PARTICLES[pr][0]), str(z if ask == 'A' else a), str(tgt[1])]
        return card('ph-nuc', 'ЕГЭ', 16, 'phys-ege-16', q, ans, e, extra={'wrong': wrong, 'check_nuc': [tgt, pr, prod, out]})
    if v == 2:
        a, z = rng.choice(NUCLIDES_ALPHA)
        na = rng.randrange(1, 5)
        nb = rng.randrange(0, 5)
        A, Z = a - 4 * na, z - 2 * na + nb
        if Z not in ELEM_Z:
            raise Retry
        ask = rng.choice(['A', 'Z'])
        ans = str(A if ask == 'A' else Z)
        q = f'Ядро {ELEM_Z[z]}-{a} (Z = {z}) испытало {na} α-распад(а) и {nb} β⁻-распад(а). Каково {"массовое" if ask == "A" else "зарядовое"} число получившегося ядра?'
        e = f'α: A − 4, Z − 2; β⁻: A не меняется, Z + 1. A = {a} − 4·{na} = {A}; Z = {z} − 2·{na} + {nb} = {Z}.'
        wrong = [str(a - 2 * na), str(z - 2 * na - nb), str(A - 4 * nb)]
        return card('ph-nuc', 'ЕГЭ', 16, 'phys-ege-16', q, ans, e, extra={'wrong': wrong})
    n = rng.choice([1, 2, 3, 4])
    T = rng.choice([2, 3, 5, 8, 10, 12, 15, 20, 30])
    m0 = rng.choice([16, 32, 40, 64, 80, 96, 120, 160, 200, 400, 800])
    m = Fr(m0, 2 ** n)
    ans = exact(m, 2)
    if ans is None:
        raise Retry
    q = f'Период полураспада радиоактивного изотопа {T} сут. Какая масса изотопа останется нераспавшейся через {n * T} сут, если сначала его было {m0} мг? Ответ дайте в миллиграммах.'
    e = f'Прошло {n} период(а): m = m0/2^{n} = {m0}/{2 ** n} = {ans} мг.'
    wrong = [fmt(m0 - m, 2), fmt(Fr(m0, 2 * n), 2), fmt(Fr(m0, n + 1), 2)]
    return card('ph-nuc', 'ЕГЭ', 16, 'phys-ege-16', q, ans, e, extra={'wrong': wrong})


# ---------- ЕГЭ 6, 10, 15, 17. «Как изменятся величины» — вычисляем знак изменения по модели

CHANGE = {'1': 'увеличится', '2': 'уменьшится', '3': 'не изменится'}

# Модель: параметры, что меняем, величины (функции от параметров), текст ситуации
MODELS = [
    {'task': 6, 'text': 'Груз на пружине совершает гармонические колебания с неизменной амплитудой.',
     'base': {'m': 1.0, 'k': 100.0, 'A': 0.1},
     'change': {'m': 'Массу груза увеличили', 'k': 'Пружину заменили на более жёсткую'},
     'qty': {'период колебаний': lambda p: 2 * math.pi * math.sqrt(p['m'] / p['k']),
             'частота колебаний': lambda p: 1 / (2 * math.pi * math.sqrt(p['m'] / p['k'])),
             'полная механическая энергия груза': lambda p: p['k'] * p['A'] ** 2 / 2,
             'максимальная скорость груза': lambda p: p['A'] * math.sqrt(p['k'] / p['m'])}},
    {'task': 6, 'text': 'Спутник движется по круговой орбите вокруг Земли.',
     'base': {'r': 7e6, 'm': 1000.0},
     'change': {'r': 'Спутник перевели на круговую орбиту большего радиуса', 'm': 'Масса спутника оказалась больше (орбита та же)'},
     'qty': {'скорость спутника': lambda p: math.sqrt(4e14 / p['r']),
             'период обращения': lambda p: 2 * math.pi * p['r'] / math.sqrt(4e14 / p['r']),
             'центростремительное ускорение': lambda p: 4e14 / p['r'] ** 2,
             'сила притяжения к Земле': lambda p: 4e14 * p['m'] / p['r'] ** 2}},
    {'task': 6, 'text': 'Тело бросают горизонтально с некоторой высоты. Сопротивлением воздуха пренебречь.',
     'base': {'v': 5.0, 'h': 20.0},
     'change': {'v': 'Начальную скорость увеличили (высота та же)', 'h': 'Высоту броска увеличили (скорость та же)'},
     'qty': {'время полёта': lambda p: math.sqrt(2 * p['h'] / 10),
             'дальность полёта': lambda p: p['v'] * math.sqrt(2 * p['h'] / 10),
             'ускорение тела': lambda p: 10.0}},
    {'task': 10, 'text': 'Идеальный газ постоянной массы находится в сосуде под поршнем.',
     'base': {'V': 1.0, 'T': 300.0, 'nu': 1.0},
     'change': {'V': 'Газ изотермически сжали', 'T': 'Газ изохорно нагрели'},
     'qty': {'давление газа': lambda p: p['nu'] * 8.31 * p['T'] / p['V'],
             'концентрация молекул': lambda p: p['nu'] / p['V'],
             'внутренняя энергия газа': lambda p: 1.5 * p['nu'] * 8.31 * p['T'],
             'средняя кинетическая энергия молекул': lambda p: 1.5 * 1.38e-23 * p['T'],
             'плотность газа': lambda p: p['nu'] * 0.004 / p['V']}},
    {'task': 15, 'text': 'Резистор подключён к источнику тока с ЭДС ε и внутренним сопротивлением r.',
     'base': {'R': 5.0, 'E': 12.0, 'r': 1.0},
     'change': {'R': 'Резистор заменили на резистор большего сопротивления', 'E': 'Источник заменили на источник с большей ЭДС и тем же r'},
     'qty': {'сила тока в цепи': lambda p: p['E'] / (p['R'] + p['r']),
             'напряжение на резисторе': lambda p: p['E'] * p['R'] / (p['R'] + p['r']),
             'тепловая мощность внутри источника': lambda p: (p['E'] / (p['R'] + p['r'])) ** 2 * p['r'],
             'внутреннее сопротивление источника': lambda p: p['r']}},
    {'task': 15, 'text': 'Плоский воздушный конденсатор зарядили и отключили от источника.',
     'base': {'d': 1.0, 'S': 1.0, 'q': 1.0},
     'change': {'d': 'Расстояние между пластинами увеличили', 'S': 'Пластины раздвинули в стороны, уменьшив площадь перекрытия'},
     'qty': {'ёмкость конденсатора': lambda p: p['S'] / p['d'],
             'заряд конденсатора': lambda p: p['q'],
             'напряжение между пластинами': lambda p: p['q'] * p['d'] / p['S'],
             'энергия конденсатора': lambda p: p['q'] ** 2 * p['d'] / p['S'] / 2}},
    {'task': 15, 'text': 'Плоский воздушный конденсатор подключён к источнику постоянного напряжения и не отключается от него.',
     'base': {'d': 1.0, 'S': 1.0, 'U': 1.0},
     'change': {'d': 'Расстояние между пластинами увеличили', 'S': 'Площадь пластин увеличили'},
     'qty': {'ёмкость конденсатора': lambda p: p['S'] / p['d'],
             'заряд конденсатора': lambda p: p['S'] / p['d'] * p['U'],
             'напряжение между пластинами': lambda p: p['U'],
             'напряжённость поля между пластинами': lambda p: p['U'] / p['d']}},
    {'task': 15, 'text': 'Предмет находится перед тонкой собирающей линзой дальше её двойного фокуса.',
     'base': {'d': 3.0, 'F': 1.0},
     'change': {'d': 'Предмет придвинули к линзе, но он остался дальше двойного фокуса'},
     'delta': {'d': 0.7},
     'qty': {'расстояние от линзы до изображения': lambda p: p['d'] * p['F'] / (p['d'] - p['F']),
             'размер изображения': lambda p: p['F'] / (p['d'] - p['F']),
             'оптическая сила линзы': lambda p: 1 / p['F']}},
    {'task': 17, 'text': 'Металлическую пластину освещают монохроматическим светом, наблюдается фотоэффект.',
     'base': {'nu': 1.0e15, 'I': 1.0, 'A': 3.0e-19},
     'change': {'nu': 'Частоту света увеличили, интенсивность прежняя', 'I': 'Интенсивность света увеличили, частота прежняя'},
     'qty': {'максимальная кинетическая энергия фотоэлектронов': lambda p: 6.6e-34 * p['nu'] - p['A'],
             'задерживающее напряжение': lambda p: (6.6e-34 * p['nu'] - p['A']) / 1.6e-19,
             'работа выхода': lambda p: p['A'],
             'длина волны падающего света': lambda p: 3e8 / p['nu']}},
    {'task': 17, 'text': 'Имеется образец радиоактивного изотопа.',
     'base': {'N': 1e20, 'T': 10.0},
     'change': {'N': 'Взяли образец того же изотопа с бóльшим числом ядер'},
     'qty': {'период полураспада': lambda p: p['T'],
             'число ядер, распавшихся за 1 сутки': lambda p: p['N'] * (1 - 2 ** (-1 / p['T'])),
             'доля ядер, распавшихся за время T': lambda p: 0.5}},
]


def ph_change(rng):
    mdl = rng.choice(MODELS)
    par = rng.choice(list(mdl['change']))
    names = rng.sample(list(mdl['qty']), 2)
    p0 = dict(mdl['base'])
    p1 = dict(p0)
    p1[par] = p0[par] * 1.5 if par not in mdl.get('delta', {}) else p0[par] * mdl['delta'][par]
    if par == 'S' and 'уменьш' in mdl['change'][par]:
        p1[par] = p0[par] * 0.6
    if par == 'V' and 'сжали' in mdl['change'][par]:
        p1[par] = p0[par] * 0.6
    ans = {}
    for i, n in enumerate(names):
        a, b = mdl['qty'][n](p0), mdl['qty'][n](p1)
        ans['АБ'[i]] = '3' if math.isclose(a, b, rel_tol=1e-9) else ('1' if b > a else '2')
    q = f'{mdl["text"]} {mdl["change"][par]}. Как изменятся величины?'
    o = {'left': [{'id': 'А', 't': names[0]}, {'id': 'Б', 't': names[1]}],
         'right': [{'id': k, 't': v} for k, v in CHANGE.items()]}
    e = '; '.join(f'{n} — {CHANGE[ans["АБ"[i]]]}' for i, n in enumerate(names)) + '. Ответ ЕГЭ: ' + ans['А'] + ans['Б'] + '.'
    return card('ph-change', 'ЕГЭ', mdl['task'], f'phys-ege-{mdl["task"]}', q, ans, e, k='match', o=o,
                extra={'answer_ege': ans['А'] + ans['Б']})


# ---------- ЕГЭ 20. Планирование опыта: выбрать две установки

EXPERIMENTS = [
    ('зависимость периода колебаний математического маятника от длины нити',
     {'длина нити, см': [40, 60, 80, 100], 'масса груза, г': [50, 100, 200], 'материал груза': ['сталь', 'латунь', 'алюминий']}, 'длина нити, см'),
    ('зависимость ёмкости плоского конденсатора от расстояния между пластинами',
     {'расстояние, мм': [0.2, 0.3, 0.4, 0.5], 'площадь пластины, см²': [10, 20, 30], 'диэлектрик': ['слюда', 'парафин', 'воздух']}, 'расстояние, мм'),
    ('зависимость сопротивления проводника от его длины',
     {'длина, м': [1, 2, 3, 4], 'площадь сечения, мм²': [0.5, 1, 2], 'материал': ['медь', 'алюминий', 'никелин']}, 'длина, м'),
    ('зависимость силы Архимеда от плотности жидкости',
     {'жидкость': ['вода', 'масло', 'керосин', 'спирт'], 'объём тела, см³': [10, 20, 40], 'материал тела': ['сталь', 'медь', 'алюминий']}, 'жидкость'),
    ('зависимость количества теплоты, нужного для нагревания, от массы вещества',
     {'масса, г': [100, 200, 300, 400], 'вещество': ['вода', 'масло', 'спирт'], 'изменение температуры, °C': [10, 20, 30]}, 'масса, г'),
    ('зависимость силы трения скольжения от материала поверхности',
     {'поверхность': ['дерево', 'стекло', 'резина', 'сталь'], 'масса бруска, г': [100, 200, 400], 'площадь опоры, см²': [20, 40, 60]}, 'поверхность'),
]


def ph_exp(rng):
    goal, attrs, target = rng.choice(EXPERIMENTS)
    keys = list(attrs)
    others = [k for k in keys if k != target]
    base = {k: rng.choice(attrs[k]) for k in keys}
    alt = dict(base)
    alt[target] = rng.choice([x for x in attrs[target] if x != base[target]])
    rows = [base, alt]
    tries = 0
    while len(rows) < 5:
        tries += 1
        if tries > 500:
            raise Retry
        r = {k: rng.choice(attrs[k]) for k in keys}
        if any(r == x for x in rows):
            continue
        # новая строка не должна давать ещё одну правильную пару
        bad = False
        for x in rows:
            same_other = all(r[k] == x[k] for k in others)
            if same_other and r[target] != x[target]:
                bad = True
        if not bad:
            rows.append(r)
    rng.shuffle(rows)
    i1, i2 = rows.index(base) + 1, rows.index(alt) + 1
    table = ' | '.join(keys)
    lines = '; '.join(f'№{i + 1}: ' + ', '.join(f'{ru(r[k]) if not isinstance(r[k], str) else r[k]}' for k in keys) for i, r in enumerate(rows))
    q = f'Ученик исследует {goal}. Какие две установки ему нужно взять? Столбцы: {table}. {lines}.'
    o = [{'id': str(i + 1), 't': f'№{i + 1}'} for i in range(5)]
    a = sorted([str(i1), str(i2)])
    e = f'Нужны установки, где отличается только исследуемая величина ({target}), а остальное одинаково: №{a[0]} и №{a[1]}.'
    return card('ph-exp', 'ЕГЭ', 20, 'phys-ege-20', q, a, e, k='many', o=o, extra={'answer_ege': ''.join(a)})


# ---------- ОГЭ физика: плотность, давление, работа/мощность (переиспользуют те же приёмы)

def ph_oge_mech(rng):
    v = rng.randrange(3)
    if v == 0:
        m = rng.choice([54, 78, 89, 112, 135, 156, 178, 270, 390, 445, 540])
        mats = {2700: 'алюминий', 7800: 'сталь', 8900: 'медь', 11300: 'свинец', 1000: 'вода', 800: 'керосин'}
        rho = rng.choice([2700, 7800, 8900])
        V = Fr(m, 1) / Fr(rho, 1000)
        ans = exact(V, 1)
        if ans is None:
            raise Retry
        q = f'Какой объём имеет деталь массой {m} г из вещества плотностью {rho} кг/м³ ({mats[rho]})? Ответ дайте в см³.'
        e = f'V = m/ρ = {m} г / {ru(Fr(rho, 1000))} г/см³ = {ans} см³.'
        wrong = [fmt(m * Fr(rho, 1000), 1), fmt(Fr(m, rho), 3), fmt(V * 1000, 0)]
    elif v == 1:
        F = rng.choice([100, 200, 400, 500, 600, 800, 1000, 1200])
        S = rng.choice([Fr(1, 100), Fr(2, 100), Fr(4, 100), Fr(5, 100), Fr(1, 10), Fr(2, 10)])
        p = F / S
        q = f'Ящик весом {F} Н стоит на полу, площадь опоры {ru(S * 10000)} см². Какое давление ящик оказывает на пол? Ответ дайте в кПа.'
        ans = exact(p / 1000, 2)
        e = f'p = F/S = {F}/{ru(S)} = {ru(p)} Па = {ans or ""} кПа.'
        wrong = [fmt(F * S, 2), fmt(F / (S * 10000), 2), fmt(p, 0)]
    else:
        m = rng.choice([10, 20, 50, 100, 200, 500])
        h = rng.choice([2, 3, 5, 10, 12, 15, 20])
        t = rng.choice([2, 4, 5, 10, 20, 25, 50])
        P = Fr(m * G * h, t)
        q = f'Подъёмник равномерно поднимает груз массой {m} кг на высоту {h} м за {t} с. Какую мощность он развивает? Ответ дайте в ваттах.'
        ans = exact(P, 1)
        e = f'N = A/t = mgh/t = {m}·10·{h}/{t} = {ans or ""} Вт.'
        wrong = [fmt(m * G * h), fmt(Fr(m * h, t), 1), fmt(m * G * h * t)]
    if ans is None:
        raise Retry
    return card('ph-oge-mech', 'ОГЭ', 'расчёт', 'phys-oge-calc', q, ans, e, extra={'wrong': wrong})


# ================================================================= ХИМИЯ


# Библиотека реакций: (реагенты, продукты, русское описание). Коэффициенты считает balance().
REACTIONS = [
    (['Al', 'O2'], ['Al2O3'], 'горение алюминия'),
    (['Fe', 'Cl2'], ['FeCl3'], 'железо с хлором'),
    (['P', 'O2'], ['P2O5'], 'горение фосфора'),
    (['CH4', 'O2'], ['CO2', 'H2O'], 'горение метана'),
    (['C2H6', 'O2'], ['CO2', 'H2O'], 'горение этана'),
    (['C3H8', 'O2'], ['CO2', 'H2O'], 'горение пропана'),
    (['C2H5OH', 'O2'], ['CO2', 'H2O'], 'горение этанола'),
    (['C6H12O6', 'O2'], ['CO2', 'H2O'], 'окисление глюкозы'),
    (['Zn', 'HCl'], ['ZnCl2', 'H2'], 'цинк с соляной кислотой'),
    (['Al', 'HCl'], ['AlCl3', 'H2'], 'алюминий с соляной кислотой'),
    (['Mg', 'H2SO4'], ['MgSO4', 'H2'], 'магний с разбавленной серной кислотой'),
    (['Fe', 'H2SO4'], ['FeSO4', 'H2'], 'железо с разбавленной серной кислотой'),
    (['Na', 'H2O'], ['NaOH', 'H2'], 'натрий с водой'),
    (['Ca', 'H2O'], ['Ca(OH)2', 'H2'], 'кальций с водой'),
    (['CaCO3', 'HCl'], ['CaCl2', 'CO2', 'H2O'], 'мрамор с соляной кислотой'),
    (['Na2CO3', 'HCl'], ['NaCl', 'CO2', 'H2O'], 'сода с соляной кислотой'),
    (['Na2SO3', 'HCl'], ['NaCl', 'SO2', 'H2O'], 'сульфит натрия с соляной кислотой'),
    (['NaOH', 'H2SO4'], ['Na2SO4', 'H2O'], 'нейтрализация серной кислоты щёлочью'),
    (['Ca(OH)2', 'HNO3'], ['Ca(NO3)2', 'H2O'], 'нейтрализация азотной кислоты'),
    (['BaCl2', 'H2SO4'], ['BaSO4', 'HCl'], 'осаждение сульфата бария'),
    (['AgNO3', 'NaCl'], ['AgCl', 'NaNO3'], 'осаждение хлорида серебра'),
    (['CuSO4', 'NaOH'], ['Cu(OH)2', 'Na2SO4'], 'осаждение гидроксида меди(II)'),
    (['FeCl3', 'NaOH'], ['Fe(OH)3', 'NaCl'], 'осаждение гидроксида железа(III)'),
    (['CaCO3'], ['CaO', 'CO2'], 'обжиг известняка'),
    (['KClO3'], ['KCl', 'O2'], 'разложение бертолетовой соли'),
    (['H2O2'], ['H2O', 'O2'], 'разложение пероксида водорода'),
    (['KMnO4'], ['K2MnO4', 'MnO2', 'O2'], 'разложение перманганата калия'),
    (['Cu(OH)2'], ['CuO', 'H2O'], 'разложение гидроксида меди(II)'),
    (['Fe2O3', 'H2'], ['Fe', 'H2O'], 'восстановление оксида железа(III) водородом'),
    (['CuO', 'H2'], ['Cu', 'H2O'], 'восстановление оксида меди(II) водородом'),
    (['Fe2O3', 'CO'], ['Fe', 'CO2'], 'восстановление оксида железа(III) угарным газом'),
    (['N2', 'H2'], ['NH3'], 'синтез аммиака'),
    (['SO2', 'O2'], ['SO3'], 'окисление сернистого газа'),
    (['NH3', 'O2'], ['NO', 'H2O'], 'каталитическое окисление аммиака'),
    (['CuS', 'O2'], ['CuO', 'SO2'], 'обжиг сульфида меди(II)'),
    (['FeS2', 'O2'], ['Fe2O3', 'SO2'], 'обжиг пирита'),
    (['Cu', 'HNO3'], ['Cu(NO3)2', 'NO2', 'H2O'], 'медь с концентрированной азотной кислотой'),
    (['Cu', 'HNO3'], ['Cu(NO3)2', 'NO', 'H2O'], 'медь с разбавленной азотной кислотой'),
    (['Al', 'NaOH', 'H2O'], ['Na[Al(OH)4]', 'H2'], 'алюминий со щёлочью'),
    (['C2H4', 'O2'], ['CO2', 'H2O'], 'горение этилена'),
    (['C2H2', 'O2'], ['CO2', 'H2O'], 'горение ацетилена'),
    (['CaC2', 'H2O'], ['Ca(OH)2', 'C2H2'], 'карбид кальция с водой'),
    (['Al4C3', 'H2O'], ['Al(OH)3', 'CH4'], 'карбид алюминия с водой'),
    (['NH4Cl', 'Ca(OH)2'], ['CaCl2', 'NH3', 'H2O'], 'получение аммиака в лаборатории'),
    (['Zn', 'CuSO4'], ['ZnSO4', 'Cu'], 'вытеснение меди цинком'),
]
# [Al(OH)4]⁻ разбирает parse_formula через скобки; квадратные скобки уберём
REACTIONS = [([s.replace('[', '(').replace(']', ')') for s in l], [s.replace('[', '(').replace(']', ')') for s in r], d) for l, r, d in REACTIONS]




def ch_balance(rng):
    lhs, rhs, desc = rng.choice(REACTIONS)
    kl, kr = balance(lhs, rhs)
    assert check_balance(lhs, rhs, kl, kr)
    sk = ' + '.join(map(pretty, lhs)) + ' → ' + ' + '.join(map(pretty, rhs))
    v = rng.randrange(2)
    if v == 0:
        ans = str(sum(kl) + sum(kr))
        q = f'Расставьте коэффициенты в схеме реакции ({desc}): {sk}. Чему равна сумма всех коэффициентов?'
        wrong = [str(sum(kl)), str(sum(kr)), str(sum(kl) + sum(kr) + 1)]
    else:
        species = lhs + rhs
        ks = kl + kr
        i = rng.randrange(len(species))
        ans = str(ks[i])
        q = f'Расставьте коэффициенты в схеме реакции ({desc}): {sk}. Какой коэффициент стоит перед {pretty(species[i])}?'
        wrong = [str(ks[i] + 1), str(max(1, ks[i] - 1)), str(ks[i] * 2)]
    e = 'Уравнение: ' + pretty(eq_str(lhs, rhs, kl, kr)) + '. Число атомов каждого элемента слева и справа совпадает.'
    return card('ch-balance', 'ОГЭ/8 кл.', 'баланс', 'chem-balance', q, ans, e,
                extra={'wrong': wrong, 'eq': [lhs, rhs, kl, kr]})


# ---------- ОГЭ / 8 класс: массовая доля элемента, количество вещества

COMPOUNDS = {
    'H2O': 'вода', 'CO2': 'углекислый газ', 'NaCl': 'хлорид натрия', 'H2SO4': 'серная кислота', 'HNO3': 'азотная кислота',
    'CaCO3': 'карбонат кальция', 'NaOH': 'гидроксид натрия', 'Fe2O3': 'оксид железа(III)', 'CuO': 'оксид меди(II)',
    'Al2O3': 'оксид алюминия', 'NH3': 'аммиак', 'CH4': 'метан', 'SO2': 'оксид серы(IV)', 'SO3': 'оксид серы(VI)',
    'KMnO4': 'перманганат калия', 'CuSO4': 'сульфат меди(II)', 'Na2CO3': 'карбонат натрия', 'MgO': 'оксид магния',
    'P2O5': 'оксид фосфора(V)', 'Ca(OH)2': 'гидроксид кальция', 'KNO3': 'нитрат калия', 'Na2SO4': 'сульфат натрия',
    'AgNO3': 'нитрат серебра', 'BaCl2': 'хлорид бария', 'ZnO': 'оксид цинка', 'FeS': 'сульфид железа(II)',
    'Fe3O4': 'железная окалина', 'NH4NO3': 'нитрат аммония', 'CaCl2': 'хлорид кальция', 'KCl': 'хлорид калия',
    'Ca3(PO4)2': 'фосфат кальция', 'Al2(SO4)3': 'сульфат алюминия', 'C2H5OH': 'этанол', 'C6H12O6': 'глюкоза',
    'CuSO4·5H2O': 'медный купорос',
}


def ch_wfrac(rng):
    f = rng.choice(list(COMPOUNDS))
    comp = parse_formula(f)
    el = rng.choice(sorted(comp))
    M = molar(f)
    w = Fr(AR[el] * comp[el]) / M * 100
    dec = rng.choice([0, 1])
    prec = 'целых' if dec == 0 else 'десятых'
    ans = fmt(w, dec)
    q = f'Вычислите массовую долю {el} в веществе {pretty(f)} ({COMPOUNDS[f]}). Ответ дайте в процентах с точностью до {prec}.'
    e = f'M({pretty(f)}) = {ru(M)} г/моль; ω({el}) = {comp[el]}·{ru(AR[el])}/{ru(M)}·100 % ≈ {ans} %.'
    wrong = [fmt(Fr(AR[el]) / M * 100, dec), fmt(Fr(comp[el], sum(comp.values())) * 100, dec), fmt(100 - w, dec)]
    return card('ch-wfrac', 'ОГЭ', 'расчёт', 'chem-oge-calc', q, ans, e, extra={'wrong': wrong})


def ch_mole(rng):
    f = rng.choice(list(COMPOUNDS))
    M = molar(f)
    v = rng.randrange(3)
    gas = f in ('CO2', 'NH3', 'CH4', 'SO2', 'H2O') and f != 'H2O'
    if v == 2 and not gas:
        v = 0
    n = Fr(rng.choice([1, 2, 3, 4, 5, 10, 15, 20, 25]), rng.choice([10, 100, 1]))
    if v == 0:
        m = n * M
        q = f'Какое количество вещества содержится в {ru(m)} г {pretty(f)}? Ответ дайте в молях.'
        ans = exact(n, 3)
        e = f'n = m/M = {ru(m)}/{ru(M)} = {ans} моль.'
        wrong = [fmt(m * M, 1), fmt(M / m, 3), fmt(n * 2, 3)]
    elif v == 1:
        m = n * M
        ans = exact(m, 2)
        q = f'Какова масса {ru(n)} моль {pretty(f)}? Ответ дайте в граммах.'
        e = f'm = nM = {ru(n)}·{ru(M)} = {ans} г.'
        wrong = [fmt(n / M, 4), fmt(M, 1), fmt(n * M * 2, 2)]
    else:
        Vv = n * Fr(224, 10)
        ans = exact(Vv, 3)
        q = f'Какой объём (н. у.) занимают {ru(n)} моль {pretty(f)}? Ответ дайте в литрах.'
        e = f'V = n·Vm = {ru(n)}·22,4 = {ans} л.'
        wrong = [fmt(n / Fr(224, 10), 3), fmt(n * M, 2), fmt(n * Fr(224, 10) * 2, 3)]
    if ans is None:
        raise Retry
    return card('ch-mole', '8 кл./ОГЭ', 'расчёт', 'chem-8-mole', q, ans, e, extra={'wrong': wrong})


# ---------- ЕГЭ 26. Растворы (массовая доля)

SOLUTES = {'NaCl': 'хлорида натрия', 'KNO3': 'нитрата калия', 'Na2SO4': 'сульфата натрия', 'NaOH': 'гидроксида натрия',
           'KCl': 'хлорида калия', 'CuSO4': 'сульфата меди(II)', 'Na2CO3': 'карбоната натрия', 'glucose': 'глюкозы'}


def ch_solution(rng):
    s = rng.choice(list(SOLUTES))
    name = SOLUTES[s]
    m1 = rng.choice([50, 80, 100, 120, 150, 200, 250, 300, 400, 500])
    w1 = rng.choice([2, 4, 5, 8, 10, 12, 15, 20, 25])
    v = rng.randrange(4)
    solute = Fr(m1 * w1, 100)
    if v == 0:
        water = rng.choice([20, 30, 50, 70, 100, 150])
        mdd = rng.choice([5, 10, 15, 20, 25, 30])
        w = (solute + mdd) / (m1 + water + mdd) * 100
        q = f'К {m1} г раствора с массовой долей {name} {w1} % добавили {water} мл воды и {mdd} г этого же вещества. Вычислите массовую долю вещества в полученном растворе.'
        e = f'm(в-ва) = {m1}·{w1}/100 + {mdd} = {ru(solute + mdd)} г; m(р-ра) = {m1} + {water} + {mdd} = {m1 + water + mdd} г; ω = {ru(solute + mdd)}/{m1 + water + mdd}·100 %'
        wrong = [fmt((solute + mdd) / (m1 + mdd) * 100, 0), fmt(solute / (m1 + water + mdd) * 100, 0), fmt((solute + mdd) / (m1 + water) * 100, 0)]
    elif v == 1:
        m2 = rng.choice([50, 100, 150, 200, 250, 300])
        w2 = rng.choice([x for x in (5, 10, 15, 20, 25, 30, 40) if x != w1])
        w = (solute + Fr(m2 * w2, 100)) / (m1 + m2) * 100
        q = f'Смешали {m1} г {w1} %-го и {m2} г {w2} %-го растворов {name}. Вычислите массовую долю вещества в полученном растворе.'
        e = f'm(в-ва) = {ru(solute)} + {ru(Fr(m2 * w2, 100))} = {ru(solute + Fr(m2 * w2, 100))} г; m(р-ра) = {m1 + m2} г; ω = m(в-ва)/m(р-ра)·100 %'
        wrong = [fmt(Fr(w1 + w2, 2), 1), fmt(Fr(w1 + w2), 0), fmt((solute + Fr(m2 * w2, 100)) / max(m1, m2) * 100, 0)]
    elif v == 2:
        ev = rng.choice([x for x in (10, 20, 30, 40, 50, 60, 80, 100) if x < m1 - solute])
        w = solute / (m1 - ev) * 100
        q = f'Из {m1} г раствора {name} с массовой долей {w1} % выпарили {ev} г воды. Вычислите массовую долю вещества в полученном растворе.'
        e = f'm(в-ва) = {ru(solute)} г не меняется; m(р-ра) = {m1} − {ev} = {m1 - ev} г; ω = {ru(solute)}/{m1 - ev}·100 %'
        wrong = [fmt(solute / (m1 + ev) * 100, 0), fmt(Fr(w1), 0), fmt((solute - ev) / m1 * 100, 0) if solute > ev else None]
    else:
        wt = rng.choice([x for x in (1, 2, 3, 4, 5) if x < w1])
        water = solute * 100 / wt - m1
        if water <= 0 or water > 2000:
            raise Retry
        q = f'Сколько граммов воды нужно добавить к {m1} г {w1} %-го раствора {name}, чтобы получить {wt} %-й раствор?'
        w = water
        e = f'm(в-ва) = {ru(solute)} г; m(нового р-ра) = {ru(solute)}·100/{wt} = {ru(solute * 100 / wt)} г; m(воды) = {ru(solute * 100 / wt)} − {m1}'
        wrong = [fmt(solute * 100 / wt, 0), fmt(Fr(m1 * w1, wt), 0), fmt(m1 * Fr(w1 - wt, 100), 0)]
    dec = rng.choice([0, 1])
    ans = fmt(w, dec)
    prec = 'целых' if dec == 0 else 'десятых'
    unit = ' г' if v == 3 else ' %'
    q += f' (Запишите число с точностью до {prec}.)'
    e += f' ≈ {ans}{unit}.'
    wrong = [fmt(num(x), dec) for x in wrong if x]
    return card('ch-solution', 'ЕГЭ', 26, 'chem-ege-26', q, ans, e, extra={'wrong': wrong, 'dec': dec})


# ---------- ЕГЭ 27. Термохимия

THERMO = [  # (реагенты, продукты, Q кДж на уравнение с наименьшими коэффициентами; >0 — выделяется). Табличные значения, округлённые.
    (['CH4', 'O2'], ['CO2', 'H2O'], 802, 'H2O(г)'),
    (['C2H5OH', 'O2'], ['CO2', 'H2O'], 1374, 'H2O(г)'),
    (['H2', 'O2'], ['H2O'], 484, 'H2O(г)'),
    (['C', 'O2'], ['CO2'], 393, ''),
    (['S', 'O2'], ['SO2'], 297, ''),
    (['P', 'O2'], ['P2O5'], 3010, ''),
    (['N2', 'H2'], ['NH3'], 92, ''),
    (['CO', 'O2'], ['CO2'], 566, ''),
    (['Mg', 'O2'], ['MgO'], 1204, ''),
    (['Al', 'O2'], ['Al2O3'], 3352, ''),
    (['C6H12O6', 'O2'], ['CO2', 'H2O'], 2816, 'H2O(ж)'),
    (['CaCO3'], ['CaO', 'CO2'], -178, ''),
    (['SO2', 'O2'], ['SO3'], 198, ''),
    (['C2H2', 'O2'], ['CO2', 'H2O'], 2610, 'H2O(г)'),
]


def ch_thermo(rng):
    lhs, rhs, Q, note = rng.choice(THERMO)
    kl, kr = balance(lhs, rhs)
    eq = pretty(eq_str(lhs, rhs, kl, kr, '='))
    eqs = f'{eq} {"+" if Q > 0 else "−"} {abs(Q)} кДж'
    i = rng.randrange(len(lhs))
    sub, k = lhs[i], kl[i]
    M = molar(sub)
    v = rng.randrange(2)
    if v == 0:
        m = Fr(rng.choice([1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 23, 24, 32, 40, 46, 50, 64, 100]), rng.choice([1, 10]))
        heat = abs(Q) * m / (M * k)
        dec = rng.choice([0, 1])
        ans = fmt(heat, dec)
        if heat < 1 or abs(num(ans) - heat) / heat > 0.02:
            raise Retry
        verb = 'выделится' if Q > 0 else 'поглотится'
        q = f'По термохимическому уравнению {eqs} вычислите, сколько теплоты {verb} при {"реакции" if Q > 0 else "разложении"} {ru(m)} г {pretty(sub)}. (Запишите число с точностью до {"целых" if dec == 0 else "десятых"}.)'
        e = f'n({pretty(sub)}) = {ru(m)}/{ru(M)} моль; по уравнению на {k} моль — {abs(Q)} кДж ⇒ Q = {abs(Q)}·n/{k} ≈ {ans} кДж.'
        wrong = [fmt(abs(Q) * m / M, dec), fmt(abs(Q) * m * k / M, dec), fmt(abs(Q) * m / (M * k) * 2, dec)]
    else:
        n = Fr(rng.choice([1, 2, 5, 10, 20, 25, 50]), rng.choice([10, 100, 1]))
        heat = abs(Q) * n
        m = n * k * M
        dec = rng.choice([0, 1])
        ans = fmt(m, dec)
        if abs(num(ans) - m) / m > 0.02:
            raise Retry
        q = f'По термохимическому уравнению {eqs} вычислите массу {pretty(sub)}, {"вступившего в реакцию" if Q > 0 else "подвергшегося разложению"}, если {"выделилось" if Q > 0 else "поглотилось"} {ru(heat)} кДж теплоты. Ответ дайте в граммах. (Запишите число с точностью до {"целых" if dec == 0 else "десятых"}.)'
        e = f'n(реакций) = {ru(heat)}/{abs(Q)}; n({pretty(sub)}) = {k}·{ru(n)} = {ru(n * k)} моль; m = n·M = {ru(n * k)}·{ru(M)} ≈ {ans} г.'
        wrong = [fmt(n * M, dec), fmt(heat / M, dec), fmt(n * k, dec)]
    return card('ch-thermo', 'ЕГЭ', 27, 'chem-ege-27', q, ans, e, extra={'wrong': wrong, 'eq': [lhs, rhs, kl, kr]})


# ---------- ЕГЭ 28 / ОГЭ. Расчёт по уравнению (выход, примеси)

STOICH = [  # (реагенты, продукты, что дано, что найти, газ ли искомое)
    (['CaCO3', 'HCl'], ['CaCl2', 'CO2', 'H2O'], 'CaCO3', 'CO2', 'известняк'),
    (['Zn', 'HCl'], ['ZnCl2', 'H2'], 'Zn', 'H2', 'технический цинк'),
    (['Na2SO3', 'HCl'], ['NaCl', 'SO2', 'H2O'], 'Na2SO3', 'SO2', 'технический сульфит натрия'),
    (['CuS', 'O2'], ['CuO', 'SO2'], 'CuS', 'SO2', 'сульфид меди(II)'),
    (['Al', 'HCl'], ['AlCl3', 'H2'], 'Al', 'H2', 'алюминий'),
    (['CaCO3'], ['CaO', 'CO2'], 'CaCO3', 'CaO', 'известняк'),
    (['Fe2O3', 'H2'], ['Fe', 'H2O'], 'Fe2O3', 'Fe', 'оксид железа(III)'),
    (['N2', 'H2'], ['NH3'], 'N2', 'NH3', 'азот'),
    (['CaC2', 'H2O'], ['Ca(OH)2', 'C2H2'], 'CaC2', 'C2H2', 'технический карбид кальция'),
    (['Na2CO3', 'HCl'], ['NaCl', 'CO2', 'H2O'], 'Na2CO3', 'CO2', 'кальцинированная сода'),
    (['NH4Cl', 'Ca(OH)2'], ['CaCl2', 'NH3', 'H2O'], 'NH4Cl', 'NH3', 'хлорид аммония'),
]
GASES = {'CO2', 'H2', 'SO2', 'NH3', 'C2H2', 'O2', 'CH4'}


def ch_stoich(rng):
    lhs, rhs, given, find, label = rng.choice(STOICH)
    kl, kr = balance(lhs, rhs)
    species, ks = lhs + rhs, kl + kr
    kg, kf = ks[species.index(given)], ks[species.index(find)]
    Mg, Mf = molar(given), molar(find)
    m = Fr(rng.choice([2, 4, 5, 8, 10, 12, 14, 16, 20, 25, 28, 30, 40, 50, 64, 80, 100, 120, 200]), 1)
    mode = rng.choice(['plain', 'impurity', 'yield'])
    pure = m
    txt = ''
    if mode == 'impurity':
        imp = rng.choice([5, 10, 15, 20, 25])
        pure = m * (100 - imp) / 100
        txt = f', содержащего {imp} % примесей (не участвующих в реакции),'
    eta = 100
    if mode == 'yield':
        eta = rng.choice([60, 70, 75, 80, 85, 90, 95])
    n_given = pure / Mg
    n_find = n_given * kf / kg * eta / 100
    as_gas = find in GASES and rng.random() < 0.7
    dec = rng.choice([0, 1, 2])
    if as_gas:
        val = n_find * Fr(224, 10)
        what, unit = 'объём (н. у.)', 'л'
    else:
        val = n_find * Mf
        what, unit = 'массу', 'г'
    ans = fmt(val, dec)
    if val < Fr(1, 10) or abs(num(ans) - val) / val > 0.02:
        raise Retry
    ytxt = f' с выходом {eta} %' if mode == 'yield' else ''
    q = (f'Вычислите {what} {pretty(find)}, полученного{ytxt} из {ru(m)} г {pretty(given)} ({label}){txt} по реакции '
         f'{pretty(eq_str(lhs, rhs, kl, kr))}. Ответ дайте в {"литрах" if unit == "л" else "граммах"}. (Запишите число с точностью до {["целых", "десятых", "сотых"][dec]}.)')
    e = (f'm(чист.) = {ru(pure)} г; n({pretty(given)}) = {ru(pure)}/{ru(Mg)}; n({pretty(find)}) = n·{kf}/{kg}' +
         (f'·{eta}/100' if mode == 'yield' else '') + (f'; V = n·22,4' if as_gas else f'; m = n·{ru(Mf)}') + f' ≈ {ans} {unit}.')
    wrong = [fmt(m / Mg * kf / kg * eta / 100 * (Fr(224, 10) if as_gas else Mf), dec) if mode == 'impurity' else None,
             fmt(n_given * (Fr(224, 10) if as_gas else Mf), dec) if kf != kg else fmt(val * 2, dec),
             fmt(val * 100 / eta, dec) if mode == 'yield' else fmt(val * Fr(3, 2), dec)]
    return card('ch-stoich', 'ЕГЭ', 28, 'chem-ege-28', q, ans, e, extra={'wrong': [w for w in wrong if w], 'eq': [lhs, rhs, kl, kr]})


# ---------- ЕГЭ 22. Смещение равновесия (Ле Шателье)

EQUILIBRIA = [  # (запись, ΔH<0 — экзо, Δn газов справа − слева, вещества: {формула: сторона 'L'/'R', газ/раствор})
    ('N₂(г) + 3H₂(г) ⇄ 2NH₃(г)', 'экзо', -2, {'N₂': 'L', 'H₂': 'L', 'NH₃': 'R'}),
    ('2SO₂(г) + O₂(г) ⇄ 2SO₃(г)', 'экзо', -1, {'SO₂': 'L', 'O₂': 'L', 'SO₃': 'R'}),
    ('CaCO₃(тв) ⇄ CaO(тв) + CO₂(г)', 'эндо', 1, {'CO₂': 'R'}),
    ('N₂(г) + O₂(г) ⇄ 2NO(г)', 'эндо', 0, {'N₂': 'L', 'O₂': 'L', 'NO': 'R'}),
    ('H₂(г) + I₂(г) ⇄ 2HI(г)', 'экзо', 0, {'H₂': 'L', 'I₂': 'L', 'HI': 'R'}),
    ('CO(г) + H₂O(г) ⇄ CO₂(г) + H₂(г)', 'экзо', 0, {'CO': 'L', 'H₂O': 'L', 'CO₂': 'R', 'H₂': 'R'}),
    ('2NO₂(г) ⇄ N₂O₄(г)', 'экзо', -1, {'NO₂': 'L', 'N₂O₄': 'R'}),
    ('CH₄(г) + H₂O(г) ⇄ CO(г) + 3H₂(г)', 'эндо', 2, {'CH₄': 'L', 'H₂O': 'L', 'CO': 'R', 'H₂': 'R'}),
    ('C(тв) + CO₂(г) ⇄ 2CO(г)', 'эндо', 1, {'CO₂': 'L', 'CO': 'R'}),
    ('2NO(г) + O₂(г) ⇄ 2NO₂(г)', 'экзо', -1, {'NO': 'L', 'O₂': 'L', 'NO₂': 'R'}),
    ('PCl₅(г) ⇄ PCl₃(г) + Cl₂(г)', 'эндо', 1, {'PCl₅': 'L', 'PCl₃': 'R', 'Cl₂': 'R'}),
]
SHIFT = {'1': 'в сторону прямой реакции', '2': 'в сторону обратной реакции', '3': 'практически не смещается'}


def lechatelier(heat, dn, subs, factor):
    kind, arg = factor
    if kind == 'T':
        up = arg == 'up'
        exo = heat == 'экзо'
        return '2' if up == exo else '1'
    if kind == 'p':
        if dn == 0:
            return '3'
        up = arg == 'up'
        return '1' if (dn < 0) == up else '2'
    if kind == 'cat':
        return '3'
    s, how = arg
    side = subs[s]
    add = how == 'add'
    return '1' if (side == 'L') == add else '2'


def ch_lechatelier(rng):
    eq, heat, dn, subs = rng.choice(EQUILIBRIA)
    factors = [('T', 'up'), ('T', 'down'), ('p', 'up'), ('p', 'down'), ('cat', None)]
    for s in subs:
        factors += [('c', (s, 'add')), ('c', (s, 'rem'))]
    pick = rng.sample(factors, 4)
    text = {('T', 'up'): 'повышение температуры', ('T', 'down'): 'понижение температуры', ('p', 'up'): 'повышение давления',
            ('p', 'down'): 'понижение давления', ('cat', None): 'добавление катализатора'}

    def name(f):
        if f[0] == 'c':
            return ('увеличение' if f[1][1] == 'add' else 'уменьшение') + f' концентрации {f[1][0]}'
        return text[f]
    left = [{'id': 'АБВГ'[i], 't': name(f)} for i, f in enumerate(pick)]
    a = {'АБВГ'[i]: lechatelier(heat, dn, subs, f) for i, f in enumerate(pick)}
    q = f'Для {"экзотермической" if heat == "экзо" else "эндотермической"} реакции {eq} установите соответствие между воздействием на систему и направлением смещения равновесия.'
    o = {'left': left, 'right': [{'id': k, 't': v} for k, v in SHIFT.items()]}
    e = f'Принцип Ле Шателье. Δn(газов) = {dn:+d};'.replace('+0', '0') + f' реакция {"экзо" if heat == "экзо" else "эндо"}термическая; катализатор равновесие не смещает. Ответ ЕГЭ: ' + ''.join(a[k] for k in 'АБВГ') + '.'
    return card('ch-lechat', 'ЕГЭ', 22, 'chem-ege-22', q, a, e, k='match', o=o, extra={'answer_ege': ''.join(a[k] for k in 'АБВГ')})


# ---------- ЕГЭ 23. Равновесные концентрации

EQ23 = [  # (реагенты с коэф., продукты с коэф.) — все газы
    ([('A', 1), ('B', 1)], [('C', 1)]),
    ([('SO₂', 2), ('O₂', 1)], [('SO₃', 2)]),
    ([('N₂', 1), ('H₂', 3)], [('NH₃', 2)]),
    ([('H₂', 1), ('I₂', 1)], [('HI', 2)]),
    ([('CO', 1), ('Cl₂', 1)], [('COCl₂', 1)]),
    ([('NO', 2), ('O₂', 1)], [('NO₂', 2)]),
    ([('CH₄', 1), ('H₂O', 1)], [('CO', 1), ('H₂', 3)]),
    ([('CO', 1), ('H₂O', 1)], [('CO₂', 1), ('H₂', 1)]),
]


def ch_eqconc(rng):
    lhs, rhs = rng.choice(EQ23)
    x = Fr(rng.choice([1, 2, 3, 4, 5]), 10)  # моль/л «прореагировало» на единицу коэффициента
    c0 = {}
    for s, k in lhs:
        c0[s] = k * x + Fr(rng.choice([1, 2, 3, 4, 5, 6]), 10)
    for s, k in rhs:
        c0[s] = Fr(rng.choice([0, 0, 1, 2]), 10)
    ceq = {s: c0[s] - k * x for s, k in lhs}
    ceq.update({s: c0[s] + k * x for s, k in rhs})
    species = [s for s, _ in lhs] + [s for s, _ in rhs]
    # скрываем 2 значения, одно из них — исходная или равновесная концентрация
    cells = [(s, 'исх') for s in species] + [(s, 'равн') for s in species]
    # чтобы решение было однозначным, оставляем открытыми обе концентрации (исх, равн) хотя бы одного вещества
    key = rng.choice(species)
    hidden = rng.sample([c for c in cells if c[0] != key], 2)
    val = lambda c: c0[c[0]] if c[1] == 'исх' else ceq[c[0]]
    right = sorted({val(h) for h in hidden})
    pool = set(right)
    cand = [Fr(i, 10) for i in range(1, 20)]
    rng.shuffle(cand)
    for cnd in cand:
        if len(pool) >= 6:
            break
        pool.add(cnd)
    pool = sorted(pool)
    if len({val(h) for h in hidden}) < 2 and len(pool) < 6:
        raise Retry
    kstr = lambda k: '' if k == 1 else str(k)
    eq = ' + '.join(kstr(k) + s for s, k in lhs) + ' ⇄ ' + ' + '.join(kstr(k) + s for s, k in rhs)
    shown = []
    for c in cells:
        if c in hidden:
            continue
        shown.append(f'{c[0]}: {c[1]}. {ru(val(c))} моль/л')
    lbl = {hidden[0]: 'X', hidden[1]: 'Y'}
    q = (f'В реакторе постоянного объёма протекает реакция {eq} (все вещества — газы). Известно: ' + '; '.join(shown) +
         f'. Найдите {hidden[0][1]}. концентрацию {hidden[0][0]} (X) и {hidden[1][1]}. концентрацию {hidden[1][0]} (Y).')
    right_list = [{'id': str(i + 1), 't': f'{ru(v)} моль/л'} for i, v in enumerate(pool)]
    a = {'X': str(pool.index(val(hidden[0])) + 1), 'Y': str(pool.index(val(hidden[1])) + 1)}
    o = {'left': [{'id': 'X', 't': f'{hidden[0][1]}. [{hidden[0][0]}]'}, {'id': 'Y', 't': f'{hidden[1][1]}. [{hidden[1][0]}]'}], 'right': right_list}
    e = (f'По веществу {key}: изменение {ru(abs(ceq[key] - c0[key]))} моль/л, что соответствует x = {ru(x)} моль/л на единицу коэффициента. '
         f'Изменения пропорциональны коэффициентам: реагенты −k·x, продукты +k·x. X = {ru(val(hidden[0]))}, Y = {ru(val(hidden[1]))}. Ответ ЕГЭ: {a["X"]}{a["Y"]}.')
    return card('ch-eqconc', 'ЕГЭ', 23, 'chem-ege-23', q, a, e, k='match', o=o,
                extra={'answer_ege': a['X'] + a['Y'], 'check': {'c0': {k: str(v) for k, v in c0.items()}, 'ceq': {k: str(v) for k, v in ceq.items()}}})


# ---------- ЕГЭ 21. Порядок растворов по pH (одинаковая молярная концентрация)

PH_TIERS = [  # от самого кислого к самому щелочному; внутри ступени вещества не сравниваем
    ['H₂SO₄'], ['HCl', 'HNO₃', 'HBr'], ['CH₃COOH', 'HCOOH'], ['NH₄Cl', 'NH₄NO₃', '(NH₄)₂SO₄'],
    ['NaCl', 'KNO₃', 'Na₂SO₄', 'KCl', 'BaCl₂'], ['CH₃COONa', 'KF'], ['Na₂CO₃', 'K₂CO₃', 'Na₃PO₄'],
    ['KOH', 'NaOH', 'LiOH'], ['Ba(OH)₂', 'Ca(OH)₂'],
]


def ch_ph_order(rng):
    tiers = sorted(rng.sample(range(len(PH_TIERS)), 4))
    subs = [rng.choice(PH_TIERS[t]) for t in tiers]
    shown = subs[:]
    rng.shuffle(shown)
    asc = rng.random() < 0.5
    order = subs if asc else subs[::-1]
    ans = ''.join(str(shown.index(s) + 1) for s in order)
    q = (f'Расположите вещества в порядке {"возрастания" if asc else "убывания"} pH их водных растворов одинаковой молярной концентрации: ' +
         '; '.join(f'{i + 1}) {s}' for i, s in enumerate(shown)) + '. Запишите номера в нужном порядке.')
    e = ('Сильные кислоты (двухосновная — ниже всех) < слабые кислоты < соли слабого основания и сильной кислоты < нейтральные соли '
         '< соли слабой кислоты и сильного основания < щёлочи (двухкислотные — выше). Ответ: ' + ans + '.')
    return card('ch-ph', 'ЕГЭ', 21, 'chem-ege-21', q, ans, e, extra={'tiers': tiers, 'shown': shown})


SUP = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')


def ch_ph_calc(rng):
    v = rng.randrange(3)
    n = rng.randrange(1, 6)
    sn = str(n).translate(SUP)
    if v == 0:
        acid = rng.choice(['HCl', 'HNO₃', 'HBr'])
        q = f'Концентрация раствора {acid} (сильная кислота, диссоциирует полностью) равна 10⁻{sn} моль/л. Чему равен pH раствора?'
        ans = str(n)
        e = f'[H⁺] = 10⁻{sn} ⇒ pH = −lg[H⁺] = {n}.'
    elif v == 1:
        base = rng.choice(['NaOH', 'KOH'])
        q = f'Концентрация раствора {base} равна 10⁻{sn} моль/л. Чему равен pH раствора (25 °C)?'
        ans = str(14 - n)
        e = f'[OH⁻] = 10⁻{sn} ⇒ pOH = {n}, pH = 14 − {n} = {14 - n}.'
    else:
        k = rng.randrange(1, 4)
        if n + k > 6:
            raise Retry
        q = f'Раствор HCl с pH = {n} разбавили водой в {10 ** k} раз. Каким стал pH?'
        ans = str(n + k)
        e = f'[H⁺] уменьшилась в 10^{k} раз ⇒ pH вырос на {k}: {n} + {k} = {n + k}.'
    return card('ch-phcalc', '10–11 кл.', 'pH', 'chem-ph', q, ans, e)


# ---------- ЕГЭ 1–3 / ОГЭ: закономерности ПСХЭ (без справочных чисел — только правила)

PERIODS = {2: ['Li', 'Be', 'B', 'C', 'N', 'O', 'F'], 3: ['Na', 'Mg', 'Al', 'Si', 'P', 'S', 'Cl']}
GROUPS = {'I': ['Li', 'Na', 'K', 'Rb', 'Cs'], 'II': ['Be', 'Mg', 'Ca', 'Sr', 'Ba'], 'VI': ['O', 'S', 'Se', 'Te'], 'VII': ['F', 'Cl', 'Br', 'I']}


def ch_period_law(rng):
    prop = rng.choice(['радиуса атома', 'электроотрицательности', 'металлических свойств'])
    if rng.random() < 0.5:
        p = rng.choice(list(PERIODS))
        seq = PERIODS[p]
        along = 'period'
    else:
        g = rng.choice(list(GROUPS))
        seq = GROUPS[g]
        along = 'group'
    picked = sorted(rng.sample(range(len(seq)), 3))
    els = [seq[i] for i in picked]
    # в периоде слева направо: радиус ↓, ЭО ↑, металличность ↓; в группе сверху вниз: радиус ↑, ЭО ↓, металличность ↑
    grows = {'радиуса атома': along == 'group', 'электроотрицательности': along == 'period', 'металлических свойств': along == 'group'}[prop]
    asc_order = els if grows else els[::-1]
    shown = els[:]
    rng.shuffle(shown)
    asc = rng.random() < 0.5
    order = asc_order if asc else asc_order[::-1]
    ans = ''.join(str(shown.index(x) + 1) for x in order)
    q = f'Расположите химические элементы в порядке {"увеличения" if asc else "уменьшения"} {prop}: ' + '; '.join(f'{i + 1}) {x}' for i, x in enumerate(shown)) + '. Запишите номера в нужном порядке.'
    e = ('В периоде слева направо радиус и металлические свойства уменьшаются, электроотрицательность растёт; '
         'в группе (главной подгруппе) сверху вниз — наоборот. Ответ: ' + ans + '.')
    return card('ch-period', 'ЕГЭ/ОГЭ', 2, 'chem-ege-2', q, ans, e)


# ---------- Степени окисления (ОГЭ 3/ЕГЭ 3, 8–9 кл.)

OX_FIXED = {'O': -2, 'H': 1, 'Na': 1, 'K': 1, 'Li': 1, 'Ca': 2, 'Mg': 2, 'Ba': 2, 'Al': 3, 'F': -1, 'Zn': 2}
OX_COMPOUNDS = [('KMnO4', 'Mn'), ('K2MnO4', 'Mn'), ('MnO2', 'Mn'), ('K2Cr2O7', 'Cr'), ('K2CrO4', 'Cr'), ('Cr2O3', 'Cr'),
                ('H2SO4', 'S'), ('Na2SO3', 'S'), ('H2S', 'S'), ('SO3', 'S'), ('Na2S2O3', 'S'), ('HNO3', 'N'), ('NaNO2', 'N'),
                ('NH3', 'N'), ('N2O', 'N'), ('NO2', 'N'), ('HClO4', 'Cl'), ('KClO3', 'Cl'), ('NaClO', 'Cl'), ('HCl', 'Cl'),
                ('H3PO4', 'P'), ('PH3', 'P'), ('Fe2O3', 'Fe'), ('Fe3O4', 'Fe'), ('CO', 'C'), ('CH4', 'C'), ('CaC2', 'C'),
                ('H2O2', 'O'), ('Na2O2', 'O'), ('OF2', 'O'), ('NaH', 'H'), ('CaH2', 'H'), ('Al4C3', 'C'), ('Mg3N2', 'N'),
                ('K2FeO4', 'Fe'), ('NaClO2', 'Cl'), ('HIO3', 'I'), ('SiO2', 'Si'), ('Na2SiO3', 'Si')]


def ox_state(formula, el):
    comp = parse_formula(formula)
    fixed = dict(OX_FIXED)
    if el in fixed:
        del fixed[el]
    # пероксиды и гидриды: O и H — искомые, остальное из таблицы
    if el == 'O' and 'F' in comp:
        fixed['F'] = -1
    total = sum(fixed[e] * n for e, n in comp.items() if e != el)
    unknown = [e for e in comp if e != el and e not in fixed]
    if unknown:
        raise ValueError(f'{formula}: нет фиксированной степени для {unknown}')
    return Fr(-total, comp[el])


def ch_oxstate(rng):
    f, el = rng.choice(OX_COMPOUNDS)
    s = ox_state(f, el)
    ans = fmt(s)
    q = f'Определите степень окисления {el} в соединении {pretty(f)}. Ответ запишите числом со знаком (например, +3 или −2; для дробной — десятичной дробью).'
    ans_view = ('+' if s > 0 else '') + ans
    e = f'Сумма степеней окисления в молекуле равна 0; известные: ' + ', '.join(f'{k} {OX_FIXED[k]:+d}' for k in parse_formula(f) if k in OX_FIXED and k != el) + f'. Для {el}: {ans_view}.'
    wrong = [fmt(-s), fmt(s + 1), fmt(s - 2)]
    return card('ch-ox', 'ОГЭ/ЕГЭ', 'с.о.', 'chem-ox', q, ans, e, extra={'wrong': wrong})


# ================================================================= реестр и самопроверка

GENERATORS = {
    # ЕГЭ физика
    'ph-kin': (ph_kin, 'ЕГЭ физика 1: кинематика'),
    'ph-dyn': (ph_dyn, 'ЕГЭ физика 2: динамика'),
    'ph-cons': (ph_cons, 'ЕГЭ физика 3: законы сохранения'),
    'ph-stat': (ph_stat_osc, 'ЕГЭ физика 4: статика, колебания'),
    'ph-change': (ph_change, 'ЕГЭ физика 6/10/15/17: изменение величин'),
    'ph-mkt': (ph_mkt, 'ЕГЭ физика 7: МКТ'),
    'ph-thermo': (ph_thermo, 'ЕГЭ физика 8: термодинамика'),
    'ph-el': (ph_el, 'ЕГЭ физика 11: электростатика, ток'),
    'ph-mag': (ph_mag, 'ЕГЭ физика 12: магнетизм, индукция'),
    'ph-opt': (ph_opt, 'ЕГЭ физика 13: колебания, оптика'),
    'ph-nuc': (ph_nuc, 'ЕГЭ физика 16: ядро'),
    'ph-exp': (ph_exp, 'ЕГЭ физика 20: планирование опыта'),
    'ph-oge-mech': (ph_oge_mech, 'ОГЭ физика: плотность, давление, мощность'),
    # химия
    'ch-period': (ch_period_law, 'ЕГЭ/ОГЭ химия 2: закономерности ПСХЭ'),
    'ch-ox': (ch_oxstate, 'Химия: степени окисления'),
    'ch-balance': (ch_balance, 'Химия 8 кл./ОГЭ: коэффициенты'),
    'ch-wfrac': (ch_wfrac, 'ОГЭ химия: массовая доля элемента'),
    'ch-mole': (ch_mole, '8 кл.: количество вещества'),
    'ch-ph': (ch_ph_order, 'ЕГЭ химия 21: порядок по pH'),
    'ch-phcalc': (ch_ph_calc, 'Химия: pH сильных кислот и щелочей'),
    'ch-lechat': (ch_lechatelier, 'ЕГЭ химия 22: смещение равновесия'),
    'ch-eqconc': (ch_eqconc, 'ЕГЭ химия 23: равновесные концентрации'),
    'ch-solution': (ch_solution, 'ЕГЭ химия 26: растворы'),
    'ch-thermo': (ch_thermo, 'ЕГЭ химия 27: термохимия'),
    'ch-stoich': (ch_stoich, 'ЕГЭ химия 28: расчёт по уравнению'),
}

# Физически/химически осмысленные диапазоны ответа для числовых типов
RANGES = {
    'ph-kin': (-100, 1000), 'ph-dyn': (0, 5000), 'ph-cons': (0, 20000), 'ph-stat': (0, 1000), 'ph-mkt': (0, 1e5),
    'ph-thermo': (-1000, 1e5), 'ph-el': (0, 1e5), 'ph-mag': (0, 1e4), 'ph-opt': (0, 1000), 'ph-nuc': (0, 1000),
    'ph-oge-mech': (0, 1e6), 'ch-ox': (-4, 8), 'ch-balance': (1, 60), 'ch-wfrac': (0, 100), 'ch-mole': (0, 1e5),
    'ch-phcalc': (0, 14), 'ch-solution': (0, 5000), 'ch-thermo': (0, 1e5), 'ch-stoich': (0, 1e4),
}


def generate(typ, rng, tries=200):
    fn = GENERATORS[typ][0]
    for _ in range(tries):
        try:
            return fn(rng)
        except Retry:
            continue
    raise RuntimeError(f'{typ}: не удалось подобрать параметры')


def validate(c, typ):
    """Проверки одной карточки. Возвращает список проблем."""
    errs = []
    for f in ('id', 't', 'k', 'q', 'a', 'e'):
        if f not in c or c[f] in (None, ''):
            errs.append(f'нет поля {f}')
    if c['k'] == 'num':
        s = c['a']
        if not re.fullmatch(r'-?\d+(,\d+)?', s):
            errs.append(f'ответ не число: {s!r}')
        else:
            lo, hi = RANGES.get(typ, (-1e9, 1e9))
            if not lo <= num(s) <= hi:
                errs.append(f'ответ вне диапазона {lo}..{hi}: {s}')
            if len(s.replace('-', '').replace(',', '')) > 8:
                errs.append(f'слишком длинный ответ {s}')
    if c['k'] == 'one':
        ids = [o['id'] for o in c['o']]
        if c['a'] not in ids or len({o['t'] for o in c['o']}) != len(ids):
            errs.append('варианты: нет верного или повторы')
    if c['k'] == 'match':
        L = {x['id'] for x in c['o']['left']}
        R = {x['id'] for x in c['o']['right']}
        if set(c['a']) != L or not set(c['a'].values()) <= R:
            errs.append('соответствие не покрывает левый столбец')
    if c['k'] == 'many':
        if not c['a'] or not set(c['a']) <= {o['id'] for o in c['o']}:
            errs.append('many: ответ не из вариантов')
    g = c.get('gen', {})
    if 'eq' in g:
        lhs, rhs, kl, kr = g['eq']
        if not check_balance(lhs, rhs, kl, kr):
            errs.append('уравнение не уравнено')
    if 'check_nuc' in g:
        tgt, pr, prod, out = g['check_nuc']
        A = tgt[0] + PARTICLES[pr][0] - PARTICLES[out][0]
        Z = tgt[1] + PARTICLES[pr][1] - PARTICLES[out][1]
        if (A, Z) != tuple(prod):
            errs.append(f'ядерная реакция не сбалансирована: {g["check_nuc"]}')
    if 'wrong' in g and c['k'] == 'num':
        w = [x for x in g['wrong'] if x and x != c['a']]
        if len(set(w)) < 2:
            errs.append('мало дистракторов')
    if 'check' in g:  # равновесие: концентрации неотрицательны
        if any(Fr(v) < 0 for v in g['check']['ceq'].values()):
            errs.append('отрицательная равновесная концентрация')
    if typ == 'ch-ph':
        if g['tiers'] != sorted(set(g['tiers'])):
            errs.append('pH: повтор ступени')
    return errs


def self_check(n=200, seed=2026):
    """По n вариантов на тип: ответ вычисляется, в диапазоне, уравнения уравнены, дубликаты текста."""
    # Статические проверки справочных данных
    static = []
    for lhs, rhs, d in REACTIONS:
        kl, kr = balance(lhs, rhs)
        if not check_balance(lhs, rhs, kl, kr):
            static.append(f'не уравнено: {d}')
    for lhs, rhs, Q, _ in THERMO:
        balance(lhs, rhs)
    for tgt, pr, prod, out in NUC_REACTIONS:
        if (tgt[0] + PARTICLES[pr][0] - PARTICLES[out][0], tgt[1] + PARTICLES[pr][1] - PARTICLES[out][1]) != prod:
            static.append(f'ядерная реакция: {tgt} {pr} → {prod} {out}')
    for f, el in OX_COMPOUNDS:
        ox_state(f, el)
    # Сверка с известными значениями (контрольные примеры)
    known = [
        (fmt(molar('CuSO4·5H2O')), '250'), (fmt(molar('Ca3(PO4)2')), '310'), (fmt(molar('Al2(SO4)3')), '342'),
        (fmt(ox_state('KMnO4', 'Mn')), '7'), (fmt(ox_state('K2Cr2O7', 'Cr')), '6'), (fmt(ox_state('Fe3O4', 'Fe')), '2,666667'),
        (str(balance(['C3H8', 'O2'], ['CO2', 'H2O'])), '([1, 5], [3, 4])'),
        (str(balance(['Cu', 'HNO3'], ['Cu(NO3)2', 'NO', 'H2O'])), '([3, 8], [3, 2, 4])'),
        (str(balance(['KMnO4'], ['K2MnO4', 'MnO2', 'O2'])), '([2], [1, 1, 1])'),
        (fmt(Fr(115 * 20, 100) + 27, 0), '50'),  # ЕГЭ-демо 26: 23 + 27 = 50 г соли
        (fmt((Fr(115 * 20, 100) + 27) / (115 + 58 + 27) * 100, 0), '25'),
        (fmt(Fr(1374) * Fr(23, 10) / 46, 1), '68,7'),  # демо 27: 2,3 г этанола → 68,7 кДж
    ]
    for got, want in known:
        if got != want:
            static.append(f'контроль: получено {got}, ожидалось {want}')

    rows = []
    total_err = 0
    for typ, (fn, title) in GENERATORS.items():
        rng = random.Random(f'{seed}-{typ}')
        cards, errs, seen, tries = [], Counter(), set(), 0
        while len(cards) < n and tries < n * 30:  # только разные условия: повтор — новая попытка
            tries += 1
            c = generate(typ, rng)
            if c['id'] in seen:
                continue
            seen.add(c['id'])
            for e in validate(c, typ):
                errs[e] += 1
            cards.append(c)
        uniq = len({c['id'] for c in cards})
        ids = len({c['id'] for c in cards})
        kinds = Counter(c['k'] for c in cards)
        answers = [c['a'] for c in cards if c['k'] == 'num']
        rng_ans = f'{min(answers, key=num)}…{max(answers, key=num)}' if answers else '—'
        n_err = sum(errs.values())
        total_err += n_err
        # оценка объёма пространства: уникальные тексты на 2000 попыток
        rng2 = random.Random(f'{seed}-{typ}-space')
        space = len({generate(typ, rng2)['id'] for _ in range(2000)})
        rows.append((typ, title, len(cards), uniq, tries - len(cards), n_err, dict(kinds), rng_ans, space, errs.most_common(3)))
    return static, rows, total_err



# ================================================================= прототипы (proto_*.py)

import glob as _glob
import importlib as _importlib
import os as _os
import time as _time

import pc_core as _pc

HERE = _os.path.dirname(_os.path.abspath(__file__))
ROOT = _os.path.dirname(_os.path.dirname(HERE))
FIPI_DIR = _os.environ.get('FIPI_DIR', '')  # локальная выгрузка банка ФИПИ (*.jsonl с полем text); в репозиторий не кладётся


def load_protos():
    """Импортирует все tools/research/proto_*.py; они регистрируют прототипы в pc_core.PROTOS."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    for path in sorted(_glob.glob(_os.path.join(HERE, 'proto_*.py'))):
        name = _os.path.basename(path)[:-3]
        try:
            _importlib.import_module(name)
        except Exception as ex:  # noqa: BLE001 — модуль в работе не должен ронять проверку остальных
            LOAD_ERRORS.append(f'{name}: {type(ex).__name__}: {ex}')
            print(f'!! {name} не загружен: {type(ex).__name__}: {ex}', file=sys.stderr)
    return _pc.PROTOS


LOAD_ERRORS = []


def load_fipi(subj, fipi_dir):
    """Тексты ФИПИ по предмету (phys/chem) из локальной выгрузки: {ege,oge}-{subj}.jsonl."""
    texts = []
    if not fipi_dir:
        return texts
    for path in sorted(_glob.glob(_os.path.join(fipi_dir, f'*-{subj}*.jsonl'))):
        for line in open(path, encoding='utf-8'):
            t = json.loads(line).get('text', '')
            if t:
                texts.append(t)
    return texts


def sample_unique(m, rng, n, max_tries=None):
    """n разных карточек прототипа (по тексту условия и вариантов). Возвращает (карточки, попыток, отброшено повторов)."""
    seen, out, tries, reps = set(), [], 0, 0
    max_tries = max_tries or n * 30
    while len(out) < n and tries < max_tries:
        tries += 1
        try:
            c = m['fn'](rng)
        except Retry:
            continue
        key = _pc.norm_key(c)
        if key in seen:
            reps += 1
            continue
        seen.add(key)
        out.append(c)
    return out, tries, reps


def measure_capacity(m, seed, tries=2000):
    """Ёмкость прототипа: число разных условий на `tries` попыток. growing — новые ещё появлялись в последней четверти."""
    rng = random.Random(f'{seed}-{m["id"]}-cap')
    seen = set()
    last_new = 0
    for i in range(tries):
        try:
            c = m['fn'](rng)
        except Retry:
            continue
        key = _pc.norm_key(c)
        if key not in seen:
            seen.add(key)
            last_new = i
    return len(seen), last_new > tries * 3 // 4


def proto_check(n=200, seed=2026, fipi_dir=FIPI_DIR, cap_tries=2000, only=None, quiet=False):
    protos = load_protos()
    sims = {s: _pc.Similarity(load_fipi(s, fipi_dir)) for s in ('phys', 'chem')}
    rows, all_keys, cross_dups, examples = [], {}, 0, {}
    for pid, m in protos.items():
        if only and not any(pid.startswith(x) for x in only):
            continue
        if m['fn'] is None:
            rows.append({'id': pid, 'm': m, 'kind': m['kind'], 'n': 0, 'errs': Counter(), 'cap': m['capacity'], 'growing': False,
                         'sim': None, 'sim_bad': 0, 'reps': 0, 'tries': 0})
            continue
        rng = random.Random(f'{seed}-{pid}')
        t0 = _time.time()
        cards, tries, reps = sample_unique(m, rng, n)
        errs = Counter()
        for c in cards:
            for e in _pc.check_card(c, m):
                errs[e[:120]] += 1
            key = _pc.norm_key(c)
            if key in all_keys and all_keys[key] != pid:
                cross_dups += 1
            all_keys[key] = pid
        if len(cards) < min(n, 50):
            errs[f'мало разных карточек: {len(cards)} за {tries} попыток'] += 1
        cap, growing = measure_capacity(m, seed, cap_tries)
        sim = sims[m['subj']]
        scores = [sim.score(_pc.card_text(c))[0] for c in cards] if sim.n else []
        rows.append({'id': pid, 'm': m, 'kind': m['kind'], 'n': len(cards), 'errs': errs, 'cap': cap, 'growing': growing,
                     'sim': max(scores) if scores else None, 'sim_bad': sum(s >= 0.3 for s in scores), 'reps': reps,
                     'tries': tries, 'sec': _time.time() - t0})
        examples[pid] = cards[0] if cards else None
    return rows, cross_dups, examples, {s: v.n for s, v in sims.items()}


def fidelity_of(m):
    """Паспорт соответствия КИМ из модуля + вердикт экзаменационной проверки (data/research/fidelity-review.json)."""
    f = dict(m.get('fidelity') or {})
    path = _os.path.join(ROOT, 'data', 'research', 'fidelity-review.json')
    if _os.path.exists(path):
        rev = json.load(open(path, encoding='utf-8')).get('reviews', {}).get(m['id'])
        if rev:
            f['status'] = rev['status']
            f['checked'] = rev.get('checked')
            f['passed'] = rev.get('passed')
            if rev.get('reason'):
                f['reason'] = rev['reason']
    f.setdefault('status', 'unchecked')
    return f


def export_protos(rows, examples):
    """data/source/phys-prototypes.json и chem-prototypes.json — по записи на прототип."""
    out = {'phys': [], 'chem': []}
    for r in rows:
        m = r['m']
        if m['fn'] is not None:
            c = examples.get(m['id'])
            ex = {k: c[k] for k in ('k', 'q', 'o', 'a', 'e') if k in c} if c else None
            gen = {'kind': m['kind'], 'fn': f'tools/research/{m["fn"].__module__}.py:{m["gen"]}'}
            cap = r['cap']
        else:
            ex, gen, cap = m['example'], dict(m['gen']), m['capacity']
            if m.get('why'):
                gen['why'] = m['why']
        out[m['subj']].append({
            'id': m['id'], 'exam': m['exam'], 'n': m['n'], 'title': m['title'], 'kes': m['kes'],
            'invariant': m['invariant'], 'varies': m['varies'], 'answer_rule': m['answer_rule'], 'mistakes': m['mistakes'],
            'gen': gen, 'capacity': cap, 'capacity_note': ('≥ (на 2000 попыток новые ещё появлялись)' if r.get('growing') else
                                                           ('оценка' if m['fn'] is None else 'разных условий на 2000 попыток')),
            'fipi_sim_max': None if r.get('sim') is None else round(r['sim'], 3),
            'fidelity': fidelity_of(m),
            'example': ex,
        })
    for subj, recs in out.items():
        recs.sort(key=lambda x: (x['exam'] != 'ЕГЭ', x['n'], x['id']))
        path = _os.path.join(ROOT, 'data', 'source', f'{subj}-prototypes.json')
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({'meta': {'about': 'Каталог прототипов заданий ЕГЭ (КИМ 2027) и ОГЭ: что неизменно, что меняется, '
                                         'как считается ответ; генератор аналогов или рецепт. Тексты заданий ФИПИ не включены; '
                                         'примеры составлены самостоятельно.',
                                'built_by': 'python3 tools/research/gen_phys_chem.py --protos --export'},
                       'prototypes': recs}, f, ensure_ascii=False, indent=1)
            f.write('\n')
        print('записано', path, len(recs))


def print_proto_report(rows, cross_dups, nfipi, n):
    print(f'Самопроверка прототипов: до {n} разных карточек на прототип; текстов ФИПИ для сверки: {nfipi}')
    print()
    print('| прототип | экз. | № | вид | карточек | повторов отброшено | ошибок | ёмкость | сходство с ФИПИ (макс.) |')
    print('|---|---|---|---|---|---|---|---|---|')
    tot_err = 0
    for r in rows:
        m = r['m']
        ne = sum(r['errs'].values())
        tot_err += ne
        cap = f"{r['cap']}{'+' if r['growing'] else ''}" if r['cap'] is not None else '—'
        sim = '—' if r['sim'] is None else f"{r['sim']:.2f}" + (f" ({r['sim_bad']} ≥ 0,3)" if r['sim_bad'] else '')
        print(f"| {r['id']} | {m['exam']} | {m['n']} | {r['kind']} | {r['n']} | {r['reps']} | {ne} | {cap} | {sim} |")
        for e, cnt in r['errs'].most_common(3):
            print(f'|  | ↳ {e} | {cnt} |  |  |  |  |  |  |')
    gen_rows = [r for r in rows if r['m']['fn'] is not None]
    bad_sim = sum(r['sim_bad'] for r in rows)
    print()
    print(f'Итого: прототипов {len(rows)} (с генератором {len(gen_rows)}, рецептов {len(rows) - len(gen_rows)}); '
          f'карточек {sum(r["n"] for r in rows)}; ошибок {tot_err}; повторов в выдаче 0 (отброшено при генерации '
          f'{sum(r["reps"] for r in rows)}); дублей между прототипами {cross_dups}; карточек со сходством с ФИПИ ≥ 0,3: {bad_sim}.')
    if LOAD_ERRORS:
        print('Модули с ошибкой загрузки:', '; '.join(LOAD_ERRORS))
    return tot_err + cross_dups + bad_sim + len(LOAD_ERRORS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=200)
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--seed', type=int, default=2026)
    ap.add_argument('--options', action='store_true', help='показывать числовые карточки как «один вариант» с дистракторами')
    ap.add_argument('--protos', action='store_true', help='самопроверка прототипов (proto_*.py) вместо старых 25 типов')
    ap.add_argument('--only', nargs='*', help='только прототипы с этими префиксами id (ph-ege-01 …)')
    ap.add_argument('--fipi', default=FIPI_DIR, help='папка с локальной выгрузкой ФИПИ (*.jsonl) для проверки сходства')
    ap.add_argument('--cap', type=int, default=2000, help='попыток для оценки ёмкости прототипа')
    ap.add_argument('--export', action='store_true', help='записать data/source/{phys,chem}-prototypes.json')
    ap.add_argument('--review-sample', metavar='PATH', help='выборка для экзаменационной проверки: 5 случайных аналогов на прототип (jsonl)')
    args = ap.parse_args()
    if args.review_sample:
        load_protos()
        with open(args.review_sample, 'w', encoding='utf-8') as f:
            for pid, m in _pc.PROTOS.items():
                if args.only and not any(pid.startswith(x) for x in args.only):
                    continue
                meta = {k: m[k] for k in ('id', 'exam', 'subj', 'n', 'title', 'invariant', 'varies', 'answer_rule', 'mistakes',
                                          'kind', 'kes', 'fidelity')}
                if m['fn'] is None:
                    meta.update(recipe=m['gen'], example=m['example'], capacity=m['capacity'])
                    cards = []
                else:
                    cards, _, _ = sample_unique(m, random.Random(f'review-{args.seed}-{pid}'), 5)
                    cards = [{k: c[k] for k in ('k', 'q', 'o', 'a', 'e') if k in c} for c in cards]
                f.write(json.dumps({'proto': meta, 'cards': cards}, ensure_ascii=False) + '\n')
        print('записано', args.review_sample)
        return
    if args.protos or args.export:
        if args.sample:
            load_protos()
            out = []
            for pid, m in _pc.PROTOS.items():
                if m['fn'] is None or (args.only and not any(pid.startswith(x) for x in args.only)):
                    continue
                cards, _, _ = sample_unique(m, random.Random(f'{args.seed}-{pid}-sample'), args.sample)
                out += cards
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return
        rows, cross, examples, nf = proto_check(args.n, args.seed, args.fipi, args.cap, args.only)
        bad = print_proto_report(rows, cross, nf, args.n)
        if args.export:
            export_protos(rows, examples)
        sys.exit(1 if bad else 0)
    if args.sample:
        out = []
        for typ in GENERATORS:
            rng = random.Random(f'{args.seed}-{typ}-sample')
            for _ in range(args.sample):
                c = generate(typ, rng)
                if args.options and c['k'] == 'num':
                    c = with_options(c, rng, c['gen'].get('wrong', []))
                out.append(c)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    static, rows, total_err = self_check(args.n, args.seed)
    print(f'Самопроверка генераторов: {args.n} вариантов на тип, seed {args.seed}')
    print('Справочные данные и контрольные примеры:', 'OK' if not static else '; '.join(static))
    print()
    print('| тип | задание | карточек | уникальных условий | отброшено повторов | ошибок | виды карточек | диапазон ответа | уникальных на 2000 |')
    print('|---|---|---|---|---|---|---|---|---|')
    for typ, title, n, uniq, ids, n_err, kinds, rng_ans, space, top in rows:
        kinds_s = ', '.join(f'{k} {v}' for k, v in kinds.items())
        print(f'| {typ} | {title} | {n} | {uniq} | {ids} | {n_err} | {kinds_s} | {rng_ans} | {space} |')
        for e, cnt in top:
            print(f'|  | ↳ {e} | {cnt} |  |  |  |  |  |')
    dup_note = sum(n - uniq for _, _, n, uniq, *_ in rows)
    print()
    print(f'Итого: {len(rows)} типов, {sum(r[2] for r in rows)} карточек, ошибок {total_err}, повторов условий в выдаче {dup_note} '
          f'(повтор при генерации — новая попытка; отброшено {sum(r[4] for r in rows)}).')
    sys.exit(1 if total_err or static else 0)


if __name__ == '__main__':
    main()
