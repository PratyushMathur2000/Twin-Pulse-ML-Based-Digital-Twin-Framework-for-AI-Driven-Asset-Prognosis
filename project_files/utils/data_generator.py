import pandas as pd
import numpy as np

def generate_fleet_data(num_pumps=15):
    """Generate fleet overview data for all pumps"""
    np.random.seed(42)
    statuses = ['Healthy', 'Degrading', 'Critical', 'Failed']
    status_weights = [0.4, 0.35, 0.15, 0.1]
    
    data = []
    for i in range(1, num_pumps + 1):
        status = np.random.choice(statuses, p=status_weights)
        
        # RUL based on status
        if status == 'Healthy':
            rul = np.random.randint(800, 2000)
        elif status == 'Degrading':
            rul = np.random.randint(300, 800)
        elif status == 'Critical':
            rul = np.random.randint(50, 300)
        else:
            rul = 0
        
        # Risk score based on status
        if status == 'Healthy':
            risk = np.random.uniform(0, 30)
        elif status == 'Degrading':
            risk = np.random.uniform(30, 60)
        elif status == 'Critical':
            risk = np.random.uniform(60, 85)
        else:
            risk = np.random.uniform(85, 100)
        
        data.append({
            'Pump_ID': f'Pump {i:02d}',
            'Status': status,
            'RUL_hours': rul,
            'Risk_Score': round(risk, 1)
        })
    
    return pd.DataFrame(data)


def generate_sensor_data(pump_id):
    """Generate sensor readings for a specific pump"""
    np.random.seed(hash(pump_id) % 1000)
    
    sensors = {
        'Sensor 1 - Temperature': np.random.uniform(50, 100),
        'Sensor 2 - Vibration': np.random.uniform(0, 10),
        'Sensor 3 - Pressure': np.random.uniform(50, 150),
        'Sensor 4 - Flow Rate': np.random.uniform(10, 100),
        'Sensor 5 - Power': np.random.uniform(0, 100),
        'Sensor 6 - RPM': np.random.uniform(1000, 3000),
        'Sensor 7 - Bearing Temp': np.random.uniform(40, 90),
        'Sensor 8 - Seal Condition': np.random.uniform(0, 100)
    }
    
    return sensors


def get_sensor_ranges():
    """Define health ranges for each sensor
    Returns dict with sensor name and ranges for [healthy, degrading, critical, failed]
    """
    return {
        'Sensor 1 - Temperature': {
            'min': 0, 'max': 120,
            'healthy': [0, 70],
            'degrading': [70, 85],
            'critical': [85, 100],
            'failed': [100, 120]
        },
        'Sensor 2 - Vibration': {
            'min': 0, 'max': 15,
            'healthy': [0, 3],
            'degrading': [3, 6],
            'critical': [6, 10],
            'failed': [10, 15]
        },
        'Sensor 3 - Pressure': {
            'min': 0, 'max': 200,
            'healthy': [0, 100],
            'degrading': [100, 130],
            'critical': [130, 160],
            'failed': [160, 200]
        },
        'Sensor 4 - Flow Rate': {
            'min': 0, 'max': 120,
            'healthy': [60, 120],
            'degrading': [40, 60],
            'critical': [20, 40],
            'failed': [0, 20]
        },
        'Sensor 5 - Power': {
            'min': 0, 'max': 120,
            'healthy': [0, 70],
            'degrading': [70, 85],
            'critical': [85, 100],
            'failed': [100, 120]
        },
        'Sensor 6 - RPM': {
            'min': 0, 'max': 3500,
            'healthy': [2000, 3500],
            'degrading': [1500, 2000],
            'critical': [1000, 1500],
            'failed': [0, 1000]
        },
        'Sensor 7 - Bearing Temp': {
            'min': 0, 'max': 110,
            'healthy': [0, 60],
            'degrading': [60, 75],
            'critical': [75, 90],
            'failed': [90, 110]
        },
        'Sensor 8 - Seal Condition': {
            'min': 0, 'max': 100,
            'healthy': [70, 100],
            'degrading': [50, 70],
            'critical': [30, 50],
            'failed': [0, 30]
        }
    }
