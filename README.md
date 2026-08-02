# Twin-Pulse: ML-Based Digital Twin Framework for AI-Driven Asset Prognosis

*Predict before failure. Perform without interruption.*

Twin-Pulse is a Machine Learning-driven Digital Twin framework designed to shift organizations from reactive maintenance to proactive, data-driven decision-making. By continuously monitoring asset conditions (using industrial pumps as a case study), it detects gradual degradation and estimates failure risk before a breakdown occurs.

## 🚀 Key Features

The system performs three core predictive functions, delivered through a comprehensive multi-page Streamlit dashboard:

1. **Health Stage Classification:** Classifies equipment into four stages (Healthy, Degrading, Critical, Failure) using a Soft-Voting Ensemble model (91.08% Accuracy, 89% Failure Recall).
2. **Remaining Useful Life (RUL) Estimation:** Predicts the remaining days before likely failure using a Gradient Boosting Regressor (MAE of 1.79 days).
3. **Risk Quantification:** Converts predictions into a 0-100 managerial risk score.

### Dashboard Modules
* **Fleet Overview:** Monitor all assets simultaneously using health stage indicators and risk bands to prioritize high-risk machines.
* **Detailed View & Sensor Trend:** Machine-specific analysis, historical sensor behavior, degradation velocity, and RUL estimates.
* **Digital Twin Sandbox:** Simulate maintenance interventions and compare baseline vs. intervention trajectories to evaluate the impact on risk evolution.
* **AI Diagnostic Agent:** (Requires Local LLM / LM Studio) Synthesizes classification probabilities, risk scores, and RUL predictions into structured maintenance recommendations and interactive Q&A.

## ☁️ Run on Streamlit Cloud

[twin-pulse-ml-based-digital-twin-for-ai-driven-asset-prognosis](https://twin-pulse-ml-based-digital-twin-for-ai-driven-asset-prognosis.streamlit.app/Digital_Twin_Sandbox)

## 🛠️ Technology Stack
* **Language:** Python
* **Data Processing:** Pandas, NumPy
* **Machine Learning:** Scikit-Learn, LightGBM, Imbalanced-learn (SMOTE)
* **Web Framework:** Streamlit
* **Local LLM Integration:** LM Studio API (Optional, for AI Diagnostic Agent)

## ⚙️ How to Run Locally

We have provided easy-to-use launch scripts that automatically handle dependencies, extract compressed models, and start the dashboard.

**On Windows:**
Simply double-click the `Launch_Dashboard (windows).bat` file.

**On macOS / Linux:**
Run the shell script from your terminal:
```bash
bash "Launch_Dashboad (macOS).sh"
```

*Note: The launch script will automatically extract the `health_stage_ensemble.zip` model file the first time you run it.*

## 🤖 Enabling the AI Diagnostic Agent
To use the AI Diagnostic Agent tab, you need to run a local language model:
1. Install [LM Studio](https://lmstudio.ai/).
2. Download a model (e.g., Nemotron 30B, Qwen 14B, or Llama 3).
3. Open LM Studio, go to the **Local Server** tab, and click **Start Server** (running on `localhost:1234`).
4. The dashboard will automatically detect the server and enable AI features!

## 👥 Authors (Group 6)
Submitted for the Analytics Project (Trim III - First Year) at NMIMS School of Business Management.
---
*For a deeper dive into the methodology, EDA, and business impact, please refer to the full project report included in the original project files.*
