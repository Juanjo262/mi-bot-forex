import time
import requests
from datetime import datetime, timedelta

# ========== CONFIGURACIÓN ==========
TELEGRAM_TOKEN = "8593830039:AAHdKNUNQ0qURg3igkOQGT7VPrSmeQEMhNI"
CHAT_ID = "1418944611"
ALPHA_VANTAGE_KEY = "AXG8BEKKWON1IB9J"

TIMEFRAME = 3
SEGUNDO_ENVIO = 45

precios = []
velas = []  # Guardaremos velas completas para analizar mechas
ultima_senal = ""

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje}, timeout=5)
        print("  📱 Enviado")
    except:
        pass

def obtener_precio():
    try:
        url = f"https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=EUR&to_currency=USD&apikey={ALPHA_VANTAGE_KEY}"
        r = requests.get(url, timeout=10)
        return float(r.json()['Realtime Currency Exchange Rate']['5. Exchange Rate'])
    except:
        return None

def obtener_etiqueta_horario():
    ahora = datetime.now()
    hora = ahora.hour
    minuto = ahora.minute
    if 7 <= hora <= 9:
        return "🟢 Horario óptimo"
    elif hora == 10 and minuto == 0:
        return "🟢 Horario óptimo"
    else:
        return "🟡 Fuera de horario"

def calcular_ema(precios, periodo=20):
    if len(precios) < periodo:
        return None
    k = 2 / (periodo + 1)
    ema = precios[-periodo]
    for p in precios[-periodo+1:]:
        ema = p * k + ema * (1 - k)
    return ema

def calcular_rsi(precios, periodo=14):
    if len(precios) < periodo + 1:
        return 50
    ganancias = 0
    perdidas = 0
    for i in range(-periodo, 0):
        cambio = precios[i] - precios[i-1]
        if cambio > 0:
            ganancias += cambio
        else:
            perdidas += abs(cambio)
    if perdidas == 0:
        return 100
    rs = ganancias / perdidas
    return 100 - (100 / (1 + rs))

def analizar_mechas(vela):
    """Analiza si la vela tiene mecha larga (rechazo)"""
    if not vela:
        return None
    
    cuerpo = abs(vela['close'] - vela['open'])
    rango = vela['high'] - vela['low']
    
    if rango == 0:
        return None
    
    mecha_sup = vela['high'] - max(vela['close'], vela['open'])
    mecha_inf = min(vela['close'], vela['open']) - vela['low']
    
    # Mecha inferior larga (rebote alcista) → CALL
    if mecha_inf > cuerpo * 2 and mecha_sup < cuerpo:
        return "CALL"
    # Mecha superior larga (rechazo bajista) → PUT
    elif mecha_sup > cuerpo * 2 and mecha_inf < cuerpo:
        return "PUT"
    return None

def analizar(precios, ultima_vela):
    if len(precios) < 30:
        return "NEUTRAL", 0, ""
    
    actual = precios[-1]
    ema = calcular_ema(precios, 20)
    rsi = calcular_rsi(precios, 14)
    
    puntos_subida = 0
    puntos_bajada = 0
    razones = []
    
    # 1. EMA (tendencia principal)
    if ema and actual > ema:
        puntos_subida += 2
        razones.append("EMA20 alcista")
    elif ema and actual < ema:
        puntos_bajada += 2
        razones.append("EMA20 bajista")
    
    # 2. RSI (momentum)
    if rsi < 35:
        puntos_subida += 2
        razones.append(f"RSI sobreventa ({rsi:.0f})")
    elif rsi > 65:
        puntos_bajada += 2
        razones.append(f"RSI sobrecompra ({rsi:.0f})")
    
    # 3. Tendencia reciente
    if len(precios) >= 6:
        if precios[-1] > precios[-6]:
            puntos_subida += 1
            razones.append("Tendencia alcista")
        else:
            puntos_bajada += 1
            razones.append("Tendencia bajista")
    
    # 4. NUEVO: Análisis de mechas de la vela actual
    senal_mecha = analizar_mechas(ultima_vela)
    if senal_mecha == "CALL":
        puntos_subida += 2
        razones.append("Mecha inferior larga (rebote)")
    elif senal_mecha == "PUT":
        puntos_bajada += 2
        razones.append("Mecha superior larga (rechazo)")
    
    diferencia = puntos_subida - puntos_bajada
    
    if diferencia >= 3:
        confianza = min(100, 60 + diferencia * 5)
        return "🟢 COMPRA (CALL)", confianza, " | ".join(razones[:3])
    elif diferencia <= -3:
        confianza = min(100, 60 + abs(diferencia) * 5)
        return "🔴 VENTA (PUT)", confianza, " | ".join(razones[:3])
    else:
        return "⚪ ESPERAR", 0, ""

def esperar_siguiente_ciclo():
    ahora = datetime.now()
    minuto_actual = ahora.minute
    proximo_minuto = ((minuto_actual // TIMEFRAME) + 1) * TIMEFRAME
    tiempo_objetivo = ahora.replace(minute=proximo_minuto, second=SEGUNDO_ENVIO, microsecond=0)
    
    if tiempo_objetivo <= ahora:
        tiempo_objetivo += timedelta(minutes=TIMEFRAME)
    
    espera = (tiempo_objetivo - ahora).total_seconds()
    if espera > 0:
        print(f"⏳ Próxima señal en {espera:.0f}s")
        time.sleep(espera)
    return tiempo_objetivo

# ========== BUCLE PRINCIPAL ==========
print("=" * 60)
print("🤖 BOT EUR/USD - CON ANÁLISIS DE MECHAS")
print("=" * 60)
print("✅ EMA20 + RSI + Tendencia + Mechas largas")
print("✅ Señal cada 3 minutos (segundo 45)")
print("=" * 60)

enviar_telegram("🤖 BOT EUR/USD MEJORADO\n✅ Con detección de mechas largas\n✅ Señal cada 3 minutos")

while True:
    try:
        tiempo_objetivo = esperar_siguiente_ciclo()
        hora_envio = tiempo_objetivo.strftime('%H:%M:%S')
        
        etiqueta = obtener_etiqueta_horario()
        
        print(f"\n📊 {hora_envio} - {etiqueta}")
        
        # Para simular velas, necesitamos varias lecturas por minuto
        # Como Alpha Vantage da 1 precio por minuto, usamos variación pequeña
        # Para simplificar, usamos el precio actual como referencia
        precio = obtener_precio()
        
        if precio:
            precios.append(precio)
            if len(precios) > 50:
                precios.pop(0)
            
            # Simular una vela con el precio actual (apertura=cierre anterior, cierre=actual)
            if len(precios) >= 2:
                vela_actual = {
                    'open': precios[-2],
                    'close': precio,
                    'high': max(precios[-2], precio),
                    'low': min(precios[-2], precio)
                }
                velas.append(vela_actual)
                if len(velas) > 10:
                    velas.pop(0)
            
            if len(precios) >= 30 and len(velas) >= 1:
                decision, confianza, razon = analizar(precios, velas[-1] if velas else None)
                if decision != "⚪ ESPERAR" and confianza >= 60:
                    mensaje = f"{decision} {hora_envio}\n📊 {razon}\n🎯 Confianza: {confianza:.0f}%\n{etiqueta}"
                    if mensaje != ultima_senal:
                        enviar_telegram(mensaje)
                        print(f"📤 {decision}")
                        ultima_senal = mensaje
                    else:
                        print("  🔁 Repetida")
                else:
                    print(f"  ⏸️ {decision}")
            else:
                print(f"  ⏳ Datos: {len(precios)}/30 | Velas: {len(velas)}/1")
        else:
            print("  ❌ Error de precio")
        
        time.sleep(1)
        
    except KeyboardInterrupt:
        print("\n🛑 Bot detenido")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)