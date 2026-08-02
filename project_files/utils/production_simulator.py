import numpy as np
import pandas as pd
from scipy.stats import linregress
import joblib
import os

# In-memory cache for simulator instances to avoid re-loading models on every rerun
_SIM_CACHE = {}

# ============================================================
# RISK SCORING ENGINE (EXACT COPY FROM JUPYTER)
# ============================================================

class RiskScoreEngine:
    """
    Four-component risk scorer + EWMA smoother.
    EXACT copy from Jupyter production_simulator.py
    """

    def __init__(self, buffer_size: int = 168, ewma_alpha: float = 0.3,
                 max_step_change: int = 20):
        self.buffer_size      = buffer_size
        self.ewma_alpha       = ewma_alpha
        self.max_step_change  = max_step_change
        self.machine_buffers  = {}           # {machine_id: DataFrame}

        self.base_risk_map = {0: 0, 1: 20, 2: 35, 3: 50}

        self.risk_bands = {
            (0,  20): "Normal",
            (21, 40): "Watch",
            (41, 70): "Warning",
            (71, 100): "Critical",
        }

        self.sensors = [
            "radial_vibration_rms", "axial_vibration_rms",
            "high_freq_vibration",  "bearing_temperature",
            "casing_temperature",   "discharge_pressure",
            "power_consumption",    "acoustic_emission",
        ]

    def _compute_raw_risk(self, row, latched_health=None):
        """Return (raw_score, dominant_sensor_list)."""
        state = latched_health if latched_health is not None else int(row["predicted_health_state"])
        base  = self.base_risk_map.get(state, 0)

        # probability-weighted expected severity (0-20)
        probs            = row["class_probabilities"]
        max_class        = len(probs) - 1
        expected_sev     = sum(i * p for i, p in enumerate(probs))
        prob_contrib     = (expected_sev / max_class) * 20 if max_class > 0 else 0.0

        # trend acceleration (0-20)
        accel   = 0
        dominant = []
        for s in self.sensors:
            s48  = row.get(f"{s}_slope_48h", 0)
            s168 = row.get(f"{s}_slope_168h", 0)
            std  = row.get(f"{s}_std_48h", 0)
            if s168 > 0 and s48 > s168 and std > 0:
                accel += 1
                dominant.append((s, s48))

        trend_contrib = min(accel * 2.5, 20.0)

        # persistence (0-10)
        persist_contrib = row.get("dwell_fraction", 0.0) * 10.0

        raw = base + prob_contrib + trend_contrib + persist_contrib

        # hard escalation floor for failure
        if state >= 3 or (len(probs) > 3 and probs[3] > 0.5):
            raw = max(raw, 85.0)

        return min(max(raw, 0.0), 100.0), dominant

    def _smooth(self, current: float, previous):
        """EWMA + step-cap."""
        if previous is None:
            return int(round(current))
        smoothed = self.ewma_alpha * current + (1 - self.ewma_alpha) * previous
        delta    = smoothed - previous
        if abs(delta) > self.max_step_change:
            smoothed = previous + np.sign(delta) * self.max_step_change
        return int(min(max(round(smoothed), 0), 100))

    def _band(self, score: int) -> str:
        for (lo, hi), name in self.risk_bands.items():
            if lo <= score <= hi:
                return name
        return "Critical"

    def process_stream(self, row, latched_health=None) -> dict:
        """
        EXACT copy from Jupyter.
        Ingest one row (dict / Series) with ALL engineered features.
        """
        machine_id = row["machine_id"]

        # initialise buffer if first call for this machine
        if machine_id not in self.machine_buffers:
            self.machine_buffers[machine_id] = pd.DataFrame()

        new_row = pd.DataFrame([row])
        buf = pd.concat([self.machine_buffers[machine_id], new_row],
                        ignore_index=True).tail(self.buffer_size)
        self.machine_buffers[machine_id] = buf

        # persistence: fraction of buffer in state >= 1
        dwell = (buf["predicted_health_state"] >= 1).mean()
        new_row.loc[new_row.index[0], "dwell_fraction"] = dwell

        # raw risk
        raw, dom_list = self._compute_raw_risk(new_row.iloc[0],
                                               latched_health=latched_health)

        # smooth using previous score stored in buffer
        prev = None
        if "risk_score" in buf.columns and len(buf) > 1:
            prev = buf["risk_score"].iloc[-2]
        score = self._smooth(raw, prev)

        # derive outputs
        dom_names = [d[0] for d in sorted(dom_list, key=lambda x: x[1], reverse=True)[:3]]
        band      = self._band(score)

        # persist score back into buffer for next call
        if "risk_score" not in buf.columns:
            buf["risk_score"] = np.nan
        buf.at[buf.index[-1], "risk_score"] = score
        self.machine_buffers[machine_id] = buf

        return {
            "risk_score":            score,
            "risk_band":             band,
            "dominant_contributors": dom_names,
        }


# ============================================================
# PUMP SIMULATOR
# ============================================================

class PumpSimulator:
    """Loads saved models and processes sensor data row by row."""
    
    ALL_SENSORS = [
        "radial_vibration_rms", "axial_vibration_rms",
        "high_freq_vibration", "bearing_temperature",
        "casing_temperature", "discharge_pressure",
        "power_consumption", "acoustic_emission",
    ]
    
    RUL_SLOPE_SENSORS = [
        "radial_vibration_rms", "axial_vibration_rms",
        "high_freq_vibration", "bearing_temperature",
        "power_consumption",
    ]
    
    HEALTH_LABELS = {0: "Healthy", 1: "Degrading", 2: "Critical", 3: "Failure"}
    
    def _rul_band(self, rul: float) -> str:
        if rul <= 0:
            return "Imminent (≤ 0 days)"
        if rul <= 10:
            return "Short-term (< 10 days)"
        if rul <= 30:
            return "Medium-term (10–30 days)"
        return "Long-term (> 30 days)"
    
    def __init__(self, models_folder: str, pump_id: str):
        self.pump_id = pump_id
        self.models_folder = models_folder
        
        self.classifier = joblib.load(os.path.join(models_folder, "health_stage_ensemble.pkl"))
        self.health_feat_order = joblib.load(os.path.join(models_folder, "health_feature_order.pkl"))
        
        thresh_path = os.path.join(models_folder, "failure_threshold.pkl")
        self.failure_threshold = joblib.load(thresh_path) if os.path.exists(thresh_path) else 0.5
        
        self.rul_model = joblib.load(os.path.join(models_folder, "rul_model.pkl"))
        self.rul_feat_order = joblib.load(os.path.join(models_folder, "rul_feature_order.pkl"))
        
        self.risk_engine = RiskScoreEngine()
        
        self.buffer = pd.DataFrame()
        self.buffer_max = 168
        self.latched_health = 0
        self.last_rul = None
        
        self.first_timestamp = None
        self.risk_history = []
        self.rul_raw_buffer = []
        
        self.log = []
    
    def _engineer_features(self, current_row: pd.DataFrame) -> pd.Series:
        """Append current_row to buffer and compute all features."""
        self.buffer = pd.concat([self.buffer, current_row], ignore_index=True)
        self.buffer = self.buffer.tail(self.buffer_max)
        
        features = {}
        
        for s in self.ALL_SENSORS:
            features[s] = current_row[s].iloc[0]
        
        for s in self.ALL_SENSORS:
            if len(self.buffer) >= 25:
                features[f"{s}_delta_24h"] = (
                    self.buffer[s].iloc[-1] - self.buffer[s].iloc[-25]
                )
            else:
                features[f"{s}_delta_24h"] = 0.0
        
        for window in (48, 168):
            for s in self.ALL_SENSORS:
                series = self.buffer[s].tail(window)
                
                features[f"{s}_mean_{window}h"] = series.mean()
                features[f"{s}_std_{window}h"] = series.std() if len(series) > 1 else 0.0
                features[f"{s}_min_{window}h"] = series.min()
                features[f"{s}_max_{window}h"] = series.max()
                features[f"{s}_range_{window}h"] = series.max() - series.min()
                
                if len(series) > 1:
                    x = np.arange(len(series))
                    slope, _, _, _, _ = linregress(x, series.values)
                    features[f"{s}_slope_{window}h"] = slope
                else:
                    features[f"{s}_slope_{window}h"] = 0.0
        
        return pd.Series(features)
    
    def _predict_health(self, features: pd.Series):
        """Returns (latched_health_state: int, class_probs: ndarray)."""
        X = pd.DataFrame([features])[self.health_feat_order]
        
        raw_pred = int(self.classifier.predict(X)[0])
        probs = self.classifier.predict_proba(X)[0]
        
        if len(probs) > 3 and probs[3] >= self.failure_threshold:
            raw_pred = 3
        
        health = max(self.latched_health, raw_pred)
        self.latched_health = health
        
        return health, probs
    
    def _predict_rul(self, probs, features: pd.Series, risk_score: int, elapsed_days: float) -> float:
        """Returns smoothed, monotonically-decreasing RUL in days."""
        if self.latched_health == 0:
            self.last_rul = None
            return np.nan
        
        if self.latched_health >= 3:
            self.last_rul = 0.0
            return 0.0
        
        # Build RUL feature vector (EXACT Jupyter logic)
        rul_row = {
            "risk_score": risk_score,
            "prob_1":     float(probs[1]) if len(probs) > 1 else 0.0,
            "prob_2":     float(probs[2]) if len(probs) > 2 else 0.0,
            "prob_3":     float(probs[3]) if len(probs) > 3 else 0.0,
            "elapsed_lifetime_days": elapsed_days,
            "risk_accel_48h": self._compute_risk_accel(),
        }
        
        for s in self.RUL_SLOPE_SENSORS:
            rul_row[f"{s}_slope_48"] = features.get(f"{s}_slope_48h", 0.0)
        
        rul_df = pd.DataFrame([rul_row])
        for col in self.rul_feat_order:
            if col not in rul_df.columns:
                rul_df[col] = 0.0
        rul_df = rul_df[self.rul_feat_order]
        
        raw_rul = max(0.0, float(self.rul_model.predict(rul_df)[0]))
        
        # Smoothing (EXACT Jupyter logic)
        self.rul_raw_buffer.append(raw_rul)
        if len(self.rul_raw_buffer) > 24:
            self.rul_raw_buffer = self.rul_raw_buffer[-24:]
        smoothed = np.mean(self.rul_raw_buffer)
        
        if self.last_rul is not None:
            rul = min(self.last_rul, smoothed)
        else:
            rul = smoothed
        
        rul = max(rul, 0.0)
        self.last_rul = rul
        
        return rul
    
    def _compute_risk_accel(self) -> float:
        """Compute risk acceleration using linregress (EXACT Jupyter logic)."""
        if len(self.risk_history) < 2:
            return 0.0
        x = np.arange(len(self.risk_history))
        slope, _, _, _, _ = linregress(x, self.risk_history)
        return slope
    
    def _compose_comment(self, health_state, risk_score, risk_band, rul_days, dominant_sensors):
        """Generate natural language comment (EXACT Jupyter logic)."""
        if health_state == 0:
            return "All parameters within normal operating limits. No action required."
        
        dom_str = " and ".join(dominant_sensors) if dominant_sensors else "general sensor drift"
        
        if health_state == 1:
            if rul_days is None or np.isnan(rul_days):
                rul_text = "N/A"
            elif rul_days > 30:
                return (f"Early degradation detected in {dom_str}. "
                        f"Risk is {risk_band.lower()}. Continue monitoring; "
                        f"schedule routine inspection within {rul_days:.0f} days.")
            else:
                return (f"Degradation progressing in {dom_str}. "
                        f"Risk: {risk_band.lower()} (score {risk_score}/100). "
                        f"Maintenance recommended within {rul_days:.0f} days.")
        
        elif health_state == 2:
            rul_text = f"~{rul_days:.1f}" if not (rul_days is None or np.isnan(rul_days)) else "N/A"
            return (f"Critical condition — accelerating degradation driven by {dom_str}. "
                    f"Risk score {risk_score}/100 ({risk_band.lower()}). "
                    f"Estimated time to failure: {rul_text} days. "
                    f"Urgent inspection and maintenance planning required.")
        
        elif health_state == 3:
            return (f"FAILURE STATE DETECTED. {dom_str} have breached safety thresholds. "
                    f"Immediate shutdown and maintenance intervention required.")
        
        return ""
    
    def process_streaming_row(self, row_df: pd.DataFrame) -> dict:
        """Process ONE raw sensor row (EXACT Jupyter pipeline)."""
        ts = row_df["timestamp"].iloc[0]
        
        if self.first_timestamp is None:
            self.first_timestamp = ts
        
        elapsed_days = (ts - self.first_timestamp).total_seconds() / 86400.0
        
        # 1) Engineer features
        features = self._engineer_features(row_df)
        
        # 2) Predict health
        health_state, probs = self._predict_health(features)
        
        # 3) Build COMPLETE risk input (like Jupyter does)
        risk_input = {
            "machine_id": self.pump_id,
            "predicted_health_state": health_state,
            "class_probabilities": probs.tolist(),
        }
        
        # Add ALL engineered features to risk_input
        for key, val in features.items():
            risk_input[key] = val
        
        # 4) Compute risk using process_stream (EXACT Jupyter method)
        risk_out = self.risk_engine.process_stream(
            pd.Series(risk_input),
            latched_health=health_state
        )
        
        # Track risk history for RUL
        self.risk_history.append(risk_out["risk_score"])
        if len(self.risk_history) > 48:
            self.risk_history = self.risk_history[-48:]
        
        # 5) Predict RUL
        rul_days = self._predict_rul(probs, features, risk_out["risk_score"], elapsed_days)
        
        # 6) Compose comment
        comment = self._compose_comment(
            health_state,
            risk_out["risk_score"],
            risk_out["risk_band"],
            rul_days,
            risk_out["dominant_contributors"]
        )
        
        # 7) Build log entry
        log_entry = {
            "timestamp": ts,
            "predicted_health_state": health_state,
            "health_label": self.HEALTH_LABELS[health_state],
            "risk_score": risk_out["risk_score"],
            "risk_band": risk_out["risk_band"],
            "rul_days": round(rul_days, 2) if not (rul_days is None or np.isnan(rul_days)) else None,
            "rul_band": self._rul_band(rul_days) if not (rul_days is None or np.isnan(rul_days)) else "N/A",
            "dominant_sensors": "; ".join(risk_out["dominant_contributors"]) if risk_out["dominant_contributors"] else "—",
            "comment": comment,
        }
        
        self.log.append(log_entry)
        
        return log_entry


def get_simulator(models_folder: str, pump_id: str) -> PumpSimulator:
    """Return a cached PumpSimulator instance or create one if missing.

    This avoids repeatedly loading joblib models during Streamlit reruns.
    """
    key = (os.path.abspath(models_folder), str(pump_id))
    if key not in _SIM_CACHE:
        _SIM_CACHE[key] = PumpSimulator(models_folder, pump_id)
    return _SIM_CACHE[key]
