# dashboard.py
# =========================================
# SafeSite — Smart Construction Safety Dashboard (Final + Telegram Alerts)
# Features:
#  - Tabs: Overview, Camera, AI Insights
#  - Live metrics from data.json (sensor_sim)
#  - YOLO webcam helmet detection (Camera tab)
#  - Trend charts + forecast (Prophet if available, else MA)
#  - Interactive map with colored pins + zone polygons
#  - Auto-refresh control
#  - Telegram alerts for high-risk readings
# =========================================

import streamlit as st
import json
import os
import time
import cv2
from ultralytics import YOLO
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from collections import deque
from datetime import datetime, timedelta
import folium
from streamlit_folium import st_folium
from alert_bot import send_alert  # ✅ Telegram alert module

# Try to import Prophet (optional). If not available, fallback to MA forecast.
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except Exception:
    PROPHET_AVAILABLE = False

# ---------- Configuration ----------
DATA_PATH = "data.json"
YOLO_WEIGHTS = "yolov8n.pt"
MAX_HISTORY = 60
FORECAST_STEPS = 12
# -----------------------------------

st.set_page_config(page_title="SafeSite Dashboard", page_icon="🏗️", layout="wide")
st.title("🏗️ SafeSite — Smart Construction Safety Dashboard (with Alerts)")

# ---------------- Sidebar ----------------
with st.sidebar:
    st.header("Controls")
    refresh_rate = st.slider("Auto refresh (seconds)", 1, 10, 3)
    auto_refresh = st.checkbox("Enable auto-refresh (re-runs every interval)", value=True)
    st.write("Camera and AI detection:")
    
    st.divider()
    st.markdown("**Forecasting engine:** " + ("Prophet (advanced)" if PROPHET_AVAILABLE else "Moving-average (fallback)"))
    

# ---------- Helpers ----------
@st.cache_resource(show_spinner=False)
def load_model(path=YOLO_WEIGHTS):
    try:
        return YOLO(path)
    except Exception as e:
        st.error(f"Failed to load YOLO model: {e}")
        return None

def load_data_file():
    if os.path.exists(DATA_PATH):
        try:
            with open(DATA_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def safety_score_from(data):
    temp = data.get("temperature", 0)
    gas = data.get("gas_level", 0)
    helmet = data.get("helmet_violations", 0)
    vib = data.get("vibration", "Normal")
    score = 100
    if temp > 38:
        score -= int((temp - 38) * 2)
    if gas > 400:
        score -= int((gas - 400) / 5)
    score -= helmet * 10
    if vib == "High":
        score -= 10
    return max(0, min(100, score))

def moving_average_forecast(history_list, periods=FORECAST_STEPS, window=5):
    if not history_list:
        return [0] * periods
    vals = list(history_list)
    forecasts = []
    for _ in range(periods):
        w = min(window, len(vals))
        ma = sum(vals[-w:]) / w
        forecasts.append(round(ma, 2))
        vals.append(ma)
    return forecasts

def prophet_forecast(history_times, history_values, periods=FORECAST_STEPS, freq_seconds=3):
    if not PROPHET_AVAILABLE or len(history_times) < 3:
        return None
    try:
        df = pd.DataFrame({"ds": [pd.to_datetime(t) for t in history_times], "y": history_values})
        model = Prophet(daily_seasonality=False, weekly_seasonality=False, yearly_seasonality=False)
        model.fit(df)
        last_time = pd.to_datetime(history_times[-1])
        future = pd.DataFrame({"ds": [last_time + timedelta(seconds=freq_seconds*(i+1)) for i in range(periods)]})
        forecast = model.predict(future)
        return [round(float(v), 2) for v in forecast["yhat"].values]
    except Exception:
        return None

def risk_label(score):
    if score >= 80:
        return "Low"
    if score >= 50:
        return "Moderate"
    return "High"

# ---------- Initialize session history ----------
if "time_history" not in st.session_state:
    st.session_state.time_history = deque(maxlen=MAX_HISTORY)
if "temp_history" not in st.session_state:
    st.session_state.temp_history = deque(maxlen=MAX_HISTORY)
if "gas_history" not in st.session_state:
    st.session_state.gas_history = deque(maxlen=MAX_HISTORY)
if "helmet_history" not in st.session_state:
    st.session_state.helmet_history = deque(maxlen=MAX_HISTORY)
if "last_data_timestamp" not in st.session_state:
    st.session_state.last_data_timestamp = None

# ---------- Load latest data ----------
data = load_data_file()
if data is None:
    temp = gas = helmet = 0
    vibration = "N/A"
    last_updated = "N/A"
else:
    temp = data.get("temperature", 0)
    gas = data.get("gas_level", 0)
    helmet = data.get("helmet_violations", 0)
    vibration = data.get("vibration", "Normal")
    try:
        last_updated = datetime.fromtimestamp(os.path.getmtime(DATA_PATH)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        last_updated = "N/A"
    st.session_state.time_history.append(last_updated)
    st.session_state.temp_history.append(temp)
    st.session_state.gas_history.append(gas)
    st.session_state.helmet_history.append(helmet)
    st.session_state.last_data_timestamp = last_updated

# ---------- ALERT CHECKS ----------
score = safety_score_from({
    "temperature": temp,
    "gas_level": gas,
    "helmet_violations": helmet,
    "vibration": vibration
})

try:
    if score < 50:
        send_alert(f"🚨 CRITICAL: Safety score low ({score})! Immediate action required.")
    elif gas > 400:
        send_alert(f"⚠️ High Gas Detected: {gas} ppm in Zone A.")
    elif temp > 38:
        send_alert(f"🔥 Overheat Risk: {temp}°C detected on site.")
    elif helmet > 0:
        send_alert(f"🪖 Helmet Violation(s) Detected: {helmet}")
except Exception as e:
    st.warning(f"Alert system issue: {e}")

# ---------- Tabs ----------
tabs = st.tabs(["Overview", "Camera", "AI Insights"])

# === Overview tab ===
with tabs[0]:
    st.subheader("Live Safety Overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🌡️ Temperature (°C)", temp)
    c2.metric("🧪 Gas Level (ppm)", gas)
    c3.metric("⛑️ Helmet Violations", helmet)
    c4.metric("⚙️ Vibration", vibration)

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        title={'text': "Site Safety Score"},
        delta={'reference': 80, 'increasing': {'color': "green"}, 'decreasing': {'color': "red"}},
        gauge={'axis': {'range': [0, 100]},
               'bar': {'color': "green" if score > 75 else "orange" if score > 50 else "red"},
               'steps': [
                   {'range': [0, 50], 'color': '#ff6b6b'},
                   {'range': [50, 80], 'color': '#ffd166'},
                   {'range': [80, 100], 'color': '#6be396'}] }
    ))
    st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown("---")
    st.subheader("Trends (recent readings)")
    if len(st.session_state.time_history) >= 1:
        df = pd.DataFrame({
            "time": list(st.session_state.time_history),
            "temperature": list(st.session_state.temp_history),
            "gas": list(st.session_state.gas_history),
            "helmet_violations": list(st.session_state.helmet_history)
        }).set_index("time")
        cola, colb = st.columns(2)
        cola.plotly_chart(px.line(df, y="temperature", title="🌡️ Temperature Trend"), use_container_width=True)
        colb.plotly_chart(px.line(df, y="gas", title="🧪 Gas Level Trend"), use_container_width=True)
        st.plotly_chart(px.line(df, y="helmet_violations", title="⛑️ Helmet Violations Trend"), use_container_width=True)
    else:
        st.info("No trend data yet — start sensor_sim.py to populate values.")

    st.caption(f"Last sensor file update: {st.session_state.get('last_data_timestamp', last_updated)}")

# === Camera tab ===
with tabs[1]:
    st.subheader("Live Camera — Helmet Detection")
    enable_cam = st.checkbox("Enable webcam detection", value=False)
    if enable_cam:
        model = load_model(YOLO_WEIGHTS)
        if model:
            frame_spot = st.empty()
            cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if cap.isOpened():
                start = time.time()
                while time.time() - start < refresh_rate:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    results = model(frame, verbose=False)
                    annotated = results[0].plot()
                    frame_spot.image(annotated, channels="BGR", use_container_width=True)
                cap.release()
                st.success("Camera sampling complete.")
            else:
                st.error("Cannot open webcam.")
    else:
        st.info("Enable webcam to view live helmet detection feed.")

# === AI Insights tab ===
with tabs[2]:
    st.subheader("AI Insights & Forecast")

    temp_hist = list(st.session_state.temp_history)
    gas_hist = list(st.session_state.gas_history)
    helm_hist = list(st.session_state.helmet_history)
    times = list(st.session_state.time_history)

    freq_seconds = max(1, refresh_rate)
    if PROPHET_AVAILABLE:
        temp_forecast = prophet_forecast(times[-30:], temp_hist[-30:], FORECAST_STEPS, freq_seconds) or moving_average_forecast(temp_hist, FORECAST_STEPS)
        gas_forecast = prophet_forecast(times[-30:], gas_hist[-30:], FORECAST_STEPS, freq_seconds) or moving_average_forecast(gas_hist, FORECAST_STEPS)
        helm_forecast = prophet_forecast(times[-30:], helm_hist[-30:], FORECAST_STEPS, freq_seconds) or moving_average_forecast(helm_hist, FORECAST_STEPS)
    else:
        temp_forecast = moving_average_forecast(temp_hist, FORECAST_STEPS)
        gas_forecast = moving_average_forecast(gas_hist, FORECAST_STEPS)
        helm_forecast = moving_average_forecast(helm_hist, FORECAST_STEPS)

    now_ts = datetime.now()
    future_times = [(now_ts + timedelta(seconds=refresh_rate*(i+1))).strftime("%H:%M:%S") for i in range(FORECAST_STEPS)]
    combined_times = (times[-30:] if times else []) + future_times
    combined_temp = (temp_hist[-30:] if temp_hist else []) + temp_forecast
    combined_gas = (gas_hist[-30:] if gas_hist else []) + gas_forecast
    combined_helm = (helm_hist[-30:] if helm_hist else []) + helm_forecast

    df_combined = pd.DataFrame({
        "time": combined_times,
        "temperature": combined_temp,
        "gas": combined_gas,
        "helmet_violations": combined_helm
    }).set_index("time")

    st.plotly_chart(px.line(df_combined, y="temperature", title="Temperature Forecast"), use_container_width=True)
    st.plotly_chart(px.line(df_combined, y="gas", title="Gas Forecast"), use_container_width=True)
    st.plotly_chart(px.line(df_combined, y="helmet_violations", title="Helmet Violations Forecast"), use_container_width=True)

    next_temp = temp_forecast[0] if temp_forecast else temp
    next_gas = gas_forecast[0] if gas_forecast else gas
    next_helm = helm_forecast[0] if helm_forecast else helmet
    predicted_score = safety_score_from({"temperature": next_temp, "gas_level": next_gas, "helmet_violations": next_helm, "vibration": "Normal"})
    st.metric("🧠 Predicted Safety Score", predicted_score, delta=f"{predicted_score - score}")

    label = risk_label(predicted_score)
    if label == "High":
        st.error(f"Predicted Risk: {label} — take immediate action.")
    elif label == "Moderate":
        st.warning(f"Predicted Risk: {label} — monitor closely.")
    else:
        st.success(f"Predicted Risk: {label} — site stable.")

    st.markdown("---")
    st.subheader("🌍 Map View — Sensor Locations & Zones")

    sensors = [
        {"name": "Zone A - Gas Sensor", "lat": 12.9716, "lon": 77.5946, "gas": gas, "temp": temp, "helmet": helmet},
        {"name": "Zone B - Helmet Cam", "lat": 12.9720, "lon": 77.5950, "gas": gas - 50, "temp": temp - 1, "helmet": helmet},
        {"name": "Zone C - Temp Sensor", "lat": 12.9725, "lon": 77.5955, "gas": gas + 40, "temp": temp + 2, "helmet": 0}
    ]

    zones = [
        {"name": "Work Zone 1", "coords": [[12.9714,77.5944],[12.9714,77.5949],[12.9719,77.5949],[12.9719,77.5944]]},
        {"name": "Work Zone 2", "coords": [[12.9721,77.5949],[12.9721,77.5954],[12.9726,77.5954],[12.9726,77.5949]]}
    ]

    center_lat = sum(s["lat"] for s in sensors) / len(sensors)
    center_lon = sum(s["lon"] for s in sensors) / len(sensors)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=17, tiles="OpenStreetMap")

    for i, z in enumerate(zones):
        color = "#ffeda0" if i % 2 == 0 else "#c7e9b4"
        folium.Polygon(locations=z["coords"], color="black", fill=True, fill_color=color, fill_opacity=0.4, tooltip=z["name"]).add_to(m)

    for s in sensors:
        if s["gas"] > 400 or s["temp"] > 38:
            color = "red"
        elif s["gas"] > 300:
            color = "orange"
        else:
            color = "green"
        popup_html = (
            f"<b>{s['name']}</b><br>"
            f"Temperature: {s['temp']} °C<br>"
            f"Gas Level: {s['gas']} ppm<br>"
            f"Helmet Violations: {s['helmet']}"
        )
        folium.CircleMarker(location=[s["lat"], s["lon"]], radius=8, color=color,
                            fill=True, fill_color=color, fill_opacity=0.9,
                            popup=folium.Popup(popup_html, max_width=300)).add_to(m)

    st_folium(m, width=900, height=480)

send_alert("🚨 Test alert from SafeSite dashboard!")
# ---------------- Auto-refresh ----------------
if auto_refresh:
    time.sleep(refresh_rate)
    try:
        st.rerun()
    except Exception:
        st.warning("Auto-refresh unsupported on this Streamlit version.")
