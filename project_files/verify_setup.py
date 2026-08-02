import os
import sys
from pathlib import Path
import zipfile

def check_folder_structure():
    """Verify all required folders and files exist."""
    print("🔍 Checking folder structure...")
    
    required_structure = {
        'files': [
            'App.py',
            'requirements.txt',
            'verify_setup.py'
        ],
        'folders': [
            'pages',
            'utils',
            'saved_models'
        ],
        'page_files': [
            'pages/0_Production_Simulator.py',
            'pages/1_Fleet_Overview.py',
            'pages/2_Detailed_View.py',
            'pages/4_Sensor_Trend.py',
            'pages/5_AI_Diagnostic_Agent.py'
        ],
        'utils_files': [
            'utils/data_generator.py',
            'utils/production_simulator.py'
        ],
        'model_files': [
            'saved_models/failure_threshold.pkl',
            'saved_models/health_feature_order.pkl',
            'saved_models/health_stage_ensemble.pkl',
            'saved_models/rul_feature_order.pkl',
            'saved_models/rul_model.pkl'
        ]
    }
    
    missing = []
    warnings = []
    
    # Extract model if zipped
    model_path = 'saved_models/health_stage_ensemble.pkl'
    zip_path = 'saved_models/health_stage_ensemble.zip'
    if not os.path.exists(model_path) and os.path.exists(zip_path):
        print(f"📦 Extracting {zip_path}...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall('saved_models')
            print(f"  ✅ Extracted {model_path}")
        except Exception as e:
            print(f"  ❌ Failed to extract model: {e}")

    # Check root files
    for file in required_structure['files']:
        if not os.path.exists(file):
            missing.append(f"❌ Missing file: {file}")
        else:
            print(f"  ✅ {file}")
    
    # Check folders
    for folder in required_structure['folders']:
        if not os.path.exists(folder):
            missing.append(f"❌ Missing folder: {folder}")
        else:
            print(f"  ✅ {folder}/")
    
    # Check page files
    print("\n  📄 Checking page files...")
    for file in required_structure['page_files']:
        if not os.path.exists(file):
            missing.append(f"❌ Missing page file: {file}")
        else:
            print(f"    ✅ {os.path.basename(file)}")
    
    # Check utils files
    print("\n  🛠️  Checking utils files...")
    for file in required_structure['utils_files']:
        if not os.path.exists(file):
            missing.append(f"❌ Missing utils file: {file}")
        else:
            print(f"    ✅ {os.path.basename(file)}")
    
    # Check model files
    print("\n  🤖 Checking model files...")
    for file in required_structure['model_files']:
        if not os.path.exists(file):
            warnings.append(f"⚠️  Missing model file: {file}")
        else:
            print(f"    ✅ {os.path.basename(file)}")
    
    if missing:
        print("\n🚨 CRITICAL ISSUES FOUND:")
        for item in missing:
            print(f"  {item}")
        return False
    
    if warnings:
        print("\n⚠️  WARNINGS:")
        for item in warnings:
            print(f"  {item}")
        print("\n  Note: You may need to train models first in the Production Simulator.")
    
    if not missing:
        print("\n✅ All required files and folders are present!")
        return True

def check_dependencies():
    """Check if all required packages are installed."""
    print("\n🔍 Checking Python dependencies...")
    
    required_packages = {
        'streamlit': 'streamlit',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'plotly': 'plotly',
        'sklearn': 'scikit-learn',
        'joblib': 'joblib',
        'openai': 'openai'
    }
    
    missing_packages = []
    
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"  ✅ {package_name}")
        except ImportError:
            print(f"  ❌ {package_name} - NOT INSTALLED")
            missing_packages.append(package_name)
    
    return missing_packages

def check_lm_studio():
    """Check if LM Studio is running and has models loaded."""
    print("\n🤖 Checking LM Studio for AI features...")
    
    try:
        import requests
        
        # Check if server is running
        response = requests.get("http://localhost:1234/v1/models", timeout=2)
        
        if response.status_code == 200:
            print("  ✅ LM Studio server is running")
            
            # Check if models are loaded
            data = response.json()
            models = data.get('data', [])
            
            if models:
                print(f"  ✅ {len(models)} model(s) available:")
                for model in models[:3]:  # Show first 3 models
                    model_id = model.get('id', 'Unknown')
                    print(f"     • {model_id}")
                if len(models) > 3:
                    print(f"     • ... and {len(models) - 3} more")
                return True
            else:
                print("  ⚠️  LM Studio is running but NO MODELS LOADED")
                print("     • Open LM Studio")
                print("     • Go to 'Chat' tab")
                print("     • Select a model (e.g., Nemotron 30B)")
                print("     • Wait for model to load")
                print("     • Then start 'Local Server'")
                return False
        else:
            print("  ⚠️  LM Studio server not responding")
            return False
            
    except ImportError:
        print("  ⚠️  'requests' package not installed (needed for LM Studio check)")
        print("     Run: pip install requests")
        return False
    except Exception as e:
        print("  ℹ️  LM Studio not detected (AI features will be unavailable)")
        print("     • Install LM Studio from: https://lmstudio.ai")
        print("     • Download a model (Nemotron 30B recommended)")
        print("     • Load model and start 'Local Server'")
        print(f"     • Debug info: {str(e)}")
        return False

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("🚀 PUMP DASHBOARD V6 - SETUP VERIFICATION")
    print("=" * 60)
    
    # Check Python version
    py_version = sys.version_info
    print(f"\n🐍 Python version: {py_version.major}.{py_version.minor}.{py_version.micro}")
    
    if py_version.major < 3 or (py_version.major == 3 and py_version.minor < 8):
        print("⚠️  Warning: Python 3.8 or higher is recommended!")
    else:
        print("  ✅ Python version is compatible")
    
    # Check folder structure
    print("\n" + "-" * 60)
    structure_ok = check_folder_structure()
    
    # Check dependencies
    print("\n" + "-" * 60)
    missing_deps = check_dependencies()
    
    # Check LM Studio (optional - won't fail setup)
    print("\n" + "-" * 60)
    lm_studio_ok = check_lm_studio()
    
    print("\n" + "=" * 60)
    
    if not structure_ok:
        print("❌ SETUP INCOMPLETE: Missing files or folders")
        print("   Please ensure all required files are in place.")
        print("=" * 60)
        return False
    
    if missing_deps:
        print("⚠️  MISSING DEPENDENCIES:")
        for pkg in missing_deps:
            print(f"   - {pkg}")
        print("\n💡 Dependencies will be installed automatically...")
        print("=" * 60)
        return "install_deps"
    
    # Summary
    print("✅ CORE SETUP COMPLETE - DASHBOARD READY!")
    
    if not lm_studio_ok:
        print("\n⚠️  AI FEATURES NOT AVAILABLE:")
        print("   • All pages will work EXCEPT AI Diagnostic Agent")
        print("   • Start LM Studio with a model to enable AI features")
    else:
        print("\n✅ AI FEATURES ENABLED!")
    
    print("=" * 60)
    return True

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result == True else 1)
