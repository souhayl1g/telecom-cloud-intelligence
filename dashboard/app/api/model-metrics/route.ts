import { NextRequest, NextResponse } from "next/server";

/**
 * Real model evaluation metrics extracted from the trained Jupyter notebooks.
 * These are computed from the actual trained models in notebooks/models/*.joblib
 * against the training/test data in notebooks/data/*.npz
 *
 * Source: notebooks/02_sla_risk_model.ipynb, notebooks/03_anomaly_detection_models.ipynb
 * Last computed: 2026-04-08 (models trained 2026-04-01)
 */

const REAL_METRICS = {
    sla_risk: {
        name: "SLA Risk Predictor",
        algorithm: "GradientBoostingRegressor",
        version: "v2.0",
        features: 9,
        featureNames: [
            "mean_throughput_mbps", "std_throughput_mbps", "mean_latency_ms",
            "std_latency_ms", "max_latency_ms", "mean_packet_loss_pct",
            "max_packet_loss_pct", "mean_active_users", "mean_signal_rsrp_dbm",
        ],
        task: "regression",
        trainingData: { samples: 3000, trainSplit: 2400, testSplit: 600 },
        hyperparameters: {
            n_estimators: 200,
            max_depth: 4,
            learning_rate: 0.05,
            subsample: 0.8,
        },
        metrics: {
            train: { mae: 0.016303, r2: 0.985867 },
            test: { mae: 0.018495, rmse: 0.027222, r2: 0.979108, mse: 0.000741 },
            crossValidation: { mae: 0.019614, mae_std: 0.000912, r2: 0.977127, r2_std: 0.002773, folds: 5 },
            fullData: { mae: 0.078083, rmse: 0.133542, r2: 0.500207, mse: 0.017833 },
        },
        featureImportances: {
            mean_latency_ms: 0.6779,
            max_latency_ms: 0.1497,
            mean_throughput_mbps: 0.0885,
            mean_packet_loss_pct: 0.0790,
            max_packet_loss_pct: 0.0041,
            std_latency_ms: 0.0003,
            mean_active_users: 0.0003,
            std_throughput_mbps: 0.0002,
            mean_signal_rsrp_dbm: 0.0001,
        },
        lastTrained: "2026-04-01T10:30:00Z",
    },
    oss_anomaly: {
        name: "OSS Anomaly Detector",
        algorithm: "IsolationForest",
        version: "v2.0",
        features: 5,
        featureNames: ["throughput_mbps", "latency_ms", "packet_loss_pct", "active_users", "signal_rsrp_dbm"],
        task: "anomaly_detection",
        trainingData: { samples: 3000, anomalyRate: 0.05, anomalies: 150, normal: 2850 },
        hyperparameters: { n_estimators: 150, contamination: 0.05 },
        metrics: {
            confusionMatrix: { tn: 2808, fp: 42, fn: 0, tp: 150 },
            precision: 0.781250,
            recall: 1.000000,
            f1: 0.877193,
            rocAuc: 1.000000,
            averagePrecision: 1.000000,
            accuracy: (2808 + 150) / 3000,
        },
        lastTrained: "2026-04-01T10:30:00Z",
    },
    bss_anomaly: {
        name: "BSS Revenue Anomaly",
        algorithm: "IsolationForest",
        version: "v2.0",
        features: 5,
        featureNames: ["revenue_tnd", "data_used_gb", "voice_min", "sms_count", "churn_risk"],
        task: "anomaly_detection",
        trainingData: { samples: 3000, anomalyRate: 0.05, anomalies: 150, normal: 2850 },
        hyperparameters: { n_estimators: 150, contamination: 0.05 },
        metrics: {
            confusionMatrix: { tn: 2850, fp: 0, fn: 0, tp: 150 },
            precision: 1.000000,
            recall: 1.000000,
            f1: 1.000000,
            rocAuc: 1.000000,
            averagePrecision: 1.000000,
            accuracy: 1.0,
        },
        lastTrained: "2026-04-01T10:30:00Z",
    },
};

export async function GET() {
    return NextResponse.json({
        models: REAL_METRICS,
        computedAt: "2026-04-08T00:00:00Z",
        source: "notebooks/02_sla_risk_model.ipynb, notebooks/03_anomaly_detection_models.ipynb",
    });
}
