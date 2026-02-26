import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from tslearn.clustering import KShape
from tslearn.preprocessing import TimeSeriesScalerMeanVariance
from sklearn.ensemble import IsolationForest
import os

class AnalyticsPipeline:
    def __init__(self, experiment_name="Teacher_Salaries_Analytics", db_uri="sqlite:///mlflow.db"):
        self.experiment_name = experiment_name
        self.db_uri = db_uri
        mlflow.set_tracking_uri(self.db_uri)
        mlflow.set_experiment(self.experiment_name)
    
    def prepare_data(self, df_real):
        """Prepare data for clustering by scaling."""
        # df_real: Index = Dates, Columns = Provinces
        X = df_real.T.values
        X_scaled = TimeSeriesScalerMeanVariance().fit_transform(X)
        return X_scaled

    def train_clustering(self, df_real, n_clusters=6):
        """Train K-Shape clustering."""
        X_scaled = self.prepare_data(df_real)
        ks = KShape(n_clusters=n_clusters, verbose=False, random_state=42)
        ks.fit(X_scaled)
        labels = ks.labels_
        return ks, labels

    def train_anomaly_detection(self, df_real):
        """Train Isolation Forest for anomalies based on quarterly returns."""
        # Calculate quarterly percentage change
        df_pct = df_real.pct_change(periods=3).fillna(0)
        
        anomalies_dict = {}
        for prov in df_real.columns:
            iso = IsolationForest(contamination=0.05, random_state=42)
            # Reshape for sklearn
            X_prov = df_pct[[prov]].values
            anomalies = iso.fit_predict(X_prov)
            # -1 for anomaly, 1 for normal
            anomalies_dict[prov] = anomalies
            
        df_anomalies = pd.DataFrame(anomalies_dict, index=df_real.index)
        return df_anomalies
    
    def run_pipeline(self, df_real, n_clusters=6):
        """Run the full pipeline and log to MLflow."""
        with mlflow.start_run(run_name="Production_Pipeline") as run:
            print(f"Started run: {run.info.run_id}")
            
            # 1. Clustering
            ks_model, labels = self.train_clustering(df_real, n_clusters)
            df_clusters = pd.DataFrame({"province": df_real.columns, "cluster": labels})
            
            # 2. Anomaly Detection
            df_anomalies = self.train_anomaly_detection(df_real)
            
            # 3. Combine results
            # We save anomalies in a long format
            df_anomalies_long = df_anomalies.reset_index().melt(id_vars='index', var_name='province', value_name='anomaly')
            df_anomalies_long.rename(columns={'index': 'date'}, inplace=True)
            
            # Save artifacts
            os.makedirs("artifacts", exist_ok=True)
            clusters_path = "artifacts/clusters.parquet"
            anomalies_path = "artifacts/anomalies.parquet"
            
            df_clusters.to_parquet(clusters_path, index=False)
            df_anomalies_long.to_parquet(anomalies_path, index=False)
            
            # Log params and artifacts
            mlflow.log_param("n_clusters", n_clusters)
            mlflow.log_artifact(clusters_path)
            mlflow.log_artifact(anomalies_path)
            
            # Log models
            mlflow.sklearn.log_model(ks_model, "kshape_model")
            
            # Register the model
            model_uri = f"runs:/{run.info.run_id}/kshape_model"
            try:
                mlflow.register_model(model_uri, "KShape_TeacherSalaries_Prod")
                print("Model registered successfully.")
            except Exception as e:
                print(f"Error registering model: {e}")
                
            return df_clusters, df_anomalies_long
    
    def load_latest_artifacts(self, local_first=True):
        """Fetch the latest clusters and anomalies. Prioritize local files for production."""
        
        # 1. Try local files first (Production/Bundle approach)
        if local_first:
            clusters_path = "artifacts/clusters.parquet"
            anomalies_path = "artifacts/anomalies.parquet"
            
            if os.path.exists(clusters_path) and os.path.exists(anomalies_path):
                try:
                    df_clusters = pd.read_parquet(clusters_path)
                    df_anomalies = pd.read_parquet(anomalies_path)
                    print(f"Loaded artifacts from local storage: {clusters_path}")
                    return df_clusters, df_anomalies
                except Exception as e:
                    print(f"Error loading local artifacts: {e}. Falling back to MLflow...")

        # 2. Fallback to MLflow (Development approach)
        client = mlflow.tracking.MlflowClient(self.db_uri)
        try:
            experiment = client.get_experiment_by_name(self.experiment_name)
            if not experiment:
                print("MLflow experiment not found.")
                return None, None
            
            runs = client.search_runs(
                experiment_ids=[experiment.experiment_id],
                order_by=["start_time DESC"],
                max_results=1
            )
            
            if not runs:
                print("No MLflow runs found.")
                return None, None
                
            latest_run = runs[0]
            run_id = latest_run.info.run_id
            
            # Download artifacts
            clusters_path = client.download_artifacts(run_id, "clusters.parquet")
            anomalies_path = client.download_artifacts(run_id, "anomalies.parquet")
            
            df_clusters = pd.read_parquet(clusters_path)
            df_anomalies = pd.read_parquet(anomalies_path)
            
            print(f"Loaded artifacts from MLflow run: {run_id}")
            return df_clusters, df_anomalies
        except Exception as e:
            print(f"Could not load artifacts from any source: {e}")
            return None, None
