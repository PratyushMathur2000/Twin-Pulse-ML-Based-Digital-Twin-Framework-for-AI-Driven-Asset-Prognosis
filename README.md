# Twin-Pulse: ML-Based Digital Twin Framework for AI-Driven Asset Prognosis

> *Predict before failure. Perform without interruption.*

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://twin-pulse-ml-based-digital-twin-for-ai-driven-asset-prognosis.streamlit.app/)

Twin-Pulse is a Machine Learning-driven Digital Twin framework designed to shift organisations from reactive, time-based maintenance to **proactive, data-driven decision-making**. Using industrial pumps as a case study, the system continuously monitors asset condition through 8 sensor streams, detects non-linear degradation patterns, quantifies risk on a 0–100 index, and estimates Remaining Useful Life (RUL) — all delivered through a comprehensive real-time Streamlit dashboard.

---

## 🎯 Problem Statement

Unplanned equipment failures cause costly downtime, safety risks, and cascading operational disruptions. Traditional maintenance strategies (run-to-failure or fixed-interval servicing) are either too late or wasteful. Twin-Pulse addresses this by building a **virtual representation of physical assets** that provides actionable early warnings 5–30 days before failure.

---

## 🧠 Core ML Pipeline

The system performs **three predictive functions** in a layered analytical pipeline:

### 1. Health Stage Classification (4-Class)
Classifies each pump into: **Healthy → Degrading → Critical → Failure**

| Model | Technique |
|-------|-----------|
| **Soft-Voting Ensemble** | Random Forest (variance reduction) + LightGBM (bias reduction) + Logistic Regression (probability calibration) |

### 2. Remaining Useful Life (RUL) Estimation
Predicts days until likely failure using a **Gradient Boosting Regressor** modeling non-linear degradation velocity.

### 3. Risk Quantification
Converts ML predictions into a managerial **0–100 risk score** with bands: Normal, Watch, Warning, Critical.

---

## 📊 Key Results

| Metric | Value | Interpretation |
|--------|-------|----------------|
| **Classification Accuracy** | **91.08%** | Strong 4-stage health classification |
| **Macro F1 Score** | **0.874** | Balanced performance across imbalanced stages |
| **Failure Recall** | **89.00%** | High sensitivity to critical failure events |
| **RUL MAE** | **1.79 days** | High-precision forecasting |
| **RUL RMSE** | **3.75 days** | Limited outliers and large deviations |
| **±7 Day Accuracy** | **97.48%** | Reliable within the operational decision horizon |
| **Early Warning Window** | **5–30 days** | Consistent actionable lead time before breakdown |

---

## 🖥️ Dashboard Modules

| Module | Description |
|--------|-------------|
| **🏠 Home** | Project presentation viewer and demo video |
| **⚙️ Production Simulator** | Upload CSV sensor data or use synthetic telemetry; multi-pump simulation with auto-play and real-time ML inference |
| **🚀 Fleet Overview** | Executive portfolio view — health stage indicators, risk bands, and asset prioritisation matrix |
| **🔍 Detailed View** | Machine-specific real-time sensor gauges, health status, and RUL estimates |
| **📈 Sensor Trend** | Historical time-series charts, rolling statistics, and threshold visualisation |
| **🔮 Digital Twin Sandbox** | What-if scenario simulation — test maintenance interventions and compare baseline vs. intervention trajectories for risk evolution and RUL |
| **🤖 AI Diagnostic Agent** | *(Requires Local LLM)* Fleet-level insights, root cause analysis, structured maintenance recommendations, and interactive Q&A chat |
| **⚙️ Settings** | 6 colour themes, auto-refresh toggle, and dashboard preferences |

---

## ☁️ Live Demo (Streamlit Cloud)

**[Launch Twin-Pulse Dashboard →](https://twin-pulse-ml-based-digital-twin-for-ai-driven-asset-prognosis.streamlit.app/)**

> **Note:** The AI Diagnostic Agent requires a local LLM server and is unavailable on the cloud deployment. All other modules are fully functional.

---

## 🛠️ Technology Stack

| Category | Technologies |
|----------|-------------|
| **Language** | Python |
| **Data Processing** | Pandas, NumPy |
| **Machine Learning** | Scikit-Learn, LightGBM, XGBoost, Imbalanced-Learn (SMOTE) |
| **Visualisation** | Plotly, Streamlit |
| **Feature Engineering** | 136 engineered features — rolling statistics (48h & 168h), 24h deltas, degradation velocity slopes, lifecycle position |
| **AI Integration** | LM Studio API (Optional — local LLM for diagnostic narratives) |

---

## 📐 Data & Feature Engineering

- **Dataset:** Physics-informed synthetic telemetry simulating **15 industrial pumps** over 6 months (~65,000 hourly observations)
- **Sensor Streams (8):** Radial & Axial Vibration, High-Frequency Vibration, Bearing & Casing Temperature, Discharge Pressure, Power Consumption, Acoustic Emission
- **Lifecycle States:** Healthy → Degrading → Critical → Failure (12 pumps failed, 3 censored)
- **Validation:** Machine-level stratified cross-validation to prevent cross-machine and temporal data leakage
- **Class Imbalance:** Handled via SMOTE oversampling

---

## ⚙️ How to Run Locally

We provide easy-to-use launch scripts that automatically handle dependencies, extract compressed models, and start the dashboard.

**On Windows:**
```
Double-click: Launch_Dashboard (windows).bat
```

**On macOS / Linux:**
```bash
bash "Launch_Dashboad (macOS).sh"
```

**Manual launch:**
```bash
cd project_files
pip install -r requirements.txt
streamlit run App.py
```

> The launch script automatically extracts the `health_stage_ensemble.zip` model file on first run.

---

## 🤖 Enabling the AI Diagnostic Agent

The AI Diagnostic Agent synthesises classification probabilities, risk scores, and RUL predictions into structured, natural-language maintenance recommendations. To enable it:

1. Install [LM Studio](https://lmstudio.ai/)
2. Download a model (e.g., Nemotron 30B, Qwen 14B, or Llama 3)
3. Open LM Studio → **Local Server** tab → Click **Start Server** (runs on `localhost:1234`)
4. The dashboard auto-detects the server and enables AI features

---

## 💰 Estimated Business Impact

| Impact Area | Estimated Benefit |
|-------------|-------------------|
| **Unplanned Downtime Reduction** | 10–20% by scheduling maintenance within the 5–30 day early-warning window |
| **Maintenance Cost Savings** | 5–15% by replacing time-based servicing with condition-based intervention |
| **Safety & Reliability** | 89% failure recall prevents catastrophic breakdowns |
| **Resource Optimisation** | RUL accuracy (MAE 1.79 days) optimises spare parts inventory and crew scheduling |

---

## 📄 Project Report

The full academic project report with detailed methodology, EDA, model evaluation, and business impact analysis is available at [`Project Report.pdf`](Project%20Report.pdf).

---

## 👥 Team — Group 6

| Name | Roll No | SAP ID |
|------|---------|--------|
| Shivani Singh | D003 | 80672500125 |
| Sunidhii Sharma | D005 | 80672500130 |
| Parth Shahi | D011 | 80672500073 |
| Aryan Jain | D012 | 80672500278 |
| Pratyush Mathur | D031 | 80672500059 |
| Abhinav Ranjan | D054 | 80672500260 |

**Institution:** SVKM's NMIMS School of Business Management  
**Program:** MBA – Business Analytics (Trimester III – First Year)  
**Course:** Analytics Project  
**Faculty:** Dr. Rajesh Save  
**Date:** February 2026

---

*For a deeper dive into the methodology, EDA, and business impact, please refer to the [Project Report](Project%20Report.pdf).*
