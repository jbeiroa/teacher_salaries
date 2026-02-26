import pytest
import pandas as pd
import numpy as np
import os
from src.salary_data.analytics import AnalyticsPipeline

@pytest.fixture
def sample_real_salary():
    """Create a sample real salary DataFrame for testing."""
    dates = pd.date_range(start='2023-01-01', periods=12, freq='MS')
    provinces = ['Prov1', 'Prov2', 'Prov3']
    data = {
        'Prov1': np.linspace(100, 110, 12),
        'Prov2': np.linspace(100, 90, 12),
        'Prov3': [100, 105, 110, 105, 100, 95, 90, 95, 100, 105, 110, 105]
    }
    return pd.DataFrame(data, index=dates)

def test_prepare_data(sample_real_salary):
    pipeline = AnalyticsPipeline()
    X_scaled = pipeline.prepare_data(sample_real_salary)
    
    # Shape: (n_provinces, n_dates, 1) for tslearn
    assert X_scaled.shape == (3, 12, 1)
    # Scaled data should have mean approx 0 and std approx 1
    assert np.isclose(X_scaled.mean(), 0, atol=1e-5)

def test_train_clustering(sample_real_salary):
    pipeline = AnalyticsPipeline()
    ks_model, labels = pipeline.train_clustering(sample_real_salary, n_clusters=2)
    
    assert len(labels) == 3
    assert set(labels).issubset({0, 1})
    assert ks_model is not None

def test_train_anomaly_detection(sample_real_salary):
    pipeline = AnalyticsPipeline()
    # Add a massive anomaly to Prov1
    sample_real_salary.iloc[6, 0] = 500.0 
    
    df_anomalies = pipeline.train_anomaly_detection(sample_real_salary)
    assert df_anomalies.shape == sample_real_salary.shape
    # Anomaly should be -1
    assert -1 in df_anomalies['Prov1'].values

def test_load_latest_artifacts_local(tmp_path, monkeypatch):
    """Test that it loads from local artifacts folder if files exist."""
    # Create temp artifacts dir
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()
    
    df_c = pd.DataFrame({"province": ["A"], "cluster": [0]})
    df_a = pd.DataFrame({"date": ["2023-01-01"], "province": ["A"], "anomaly": [1]})
    
    df_c.to_parquet(artifacts_dir / "clusters.parquet")
    df_a.to_parquet(artifacts_dir / "anomalies.parquet")
    
    # Change CWD to tmp_path so it finds artifacts/
    monkeypatch.chdir(tmp_path)
    
    pipeline = AnalyticsPipeline()
    loaded_c, loaded_a = pipeline.load_latest_artifacts(local_first=True)
    
    assert loaded_c is not None
    assert loaded_a is not None
    assert loaded_c.iloc[0]["province"] == "A"
