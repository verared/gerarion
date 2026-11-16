/** runbook del notario GUS en producción
 *
 * (documento operacional — capa 2; el protocolo normativo está en
 * docs/spec/gus-2.0.md §8 y en src/gerarion/notary_cluster.py)
 */

# Runbook del notario GUS en producción

Objetivo: operar el quórum k-de-n de réplicas del notario diario con todas
las garantías del modelo de amenazas: ninguna réplica puede reescribir el
pasado sin que el quórum (y la publicación externa) detecten la divergencia.

## 1. Parámetros del despliegue

| Parámetro | Mínimo recomendado | Nota |
|---|---|---|
| Réplicas n | 5 | en 3 jurisdicciones ó proveedores distintos |
| Quórum k | 3 (mayoría) | `threshold = n//2 + 1` por defecto |
| Sellado | diario, al cierre LC/SC | orden estricto 0,1,2,... |
| Publicación | al menos 2 canales independientes | release de GitHub + espejo (IPFS/HDD externo/auditor) |
| Retención | ≥ 10 años | el chain head reconstruye todo |

## 2. Ceremonia de claves (solo primera vez)

1. Reunir a exactamente las personas del quórum (mín. 2 testigos fuera).
2. En cada réplica: generar claves SLH-DSA (FIPS 205) 128f con RNG del SO;
   grabar las llaves públicas.
3. Construir el **trust root**: `tools/trust_root.py create` produce un JSON
   con las réplicas, sus llaves públicas, el umbral k y la versión GUS; se
   firma con la clave de ceremonia (SLH-DSA).
4. Publicar el trust root firmado en los 2+ canales. Los consumidores
   arrancan SIEMPRE desde este archivo: es la única raíz de confianza.
5. Guardar el archivo transcript (video/hashes) de la ceremonia junto al
   trust root.

## 3. Operación diaria

Fanout: el emisor de marcas envía cada payload a TODAS las réplicas en el
mismo orden (`POST /receive`). Al cierre del día: `POST /seal` en cada
réplica y publicación de su `day_root` en los canales. Un consumidor verifica:

```
PYTHONPATH=src python3 -c "from gerarion.notary_cluster import verify_bundle; ..."
```

Reglas operacionales:

- Ningún día se salta: los días vacíos TAMBIÉN se sellan (raíz vacía
  definida) — impide inflar silenciosamente huecos.
- `verify_chain` local en cada réplica después de cada sellado.
- Monitoreo: alarma si (a) alguna réplica no publica en la ventana, (b) dos
  réplicas honestas difieren en `day_root`, (c) `self_check` falla.

## 4. Rotación de claves del firmante (por época)

1. Cada árbol de firmas (por defecto 2^8 hojas) se rota ANTES de agotarse.
2. La nueva clave pública se publica firmada por la clave saliente
   (cadena de confianza) y anclada `POST /receive` a todas las réplicas
   el mismo día del cambio.
3. La clave saliente se archiva para verificación histórica; jamás vuelve a
   firmar. Un intento de reuso debe disparar alarma.

## 5. Revocación y respuesta a incidentes

Clave comprometida (o sospecha):
1. Detener la firma inmediatamente; publicar aviso firmado por el trust root
   de ceremonia con el día GUS de corte.
2. Divergencia detectada (raíz distinta): el quórum declara inválida a las
   réplicas divergentes (`divergent` del `verify_bundle`); se reemplazan con
   réplicas nuevas reconstruidas desde el log del quórum.
3. Todo cambio se ancla en el día en curso: la cadena lo deja registrado.

Replica comprometida pero dentro del quórum (n/2): el ataque es detectable
solo por observadores externos — por eso los 2+ canales de PUBLICACIÓN
externos son OBLIGATORIOS, no opcionales.

## 6. Rotación del trust root (crisis)

Solo aceptable tras pérdida de quórum o colapso total. Mismo proceso de
ceremonia (2), con dos anclas extra: (a) firma del ANTERIOR trust root
(aunque sea sospechado) sobre el nuevo, (b) sello del nuevo trust root en
cada canal externo. El anterior NUNCA se borra: los consumidores antiguos
pueden reconstruir la cadena.

## 7. Puentes con infraestructura existente

- **RFC 3161**: el payload de una marca GST puede enviarse a cualquier TSA
  RFC 3161 como hora secundaria (dual-timestamping). El sello TSA obtenido
  se almacena junto a la GST como evidencia adicional, no sustituye el
  anclaje del notario.
- **OpenTimestamps**: `tools/ots_bridge.py` sella el hash del día
  (`day_root`) en la blockchain de Bitcoin vía OTS; el .ots resultante
  publica por los mismos canales que las raíces diarias.
- Ambos puentes son posteriores en la cadena de confianza (GUS primero); un
  puente roto no invalida el notario: su único costo es menos canales.

## 8. Despliegue reproducible

```
cd deploy
docker compose up --build          # 3 réplicas en puertos 8081-8083
curl localhost:8081/health
```

Systemd (bare metal): unit template `systemd/gus-notary@.service`:

```
systemctl enable --now gus-notary@alpha
journalctl -u gus-notary@alpha -f
```

Checklist final de adopción de una réplica nueva: trust root verificada,
`/health` reporta `chain_head_valid: true`, se cubre el monitoreo del §3.
