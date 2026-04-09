# Telecom Cloud Intelligence - Notebooks

AI Operations Agent notebooks for CEM-CVM Intelligence.

## Setup

### Virtual Environment

The project uses a shared virtual environment at the project root:

```
telecom-cloud-intelligence/
├── .venv/                    # Virtual environment (created by VS Code)
├── notebooks/                # This directory
├── services/                 # Backend services
└── dashboard/                # Frontend
```

**All dependencies are pre-installed in `.venv/`** - no separate venv needed.

### Selecting the Kernel in VS Code

1. Open any notebook (e.g., `01_data_preparation_eda.ipynb`)
2. Click the kernel selector in the top-right corner
3. Select **"Telecom AI (Python 3.11)"**
4. VS Code will use the pre-installed packages from `.venv/`

### Available Kernels

| Kernel Name | Python Path | Use Case |
|-------------|-------------|----------|
| Telecom AI (Python 3.11) | `.venv/bin/python` | This project |
| python3 | System default | General Python |

## Notebooks

| Notebook | Purpose |
|----------|---------|
| `01_data_preparation_eda.ipynb` | Data generation, EDA, feature engineering |
| `02_sla_risk_model.ipynb` | SLA Risk model training (GradientBoosting) |
| `03_anomaly_detection_models.ipynb` | OSS/BSS anomaly detection (IsolationForest) |

## Dependencies

All packages are in `requirements.txt` and installed in `.venv/`:

```
numpy==2.0.1
pandas==2.2.2
matplotlib==3.9.2
seaborn==0.13.2
scikit-learn==1.5.2
joblib==1.4.2
scipy==1.14.1
ipykernel==6.29.5
jupyter==1.1.1
notebook==7.2.2
```

## Directory Structure

```
notebooks/
├── .gitignore              # Git exclusions
├── README.md               # This file
├── requirements.txt        # Dependencies list
├── 01_data_preparation_eda.ipynb
├── 02_sla_risk_model.ipynb
├── 03_anomaly_detection_models.ipynb
├── models/                 # Trained model artifacts (.joblib)
└── data/                   # Generated data (git-ignored)
    ├── *.png               # Visualization outputs
    ├── *.csv               # Sample datasets
    └── *.npz               # Training data arrays
```

## Common Tasks

### Re-run All Cells
- VS Code: Select "Restart & Run All" from the notebook toolbar

### Install New Package
```bash
source .venv/bin/activate
pip install <package>
pip freeze > requirements.txt  # Update requirements
```

### Check Package Versions
```bash
.venv/bin/pip list | grep -E "numpy|pandas|scikit"
```

## Troubleshooting

### Kernel Not Found
```bash
# Re-register the kernel
.venv/bin/python -m ipykernel install --user --name=telecom-ai --display-name="Telecom AI (Python 3.11)"
```

### Import Errors
```bash
# Verify packages are installed
.venv/bin/pip install -r requirements.txt
```
