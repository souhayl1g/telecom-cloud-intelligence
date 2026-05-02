import { NextRequest, NextResponse } from "next/server";

/**
 * Real model evaluation metrics extracted from the trained Jupyter notebooks.
 * These are computed from the actual trained models in notebooks/models/*.joblib
 * against the training/test data in notebooks/data/*.npz
 *
 * Source:
 *   - notebooks/05_real_data_etl_engineering.ipynb (feature engineering)
 *   - notebooks/09_master_v3_training.py (master combined training — 1.5M+ real + simulated)
 * Data: Real Tunisie Telecom BSS (Feb/Mar 968K) + simulated (Jan/Apr/May 1.5M) + OSS real (Mar/Apr 18.8M) + simulated
 * Last computed: 2026-04-28
 */

const REAL_METRICS = {
    cem_score: {
        name: "CEM Experience Score",
        algorithm: "LightGBM (DART)",
        version: "v3.0-gpu",
        features: 13,
        featureNames: [
            "usim_bottleneck", "data_intensity", "dou_total", "duration",
            "s1_mme_sr", "iu_attach_sr", "gb_attach_sr",
            "avg_throughput", "avg_latency", "avg_packet_loss", "anomaly_rate",
            "generation_4g", "generation_5g",
        ],
        task: "regression",
        trainingData: {
            samples: 2468026,
            trainSplit: 2097822,
            testSplit: 370204,
            realSamples: 968077,
            simulatedSamples: 1499949,
        },
        hyperparameters: {
            boosting_type: "dart",
            drop_rate: 0.1,
            skip_drop: 0.5,
            num_leaves: 256,
            max_depth: 12,
            learning_rate: 0.03,
            feature_fraction: 0.8,
            bagging_fraction: 0.8,
            bagging_freq: 5,
            min_child_samples: 50,
            reg_alpha: 0.1,
            reg_lambda: 1.0,
            num_boost_round: 1000,
        },
        metrics: {
            test: { mae: 0.0129, rmse: 0.0162, r2: 0.9933 },
        },
        featureImportances: {
            s1_mme_sr: 0.1316,
            dou_total: 0.0570,
            iu_attach_sr: 0.0467,
            gb_attach_sr: 0.0359,
            generation_4g: 0.0024,
            avg_packet_loss: 0.0018,
            data_intensity: 0.0012,
            avg_throughput: 0.0009,
            avg_latency: 0.0006,
            duration: 0.0004,
            usim_bottleneck: 0.0003,
            anomaly_rate: 0.0002,
            generation_5g: 0.0001,
        },
        lastTrained: "2026-04-28T20:53:00Z",
        note: "Trained on 2.47M subscribers across 5 months (real + simulated). DART boosting with 256 leaves. Target is formula-derived CEM score.",
    },
    oss_anomaly: {
        name: "OSS Experience Anomaly",
        algorithm: "Variational Autoencoder (PyTorch)",
        version: "v3.0-gpu",
        features: 9,
        featureNames: [
            "throughput_mbps", "latency_ms", "packet_loss_rate", "jitter_ms",
            "cell_load_pct", "rsrp_dbm", "active_users", "integrity", "call_drop_rate",
        ],
        task: "anomaly_detection",
        trainingData: {
            samples: 499729,
            anomalyRate: 0.0443,
            realSamples: 299729,
            simulatedSamples: 200000,
            trainedOnNormalOnly: 424769,
        },
        hyperparameters: {
            architecture: "9 → 32 → 16 → Latent(8) → 16 → 32 → 9",
            parameters: 2057,
            epochs: 100,
            batch_size: 1024,
            learning_rate: 0.001,
            weight_decay: 0.00001,
            threshold: 0.23654,
        },
        metrics: {
            precision: 0.3769,
            recall: 0.7003,
            f1: 0.4901,
            rocAuc: 0.9307,
            accuracy: 0.9574,
        },
        lastTrained: "2026-04-28T20:55:00Z",
        note: "Trained on 500K mixed real+simulated OSS records. Deeper 8-latent architecture. Threshold optimized for 70% recall. GPU-accelerated via CUDA.",
    },
    rat_underservice: {
        name: "RAT Underservice Detection",
        algorithm: "XGBoost Classifier",
        version: "v3.0-gpu",
        features: 10,
        featureNames: [
            "dou_total", "duration", "s1_mme_sr", "iu_attach_sr", "gb_attach_sr",
            "network_experience_index", "avg_throughput", "avg_latency", "avg_packet_loss", "anomaly_rate",
        ],
        task: "classification",
        trainingData: {
            samples: 2468026,
            positiveRate: 0.092,
            positive: 226564,
            negative: 2241462,
            realSamples: 968077,
            simulatedSamples: 1499949,
        },
        hyperparameters: {
            n_estimators: 500,
            max_depth: 8,
            learning_rate: 0.05,
            subsample: 0.8,
            colsample_bytree: 0.8,
            min_child_weight: 3,
            gamma: 0.2,
            reg_alpha: 0.1,
            reg_lambda: 2.0,
            scale_pos_weight: 9.87,
            device: "cuda",
            tree_method: "hist",
        },
        metrics: {
            precision: 0.4078,
            recall: 0.8934,
            f1: 0.5599,
            rocAuc: 0.9605,
            accuracy: 0.8708,
        },
        featureImportances: {
            dou_total: 0.5186,
            network_experience_index: 0.3476,
            iu_attach_sr: 0.0791,
            duration: 0.0308,
            gb_attach_sr: 0.0113,
            s1_mme_sr: 0.0058,
            avg_packet_loss: 0.0035,
            avg_latency: 0.0020,
            avg_throughput: 0.0013,
            anomaly_rate: 0.0010,
        },
        lastTrained: "2026-04-28T20:55:00Z",
        note: "Trained on 2.47M subscribers across 5 months. 500 trees, depth 8, GPU-accelerated XGBoost. Catches 89% of underserved subscribers.",
    },
    // Legacy v2.0 models retained for reference
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
        hyperparameters: { n_estimators: 200, max_depth: 4, learning_rate: 0.05, subsample: 0.8 },
        metrics: {
            train: { mae: 0.016303, r2: 0.985867 },
            test: { mae: 0.018495, rmse: 0.027222, r2: 0.979108, mse: 0.000741 },
            crossValidation: { mae: 0.019614, mae_std: 0.000912, r2: 0.977127, r2_std: 0.002773, folds: 5 },
        },
        lastTrained: "2026-04-01T10:30:00Z",
        note: "Legacy v2.0 model trained on synthetic data. Superseded by v3.0 CEM LightGBM.",
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
            precision: 1.0, recall: 1.0, f1: 1.0, rocAuc: 1.0, averagePrecision: 1.0, accuracy: 1.0,
        },
        lastTrained: "2026-04-01T10:30:00Z",
        note: "Legacy v2.0 model trained on synthetic data. v3.0 RAT model covers subscriber experience.",
    },
};

export async function GET() {
    return NextResponse.json({
        models: REAL_METRICS,
        computedAt: "2026-04-28T20:55:00Z",
        source: "notebooks/09_master_v3_training.py",
        dataSource: "Real Tunisie Telecom BSS (Feb/Mar 968K) + simulated (Jan/Apr/May 1.5M) + OSS real (Mar/Apr 18.8M) + simulated",
    });
}
