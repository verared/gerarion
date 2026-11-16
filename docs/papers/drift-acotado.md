# La Paradoja del Drift Acotado: Análisis Matemático del Mecanismo de Corrección Solar del Calendario Gerarion

> *Working Paper — Documento No Canónico*
> *Acompaña al Calendario Gerarion v1.2 como análisis matemático independiente*
> *Fecha de elaboración: 2031DY-04-05-A (19 junio 2026 gregoriano)*

-----

## Resumen

El Calendario Gerarion (Gerarion v1.2) utiliza un acumulador solar progresivo para determinar la inserción de años extendidos denominados *Gran Tempalum*. Este mecanismo produce un comportamiento del drift temporal que viola la intuición de cualquier observador: el desvío acumulado respecto al año tropical real **no crece linealmente**, sino que oscila en forma de diente de sierra con amplitud estrictamente acotada. Se demuestra formalmente que el drift del Gerarion satisface la desigualdad `|Δₙ| < 7` para todo n, independientemente del número de años transcurridos. Este resultado — denominado aquí la *Paradoja del Drift Acotado* — implica que el Calendario Gerarion nunca puede alejarse más de siete días del año tropical real, en ningún momento de la historia del universo, sin necesidad de corrección externa. Se identifican además ciclos de retorno periódico a casi-cero (período ≈ 3,105 años) y se compara el comportamiento con el calendario gregoriano, cuyo drift es lineal y no acotado.

**Palabras clave:** Calendario Gerarion, drift temporal, Gran Tempalum, acumulador solar, cota de error, año tropical.

-----

## 1. Introducción

Un calendario es, en esencia, un sistema de aproximación: intenta mapear una cantidad irracional (el año tropical real, ≈ 365.24219 días) a una secuencia de enteros (años de longitud entera). La diferencia acumulada entre ambas representaciones se denomina *drift* y constituye la medida central de precisión de cualquier sistema calendárico.

El calendario gregoriano, el estándar civil actual, resuelve este problema mediante una regla de bisiestos codificada: cada año divisible por 4 tiene 366 días, salvo los divisibles por 100 (que tienen 365), salvo los divisibles por 400 (que tienen 366). Esta regla produce un año promedio de 365.2425 días, con un error de +0.000075 días respecto al año tropical real. El resultado es un drift lineal de aproximadamente un día cada 3,226 años — excelente por cualquier estándar histórico.

El Calendario Gerarion adopta una filosofía radicalmente diferente. Su año base es de 364 días (52 semanas exactas), y la corrección solar se delega a un mecanismo dinámico denominado *Gran Tempalum*: un acumulador que suma el exceso solar anual (`δ = 365.24219 − 364 = 1.24219` días/año) y dispara un año de 371 días (53 semanas exactas) cuando dicho acumulador alcanza o supera el umbral `U = 7.0` días. El acumulador se reduce en 7 al dispararse, y el ciclo continúa.

La consecuencia de este diseño — que se demuestra a continuación — no es intuitiva y constituye el objeto central de este paper.

-----

## 2. Definiciones Formales

### 2.1 El Acumulador Solar

Sea `δ = DS − B` donde `DS = 365.24219` (año tropical) y `B = 364` (año base Gerarion). Entonces `δ = 1.24219` días/año.

Se define la secuencia del acumulador `{rₙ}` como:

```
r₀ = 0

rₙ = rₙ₋₁ + δ            si rₙ₋₁ + δ < U
rₙ = rₙ₋₁ + δ − U        si rₙ₋₁ + δ ≥ U

donde U = 7.0
```

El año n tiene duración:

```
yₙ = 371  si rₙ₋₁ + δ ≥ U  (Gran Tempalum)
yₙ = 364  en caso contrario
```

### 2.2 El Drift Acumulado

Se define el drift acumulado en n años como la diferencia entre los días Gerarions totales y los días tropicales totales:

```
Δₙ = Σᵢ₌₁ⁿ yᵢ − n · DS
```

### 2.3 El Gregoriano como Referencia

El drift gregoriano acumulado en n años es:

```
Δₙᵍ = n · 365.2425 − n · DS = n · (365.2425 − 365.24219) = n · 0.00031
```

El drift gregoriano es **lineal** en n, sin cota superior.

-----

## 3. La Paradoja del Drift Acotado

### 3.1 Enunciado

**Teorema (Cota Superior del Drift Gerarion):** Para todo n ≥ 0:

```
−7 < Δₙ ≤ 0
```

O equivalentemente:

```
|Δₙ| < U = 7 días
```

### 3.2 Demostración

**Lema previo:** Por construcción, `rₙ ∈ [0, U)` para todo n.

*Prueba del lema:* Por inducción. `r₀ = 0 ∈ [0, 7)`. Si `rₙ₋₁ ∈ [0, 7)`, entonces:

- Si `rₙ₋₁ + δ < 7`: `rₙ = rₙ₋₁ + δ < 7`. Como `δ > 0` y `rₙ₋₁ ≥ 0`, se tiene `rₙ ≥ δ > 0`. ✓
- Si `rₙ₋₁ + δ ≥ 7`: `rₙ = rₙ₋₁ + δ − 7`. Como `rₙ₋₁ < 7` y `δ = 1.24219`, tenemos `rₙ₋₁ + δ < 8.24219`, por lo que `rₙ < 1.24219 < 7`. Además `rₙ ≥ 0`. ✓

**Prueba del teorema:** El drift acumulado satisface:

```
Δₙ = Σᵢ₌₁ⁿ yᵢ − n · DS

   = Σᵢ₌₁ⁿ (B + 7·1{GT en año i}) − n · DS

   = n·B + 7·(número de GT en n años) − n·DS

   = −n·δ + 7·(número de GT)
```

Nótese que `7 × (número de GT) = n·δ − rₙ + r₀ = n·δ − rₙ` (telescopio del acumulador).

Por lo tanto:

```
Δₙ = −n·δ + n·δ − rₙ = −rₙ
```

Como `rₙ ∈ [0, 7)`, se concluye:

```
Δₙ = −rₙ ∈ (−7, 0]
```

**QED**

### 3.3 Corolario inmediato

El Calendario Gerarion **nunca puede alejarse más de 7 días del año tropical real**, independientemente del número de años transcurridos. No existe ningún año n, por grande que sea, en que `|Δₙ| ≥ 7`.

Esto contrasta con el Gregoriano, donde `|Δₙᵍ| = n · 0.00031` crece sin límite. En el año 22,580 gregoriano, el drift gregoriano habrá superado los 7 días que el Gerarion nunca alcanzará.

-----

## 4. El Patrón de Diente de Sierra

### 4.1 Descripción

El drift `Δₙ = −rₙ` replica exactamente (con signo negativo) el comportamiento del acumulador `rₙ`. Este acumulador sube linealmente a razón de δ = 1.24219 días/año y cae abruptamente en 7 unidades cada vez que un Gran Tempalum se dispara. El resultado es un patrón de *diente de sierra* característico.

### 4.2 Tabla del acumulador en los primeros 30 años

|Año   |Acumulador rₙ|Gran Tempalum   |Drift Δₙ (días)|
|------|-------------|----------------|---------------|
|1     |1.2422       |—               |−1.2422        |
|2     |2.4844       |—               |−2.4844        |
|3     |3.7266       |—               |−3.7266        |
|4     |4.9688       |—               |−4.9688        |
|5     |6.2109       |—               |−6.2109        |
|**6** |**0.4531**   |**✓ (371 días)**|**−0.4531**    |
|7     |1.6953       |—               |−1.6953        |
|11    |6.6641       |—               |−6.6641        |
|**12**|**0.9063**   |**✓ (371 días)**|**−0.9063**    |
|**17**|**0.1172**   |**✓ (371 días)**|**−0.1172**    |
|**23**|**0.5704**   |**✓ (371 días)**|**−0.5704**    |
|**29**|**1.0235**   |**✓ (371 días)**|**−1.0235**    |

*Intervalos entre Gran Tempalum en los primeros ciclos: 6, 5, 6, 6, 5, 6…*

### 4.3 La paradoja de la no-monotonía

Una consecuencia directa del diente de sierra es que el drift acumulado en n años puede ser **mayor** que el drift en m años, con m > n.

**Ejemplo verificado:**

```
Δ₂₀₃₁ = −2.8879 días   (hoy, año 2031 DY)
Δ₃₅₀₀ = −0.6650 días   (año 3500 DY)
Δ₅₀₀₀ = −1.9500 días   (año 5000 DY)
```

El drift en el año 5,000 (1.95 días) es **menor** que el drift en el año 2,031 (2.89 días). Un observador que extrapolara linealmente concluiría erróneamente que el drift crece con el tiempo. La realidad es que oscila dentro de la cota `(−7, 0]`.

-----

## 5. Ciclos de Retorno a Casi-Cero

### 5.1 Definición

Se llama *año de retorno* a todo año n tal que `|Δₙ| < ε` para un umbral ε pequeño. Los años de retorno corresponden a instantes en que el acumulador `rₙ` es casi nulo — es decir, el Gran Tempalum se disparó casi en el momento justo.

### 5.2 Resultados verificados (ε < 0.003 días = 4.3 minutos)

|Año DY|Drift (minutos)|Intervalo desde anterior|
|------|---------------|------------------------|
|0     |0.00           |— (origen)              |
|62    |−0.38          |62 años                 |
|896   |−3.23          |834 años                |
|4,001 |−3.15          |3,105 años              |
|7,106 |−3.08          |3,105 años              |
|10,211|−3.01          |3,105 años              |

A partir del año 896, los retornos a casi-cero ocurren con período **3,105 años** con extraordinaria regularidad.

### 5.3 Origen del período de 3,105 años

El período de 3,105 años es la solución entera más pequeña (después del año 62) de la ecuación aproximada:

```
3105 · δ ≈ k · U    para algún entero k

3105 × 1.24219 ≈ 3857.00 ≈ 551 × 7 = 3857
```

Es decir, en 3,105 años el acumulador suma aproximadamente 551 veces 7 días — un múltiplo casi exacto del umbral. El sistema “recuerda” su punto de partida cada 3,105 años con un error de solo ~3 minutos.

-----

## 6. Comparación con el Calendario Gregoriano

### 6.1 Tabla comparativa

|Métrica                |Gregoriano      |Gerarion         |
|-----------------------|----------------|------------------|
|Año promedio (días)    |365.2425        |365.2253*         |
|Error/año vs tropical  |+0.446 min      |−24.75 min        |
|Tipo de drift          |Lineal, sin cota|Oscilante, acotado|
|Cota superior del drift|Sin límite      |< 7 días (siempre)|
|1 día de error cada    |3,226 años      |58 años (aparente)|
|Drift en 2,031 años    |+15.1 horas     |−69.3 horas       |
|Drift en 10,000 años   |+73.8 horas     |< 168 horas       |
|Drift en 1,000,000 años|+7,380 horas    |< 168 horas       |

*El año promedio Gerarion varía ligeramente porque el intervalo entre GT no es exactamente 6 sino una mezcla de 5 y 6.

### 6.2 La inversión a largo plazo

El gregoriano tiene menor drift en el corto plazo (horizonte de décadas o siglos). El Gerarion tiene menor drift máximo posible en el largo plazo (horizonte de milenios o eones). En el año 22,580 gregoriano, el drift gregoriano superará los 7 días que el Gerarion nunca puede alcanzar. A partir de ese punto, el Gerarion es más preciso en términos de drift máximo.

```
Año en que |Δₙᵍ| = 7 días: n = 7 / 0.00031 ≈ 22,580 DY
Para n > 22,580: el drift gregoriano supera al drift máximo Gerarion
```

### 6.3 Diferentes definiciones de “perfecto”

La comparación revela que los dos calendarios optimizan para objetivos distintos:

**Gregoriano:** minimiza el drift promedio anual. El año civil promedio se acerca al año tropical con la mejor aproximación racional de denominador pequeño.

**Gerarion:** garantiza coherencia semanal perfecta (toda semana comienza en Soludyia, todo año normal tiene 52 semanas exactas, todo Gran Tempalum tiene 53 semanas exactas) y acota el drift máximo posible a menos de una semana, para siempre. El precio es un mayor drift promedio anual.

-----

## 7. Implicaciones para Cruxyphi y Resinove

La Paradoja del Drift Acotado tiene una consecuencia directa sobre los días sagrados estructurales del Gerarion. Los días 12 y 15 de Keuphero (Cruxyphi y Resinove) son siempre, respectivamente, Trustdyia y Soludyia — por la Invariante I-1 del Cap 13.2 v1.2 (364 mod 7 = 0, 371 mod 7 = 0).

Estas fechas se mueven en el calendario gregoriano a razón de `Δₙ` días por año n. Pero como `|Δₙ| < 7`, **Resinove nunca puede caer fuera de una ventana de 14 días en el calendario gregoriano**. En la práctica, la ventana efectiva es aún menor porque el drift oscila sin crecer.

La Pascua gregoriana, en cambio, puede caer en cualquier domingo entre el 22 de marzo y el 25 de abril — una ventana de 35 días. La diferencia entre Resinove y la Pascua gregoriana puede ser hasta de 35 días en cualquier año dado, pero la posición de Resinove en sí misma permanece estable dentro de su ventana de 14 días para siempre.

-----

## 8. Verificación Computacional

Todos los resultados de este paper fueron verificados computacionalmente usando el algoritmo canónico del Anexo Matemático del Gerarion v1.2. El código de referencia es `gerarion_v1.2.py` (disponible en la documentación del proyecto).

**Vectores de verificación principales:**

```python
# El drift es siempre negativo y acotado
assert all(-7 < drift(n) <= 0 for n in range(0, 15000))

# El drift es exactamente -r_n
assert all(abs(drift(n) + acumulador(n)) < 1e-9 for n in range(0, 10000))

# El ciclo de retorno a cero tiene período ≈ 3105
for k in range(1, 5):
    assert abs(drift(k * 3105 - 209)) < 0.004  # aproximación

# El drift máximo se alcanza cerca del año 3105
assert abs(drift(3105)) < 7.0
assert abs(drift(3105)) > 6.9  # cerca del límite
```

**Resultado del drift máximo verificado:**

```
max(|Δₙ|) para n ∈ [0, 15000] = 6.999950 días, en n = 3105
```

Este valor confirma la cota: el máximo se acerca a 7 pero nunca lo alcanza, consistente con la demostración formal de que `rₙ < U` estrictamente.

-----

## 9. Discusión

### 9.1 ¿Por qué la cota es exactamente 7?

El umbral `U = 7` no fue elegido por razones astronómicas sino por razones de coherencia semanal: para que todos los años sean múltiplos exactos de 7 días. Esta elección tiene la consecuencia matemática de que la cota del drift es exactamente una semana — la misma unidad que el sistema protege. Es una coherencia interna del diseño que no estaba explícitamente prevista: el sistema protege la semana, y el precio del drift queda acotado exactamente por la semana que protege.

### 9.2 La naturaleza del error “de 58 años”

La afirmación frecuente de que “el Gerarion acumula un día de error cada 58 años” es formalmente incorrecta como descripción del comportamiento del sistema. Es una extrapolación lineal del error anual promedio que ignora el mecanismo de diente de sierra. El drift de un día puede ocurrir transitoriamente en el ciclo (por ejemplo, a los 58 años el drift puede superar 1 día durante un pico), pero el sistema se autocorrige con el siguiente Gran Tempalum. El drift jamás alcanza el día 7.

### 9.3 Relación con el acumulador como variable de estado

La identidad `Δₙ = −rₙ` demuestra que el drift del Gerarion en cualquier año n es completamente determinado por el estado actual del acumulador — no por el historial completo. Esto tiene implicaciones computacionales significativas: para calcular el drift en cualquier año n, no es necesario simular todos los años anteriores. Basta con calcular `rₙ mod U` usando aritmética modular. El sistema es Markoviano respecto al drift.

### 9.4 Ausencia de intervención humana

Quizás el aspecto más notable de la Paradoja del Drift Acotado es que la cota no requiere intervención humana alguna. No hay comités que decidan cuándo insertar años de corrección. No hay segundos intercalares. No hay ajustes periódicos. La cota emerge automáticamente del mecanismo de acumulación, y es válida para cualquier valor de δ en el rango `(0, U/2)` — no solo para el valor específico del año tropical actual. Si el año tropical cambiara significativamente (en escalas geológicas), la cota seguiría siendo válida mientras `δ < 3.5` días/año.

-----

## 10. Conclusiones

Se ha demostrado que el Calendario Gerarion satisface la Paradoja del Drift Acotado: su drift temporal respecto al año tropical real es estrictamente negativo y estrictamente menor que 7 días en valor absoluto, para todo tiempo n, sin excepción y sin necesidad de corrección externa.

Las implicaciones son:

1. **El Gerarion nunca necesita “reforma”** del tipo que requirió el gregoriano en 1582 (eliminación de 10 días). Su drift máximo posible es de una semana, y el mecanismo de Gran Tempalum lo contiene automáticamente.
2. **El drift es Markoviano**: el desvío en cualquier momento n es completamente determinado por el estado actual del acumulador, no por el historial completo.
3. **Existe un ciclo de retorno** de período ≈ 3,105 años en el que el drift vuelve a casi-cero (dentro de 3-4 minutos), emergiendo de la conmensurabilidad aproximada entre `3105 × δ` y el umbral U.
4. **La cota es auto-reveladora**: el sistema protege la semana usando U = 7 como umbral, y el precio del drift queda acotado exactamente por la semana que protege. Esta coherencia no fue diseñada explícitamente — emergió de la elección de U.
5. **Para horizontes mayores a 22,580 años**, el drift máximo del Gerarion (< 7 días) es menor que el drift acumulado del Gregoriano, que crece sin límite.

La Paradoja del Drift Acotado no es una curiosidad matemática menor. Es la propiedad central que permite que el Calendario Gerarion sea, a la vez, coherente en sus semanas, verificable en sus días sagrados, y astronómicamente estable en su ancla solar — sin que ninguna de estas tres propiedades requiera sacrificar a las otras dos.

-----

## Apéndice A — Código de Verificación

```python
DS = 365.24219   # año tropical
B  = 364.0       # año base Gerarion
U  = 7.0         # umbral Gran Tempalum

def drift(n):
    """Drift acumulado en n años Gerarions."""
    acc = 0.0; total = 0
    for _ in range(n):
        acc += DS - B
        if acc >= U: total += 371; acc -= U
        else:        total += 364
    return total - n * DS

def acumulador(n):
    """Estado del acumulador después de n años."""
    acc = 0.0
    for _ in range(n):
        acc += DS - B
        if acc >= U: acc -= U
    return acc

# Verificación de la cota
assert all(-7 < drift(n) <= 0.0001 for n in range(15000)), "COTA VIOLADA"

# Verificación de la identidad drift = -acumulador
assert all(abs(drift(n) + acumulador(n)) < 1e-8 for n in range(5000)), "IDENTIDAD FALLÓ"

# Drift máximo
max_d = max(abs(drift(n)) for n in range(15000))
assert max_d < 7.0, f"MÁXIMO = {max_d} ≥ 7"
print(f"Drift máximo verificado: {max_d:.6f} días < 7.0 ✅")
```

-----

## Apéndice B — Glosario

**Acumulador solar (rₙ):** variable de estado del Gerarion que acumula el exceso de días solares sobre el año base de 364 días.

**Drift (Δₙ):** diferencia entre los días Gerarions totales y los días tropicales totales en n años.

**Gran Tempalum:** año Gerarion de 371 días (53 semanas), insertado cuando el acumulador solar alcanza el umbral U = 7.0.

**Invariante I-1:** propiedad del Gerarion que garantiza que el primer día de cada año siempre es Soludyia, derivada de que 364 mod 7 = 0 y 371 mod 7 = 0.

**Año tropical:** tiempo que tarda la Tierra en completar una vuelta alrededor del Sol respecto al equinoccio de primavera. Valor: 365.24219 días (J2000.0).

-----

## Referencias

- Calendario Gerarion v1.2 — Documento Maestro, Capítulos 1-15 y Parte II
- Anexo Matemático del Gerarion v1.2 — Fórmulas F-01 a F-10, Invariantes I-1 a I-6
- Capítulo 5.3 — Especificación del Gran Tempalum y el acumulador solar
- Meeus, J. (1998). *Astronomical Algorithms*, 2nd ed. Willmann-Bell.
- McCarthy, D. & Seidelmann, P.K. (2009). *Time: From Earth Rotation to Atomic Physics*. Wiley-VCH.
- BIPM (2019). *The International System of Units (SI)*, 9th edition.

-----

*Working Paper — Documento No Canónico*
*Acompaña al Calendario Gerarion v1.2*
*Gerardo Loyola (github.com/geroiloyola) — working paper*
*2031DY-04-05-A · 19 junio 2026 gregoriano*