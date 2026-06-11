import time
import yfinance as yf
import requests
from datetime import datetime, timedelta
import json
import os

# ========== CONFIGURACIÓN ==========
TELEGRAM_TOKEN = "8593830039:AAHdKNUNQ0qURg3igkOQGT7VPrSmeQEMhNI"
CHAT_ID = "1418944611"

TIMEFRAME = 3          # señal cada 3 minutos
SEGUNDO_ENVIO = 45

ARCHIVO_PRECIOS = "precios.json"

precios = []
ultimo_mensaje = ""

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": mensaje}, timeout=5)
        print("  📱 Enviado")
    except:
        pass

def obtener_precio():
    try:
        ticker = yf.Ticker("EURUSD=X")
        datos = ticker.history(period="5m", interval="1m", progress=False)
        if not datos.empty:
            return datos['Close'].iloc[-1]
    except Exception as e:
        print(f"Error precio: {e}")
    return None

def cargar_precios():
    if os.path.exists(ARCHIVO_PRECIOS):
        with open(ARCHIVO_PRECIOS, 'r') as f:
            return json.load(f)
    return []

def guardar_precios(precios):
    with open(ARCHIVO_PRECIOS, 'w') as f:
        json.dump(precios[-60:], f)

def calcular_confianza(precios):
    if len(precios) < 6:
        return 50
    actual = precios[-1]
    hace_3 = precios[-3]
    cambio = abs((actual - hace_3) / hace_3) * 100
    return min(100, 50 + cambio * 10)

def esperar_siguiente_ciclo():
    ahora = datetime.now()
    minuto_actual = ahora.minute
    proximo_minuto = ((minuto_actual // TIMEFRAME) + 1) * TIMEFRAME

    if proximo_minuto == 60:
        tiempo_objetivo = ahora.replace(minute=0, second=SEGUNDO_ENVIO, microsecond=0) + timedelta(hours=1)
    else:
        tiempo_objetivo = ahora.replace(minute=proximo_minuto, second=SEGUNDO_ENVIO, microsecond=0)

    if tiempo_objetivo <= ahora:
        tiempo_objetivo += timedelta(minutes=TIMEFRAME)

    espera = (tiempo_objetivo - ahora).total_seconds()
    if espera > 0:
        print(f"⏳ Próxima señal en {espera:.0f}s")
        time.sleep(espera)
    return tiempo_objetivo

# ========== INICIO ==========
print("🤖 BOT 24/5 (el que funciona 70%)")
print("✅ EUR/USD | Señal cada 3 min en segundo 45")
print("✅ Arranque rápido con precios guardados")

precios = cargar_precios()
print(f"📂 Cargados {len(precios)} precios históricos")

enviar_telegram("🤖 BOT 24/5 ACTIVADO\n✅ Señal cada 3 min\n✅ 70% histórico")

while True:
    try:
        ahora = datetime.now()
        hora = ahora.hour

        if ahora.weekday() >= 5:
            print("🌙 Fin de semana - pausa")
            time.sleep(3600)
            continue

        if not (7 <= hora <= 12):
            print(f"🟡 {ahora.strftime('%H:%M')} - fuera horario óptimo")

        esperar_siguiente_ciclo()
        hora_envio = datetime.now().strftime('%H:%M:%S')

        precio = obtener_precio()
        if precio:
            precios.append(precio)
            if len(precios) > 60:
                precios.pop(0)
            guardar_precios(precios)

            if len(precios) >= 6:
                actual = precios[-1]
                hace_3 = precios[-3]

                if actual > hace_3:
                    decision = "🟢 COMPRA (CALL)"
                else:
                    decision = "🔴 VENTA (PUT)"

                confianza = calcular_confianza(precios)

                msg = f"{decision} {hora_envio}\n🎯 Confianza: {confianza:.0f}%"
                if msg != ultimo_mensaje:
                    enviar_telegram(msg)
                    print(f"📤 {decision}")
                    ultimo_mensaje = msg
                else:
                    print("  🔁 repetida")
            else:
                print(f"⏳ Datos: {len(precios)}/6")
        else:
            print("❌ Error precio")

        time.sleep(1)

    except KeyboardInterrupt:
        print("🛑 Bot detenido")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)