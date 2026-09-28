# Caso comercial: agente de voz para el BPO de AeroAndes

*Estimación para la demo. Todas las cifras son supuestos razonables basados en rangos públicos de 2026; no son datos de un cliente real.*

## El problema del cliente

Un BPO en Colombia atiende la línea telefónica de AeroAndes para pasajeros de cinco países: Colombia, México, Argentina, Chile y Perú. Enfrenta tres problemas:

1. **Costo:** cada llamada de cambio o consulta la atiende un humano, aunque la mayoría son repetitivas (consultar una reserva, cambiar una fecha, preguntar por equipaje).
2. **Picos imposibles de cubrir:** cuando hay irregularidades (clima, cierres de aeropuerto), el volumen se multiplica en horas. No hay forma de contratar y entrenar asesores a esa velocidad.
3. **Experiencia local:** un pasajero mexicano atendido con acento colombiano, o con un español "neutro" robótico, siente que no lo atiende su aerolínea.

## Supuestos

| Supuesto | Valor | Base |
|---|---|---|
| Volumen mensual (5 países) | 100.000 llamadas | Aerolínea regional mediana |
| Costo cargado de un asesor nearshore (Colombia) | USD 15/hora (rango 12–20) | Tarifas públicas de BPO nearshore 2026 |
| Duración promedio de una llamada humana (AHT) | 6 minutos | Llamadas de cambio de vuelo con verificación y espera |
| Ocupación del asesor | 80 % | Referencia típica de contact center |
| Costo del agente de IA por minuto | USD 0,15 (rango 0,12–0,15) | Minuto de ElevenLabs Agents (~USD 0,08–0,10) más LLM y telefonía |
| Duración de la llamada con IA | 4 minutos | Sin tiempos de espera ni transferencias internas |
| Contención (llamadas resueltas sin humano) | 60 % | Supuesto conservador para cambios, consultas y equipaje |

## Resultado

| | Valor |
|---|---|
| Costo por llamada humana | **USD 1,88** (rango 1,50–2,50) |
| Costo por llamada con IA | **USD 0,60** (rango 0,48–0,60) |
| Costo mensual actual (100 % humano) | USD 187.500 |
| Costo mensual con IA (60 % IA, 40 % humano) | USD 111.000 |
| **Ahorro** | **USD 76.500 al mes (≈ USD 918.000 al año), −41 %** |

## El argumento más fuerte: los picos

- En un día normal entran unas 3.300 llamadas, que requieren unos **35 asesores** simultáneos.
- En un día de irregularidad (5 veces el volumen) entrarían unas 16.700 llamadas. Harían falta unos **175 asesores** a la vez: imposible de conseguir en horas.
- El agente de IA escala por concurrencia. Atiende primero a los afectados por la cancelación y deja a los humanos libres para los casos complejos (reembolsos, indemnizaciones, reclamos).

## Más allá del costo

- **Acento local por país:** el agente detecta el país por el prefijo del número y responde con una voz local. Cinco "asesores nativos" desde un solo agente.
- **Atención 24/7** sin turnos nocturnos.
- **Calidad medible:** cada llamada queda con transcripción, evaluación automática y datos extraídos (motivo, resultado, necesidad de seguimiento).
- **Cumplimiento:** el agente nunca recibe datos de tarjeta (paga por enlace SMS) y sigue la política de verificación en el 100 % de las llamadas.

## Cómo contarlo en el video (unos 30 segundos)

> "A Colombian BPO runs AeroAndes' phone line for five countries. Every call costs them about two dollars with a human agent, and when weather cancels flights, call volume jumps five times in a few hours, and they simply can't staff for it. This agent resolves the routine 60 % — lookups, flight changes, baggage — for about 60 cents a call, answers in the caller's local accent, and hands the complex cases to humans with full context."

## Sensibilidad (para responder preguntas)

- Con asesor a USD 12/h y contención del 40 %, el ahorro baja a unos USD 36.000 al mes: el caso se sostiene.
- Con asesor a USD 20/h y contención del 70 %, sube a unos USD 133.000 al mes.
- La variable que más pesa es la **contención**, y por eso se mide con evaluaciones en cada llamada.

## Fuentes de los rangos

- Tarifas de BPO nearshore en Colombia (USD 12–20 por hora de asesor, costo cargado): Fusion CX, Centris, Call Force Global, 2026.
- Precio de ElevenLabs Agents (alrededor de USD 0,08–0,10 por minuto, más LLM y telefonía aparte): guías públicas de precios de 2026. Conviene verificarlo en la página oficial de precios antes de grabar.
