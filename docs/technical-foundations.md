# Technical Foundations — Complete Reference

> A deep-dive technical course covering every concept behind the Telecom NeXoligence Platform.  
> Written for: Souhayl Guenichi | April 2026

---

# Part I — Telecom Network Fundamentals

---

## Chapter 1: The Mobile Network Stack

### 1.1 What Happens When a Phone Connects

When a subscriber turns on their phone, before they can make a call or use data, the device must **attach** to the network. This is a multi-step process:

```
┌──────────┐        ┌──────────┐        ┌──────────┐        ┌──────────┐
│  Device   │──RF───│  Base     │──Wire──│  Core     │──Wire──│  Internet │
│  (UE)     │       │  Station  │        │  Network  │        │  / PSTN   │
└──────────┘        └──────────┘        └──────────┘        └──────────┘
   Phone             eNodeB/gNB          MME/AMF/SGSN         Data/Voice
```

**UE (User Equipment):** The subscriber's device. It has:
- An IMSI (on the SIM) — the subscriber's identity
- An IMEI (on the device) — the device's identity (first 8 digits = TAC)
- Radio capabilities — which frequencies and RATs it supports

**Base Station:** The antenna tower. Different names per generation:
- 2G: BTS (Base Transceiver Station)
- 3G: NodeB
- 4G: eNodeB (evolved NodeB)
- 5G: gNB (next generation NodeB)

**Core Network:** The brain. Routes calls, manages subscribers, authenticates SIMs:
- 2G/3G: MSC (voice) + SGSN/GGSN (data)
- 4G: MME (Mobility Management Entity) + S-GW/P-GW
- 5G: AMF (Access and Mobility Function) + SMF/UPF

### 1.2 RAT — Radio Access Technology

RAT is the wireless protocol the device uses to communicate with the base station.

| RAT | Generation | Typical Data Speed | Typical Latency | In Your Data |
|-----|-----------|-------------------|-----------------|--------------|
| GSM/GPRS/EDGE | 2G | 50-200 Kbps | 300-1000ms | traffic_2g |
| UMTS/HSPA/HSPA+ | 3G | 1-42 Mbps | 50-100ms | traffic_3g |
| LTE/LTE-A | 4G | 50-300 Mbps | 10-30ms | traffic_4g |
| NR (New Radio) | 5G | 100-1000+ Mbps | 1-10ms | traffic_5g |

**In your BSS data:**
- `generation` = what the DEVICE supports (hardware capability)
- `highest_rat` = what the subscriber ACTUALLY used (network reality)
- The gap between these two = underservice

### 1.3 The Interfaces — Where Your Data Features Come From

Each attach success rate in your BSS data corresponds to a specific network interface:

**`s1_mme_sr` — The S1 Interface (4G)**
```
    UE ←──radio──→ eNodeB ←──S1──→ MME
                              ↑
                         This interface
```
The S1 interface connects the 4G base station (eNodeB) to the core network controller (MME). When a subscriber tries to attach to 4G, the eNodeB sends an "Attach Request" to the MME over S1. The MME authenticates the subscriber (checks IMSI against HSS), and if successful, returns an "Attach Accept."

`s1_mme_sr = successful_attaches / total_attempts`

- **1.0** = every 4G attach attempt succeeded → subscriber has reliable 4G
- **0.0** = subscriber never successfully attached to 4G → either never tried (2G-only device), or tried and failed (network issue, SIM issue)
- **0.5-0.99** = intermittent failures → congestion, weak signal, handover issues

**`iu_attach_sr` — The Iu Interface (3G)**
```
    UE ←──radio──→ NodeB ←──Iub──→ RNC ←──Iu──→ SGSN
                                          ↑
                                     This interface
```
The Iu interface connects the 3G Radio Network Controller (RNC) to the SGSN in the core. Similar to S1 but for 3G. The RNC manages multiple NodeBs and handles radio resource management.

**`gb_attach_sr` — The Gb Interface (2G)**
```
    UE ←──radio──→ BTS ←──Abis──→ BSC ←──Gb──→ SGSN
                                         ↑
                                    This interface
```
The Gb interface connects the 2G Base Station Controller (BSC) to the SGSN for packet data. This is the oldest interface — 2G data (GPRS/EDGE) goes through here.

**Why this matters for your project:**
These three attach rates are OSS-grade metrics embedded in BSS data. They tell you per-subscriber network quality at each RAT layer. In a pure BSS system, you'd only have usage data. Having attach rates means you can detect network-level issues from the subscriber side — which is the foundation of O+B convergence.

### 1.4 USIM vs SIM — Why 74% of Your Subscribers Are Stuck

**SIM (Subscriber Identity Module):** The original 2G-era card. Contains the IMSI and authentication keys for GSM (2G). Can only authenticate on 2G networks.

**USIM (Universal SIM):** The 3G+ era card. Contains enhanced authentication algorithms (MILENAGE) that support 3G, 4G, and 5G mutual authentication. Without USIM, the network CANNOT authenticate the subscriber on 3G/4G/5G — even if the device hardware supports it.

In your data: `usim_flag=0` for 74% of subscribers. This means 370,000 subscribers are limited to 2G authentication regardless of their device. A subscriber with an iPhone 16 Pro Max (5G-capable) but usim_flag=0 is stuck on 2G for all authenticated services. This is why `sim_bottleneck` is one of your most important engineered features.

### 1.5 VoLTE and CS Fallback

**VoLTE (Voice over LTE):** Voice calls carried as data packets over the 4G network. HD voice quality, no need to drop to 3G/2G for calls.

**CS Fallback (Circuit-Switched Fallback):** When a 4G subscriber makes a voice call but VoLTE isn't available, the network drops them to 3G or 2G for the call. This is why `voice_onlinetime_2g` can be high even for subscribers with 4G-capable devices — their voice is falling back to legacy networks.

In your data:
- `volte_flag=1` for only 6% of subscribers → VoLTE adoption is very low
- `voice_3g_ratio` (engineered feature) captures how much voice is handled by 3G vs 2G
- High `voice_3g_ratio` with `volte_flag=1` means VoLTE is available but not being used — potential configuration issue

### 1.6 OSS vs BSS — The Two Worlds

**OSS (Operations Support System):**
- Manages the NETWORK
- Cell-level KPIs: throughput, latency, packet loss, interference, alarms
- Network engineers use this
- Question it answers: "Is the network healthy?"

**BSS (Business Support System):**
- Manages the SUBSCRIBERS
- Subscriber profiles, usage, billing, provisioning
- Business teams use this
- Question it answers: "Are subscribers happy/profitable?"

**The Problem:** OSS and BSS are traditionally separate systems with separate databases, separate teams, and separate dashboards. When a cell degrades, the network team sees KPI drops. When subscribers complain, the business team sees support tickets. Nobody automatically connects "cell degradation in area X" with "subscriber experience drop in area X."

**Your Platform:** Bridges OSS and BSS by computing correlations between network KPIs and subscriber experience metrics, joined on geography and RAT. This is the O+B convergence.

### 1.7 CEM — Customer Experience Management

CEM goes beyond traditional BSS metrics (billing, ARPU) to measure the **quality of experience** each subscriber receives. Huawei's SmartCare is a CEM platform.

CEM dimensions in your data:
1. **Service experience** — can the subscriber use data? make calls? (dou_total, duration)
2. **Network experience** — does the network respond reliably? (attach success rates)
3. **Device experience** — is the device appropriate for the services used? (generation, tertype)
4. **Coverage experience** — does the subscriber get the best available technology? (highest_rat, rat_gap)

Your CEM Experience Score (Model 1) combines all four dimensions into a single 0-1 score per subscriber.

### 1.8 ADN — Autonomous Driving Network

Huawei's ADN framework defines 6 levels of network automation:

| Level | Name | Description | Your Platform |
|-------|------|-------------|---------------|
| L0 | Manual | Human does everything | - |
| L1 | Assisted | System provides information, human acts | Dashboard showing metrics |
| L2 | Partial | System recommends actions, human approves all | Not here |
| L3 | Conditional | System acts on low-risk, human approves high-risk | Not here |
| **L4** | **High** | **System acts autonomously, human oversees critical** | **Your L4 Agent** |
| L5 | Full | Fully autonomous, no human needed | Future goal |

Your platform is L4 because:
- Auto-approves safe actions (informational, predictions) without human
- Requires human approval only for critical/warning remediations
- Executes real backend playbooks after approval
- All actions audited in PostgreSQL

---

# Part II — Machine Learning

---

## Chapter 2: Supervised Learning — Predicting Known Targets

### 2.1 What Is Supervised Learning?

You have inputs (features) and a known output (label/target). The model learns the mapping: `f(features) → target`. After training, it predicts the target for new, unseen features.

**In your project:**
- Model 1 (CEM Score): features → experience score (0-1)
- Model 4 (RAT Underservice): features → root cause class

### 2.2 GradientBoosting — How Your CEM Score Works

**The idea:** Build many small, weak decision trees. Each tree corrects the mistakes of the previous ones. The final prediction is the sum of all trees.

**Step by step:**

```
Step 1: Make initial prediction (mean of all targets)
        prediction_0 = 0.5 (for all subscribers)

Step 2: Compute residuals (errors)
        residual_1 = actual_score - prediction_0
        (e.g., 0.9 - 0.5 = 0.4 for a good subscriber)

Step 3: Fit a small tree to predict the residuals
        Tree_1: if attach_composite > 0.8 → residual ≈ +0.3
                else → residual ≈ -0.2

Step 4: Update prediction
        prediction_1 = prediction_0 + learning_rate × Tree_1(features)
        = 0.5 + 0.1 × 0.3 = 0.53

Step 5: Compute new residuals from prediction_1
        residual_2 = actual_score - prediction_1

Step 6: Fit Tree_2 to predict residual_2
        ... repeat for N trees (200 in your setup)

Final: prediction = prediction_0 + lr×Tree_1 + lr×Tree_2 + ... + lr×Tree_200
```

**Why "Gradient"?** Each tree is fitted to the negative gradient of the loss function (for MSE loss, the gradient is simply the residual). This is gradient descent, but instead of updating weights in a neural network, you're adding trees.

**Why "Boosting"?** Each tree boosts the model's performance by focusing on what previous trees got wrong. Early trees learn the broad patterns ("high attach = good experience"). Later trees learn the edge cases ("high attach but zero data usage and premium device = anomalous experience").

**Key hyperparameters in your setup:**
- `n_estimators=200` — number of trees. More trees = more capacity to learn patterns, but risk of overfitting.
- `max_depth=4` — each tree can only go 4 splits deep. Keeps trees weak (prevents them from memorizing individual subscribers). The ensemble of many weak trees generalizes better than one deep tree.
- `learning_rate=0.1` — how much each tree contributes. Low rate means each tree makes a small correction, requiring more trees but giving a smoother, more stable model.

**Feature importance — why GBR is interpretable:**
After training, you can compute how much each feature contributed to reducing the loss across all trees. If `attach_composite` appeared in many splits early in many trees and each split reduced the error significantly, it gets high importance. This is what feeds the L4 Agent's explanations.

```python
model.feature_importances_
# → {'attach_composite': 0.42, 'rat_gap': 0.21, 'traffic_concentration': 0.15, ...}
```

### 2.3 XGBoost — How Your Underservice Classifier Works

XGBoost (eXtreme Gradient Boosting) is an optimized implementation of gradient boosting with key improvements:

**Regularization:** XGBoost adds L1 (lasso) and L2 (ridge) regularization terms to the loss function:
```
Loss = Σ(actual - predicted)² + λ × Σ(leaf_weights²) + α × Σ|leaf_weights|
```
This penalizes complex trees (many leaves with large weights), preventing overfitting. Standard GBR doesn't have this built-in.

**Handling missing values:** XGBoost learns the optimal direction (left or right) to send missing values at each split. Your BSS data has NULLs in volte_flag (45%), sim_slot (5%), brand (5%). XGBoost handles these natively without imputation.

**Multi-class classification:** For your underservice model with 5 classes (sim_bottleneck, coverage_gap, congestion, device_config, not_underserved), XGBoost builds 5 separate sets of trees (one-vs-rest) and combines them with softmax:

```
P(sim_bottleneck) = exp(score_sim) / Σ exp(score_all_classes)
```

**Why XGBoost over GBR for classification?**
- Native multi-class support with softmax probabilities
- Built-in regularization (critical with 500K rows — prevents memorizing)
- Handles NULLs without preprocessing
- Faster training (histogram-based binning, parallel tree construction)

### 2.4 Decision Boundaries — What Trees Actually Learn

A decision tree splits the feature space into rectangular regions:

```
                    rat_gap > 1?
                   /            \
                 YES             NO
                /                  \
        usim_flag = 0?          → not_underserved
        /          \
      YES           NO
      /               \
→ sim_bottleneck    s1_mme_sr > 0?
                    /           \
                  YES            NO
                  /                \
            → congestion      → coverage_gap
```

A single tree is too rigid. An ensemble of 200+ trees, each seeing a random subset of features and data, creates smooth, complex decision boundaries that capture the nuanced interactions between all 15 input features.

---

## Chapter 3: Unsupervised Learning — Finding Patterns Without Labels

### 3.1 What Is Unsupervised Learning?

You have inputs but NO output labels. The model learns the structure of the data itself — clusters, distributions, manifolds. Anomalies are points that don't fit the learned structure.

**In your project:**
- Model 2 (Autoencoder): learns what "normal" subscribers look like, flags deviations

### 3.2 IsolationForest — What You're Replacing (and Why It Worked Before)

**The idea:** Anomalies are rare and different. If you randomly split the data, anomalies get isolated in fewer splits.

**How it works:**
```
1. Pick a random feature (e.g., dou_total)
2. Pick a random split value between min and max
3. Points to the left go to left child, right go to right child
4. Repeat until each point is isolated (in its own leaf)
5. Count how many splits it took to isolate each point

Normal points: deep in the tree (many splits needed, they're similar to neighbors)
Anomalies: near the root (few splits needed, they're easy to separate)

Anomaly score = average path length across all trees (lower = more anomalous)
```

**Why it worked on synthetic data (6 features):** With 6 numeric features (latency, jitter, packet loss, throughput, call drops, handover failures), anomalies WERE extreme on individual features. A latency of 500ms when the mean is 50ms gets isolated immediately. IsolationForest's random feature splits catch this easily.

**Why it fails on real data (26+ features):** With 26 features across 4 dimensions, anomalies are often extreme on COMBINATIONS, not individuals. A subscriber with normal attach rates, normal data usage, but a premium 5G device — each feature is normal individually. The anomaly is the combination. IsolationForest's random single-feature splits rarely isolate combination anomalies because it would need to split on the RIGHT sequence of features in the RIGHT order.

### 3.3 The Curse of Dimensionality

As features increase, the volume of the feature space grows exponentially. With 6 features, data points are relatively dense. With 42 features (26 raw + 16 engineered), the same 500K points are scattered in a space that has 2^42 times more volume. Distance metrics become unreliable — every point is roughly equidistant from every other point.

This is why IsolationForest struggles in high dimensions: the random splits become increasingly meaningless as dimensions increase, because the probability of splitting on an informative feature at an informative value decreases with each added dimension.

Autoencoders handle this by learning a compressed representation (the bottleneck) that captures only the meaningful structure, effectively projecting 42 dimensions down to 32 latent dimensions where the data is dense and the manifold is learnable.

---

## Chapter 4: IsolationForest vs Autoencoder — The Full Comparison

This comparison matters because it's the core of your v2.0 → v3.0 transition.

| Aspect | IsolationForest | Autoencoder |
|--------|----------------|-------------|
| **How it detects** | Isolation depth (few splits = anomaly) | Reconstruction error (high error = anomaly) |
| **Feature interactions** | None — splits on one feature at a time | Full — encoder learns joint feature representation |
| **Dimensionality** | Degrades above ~15-20 features | Handles high dimensions via compression |
| **Training data** | Fits on all data (expects contamination %) | Trains on clean data only (learns "normal") |
| **Training speed** | Fast (random trees, no gradient descent) | Slower (neural network, needs epochs) |
| **Inference speed** | Fast (tree traversal) | Fast (single forward pass through network) |
| **Interpretability** | Low (anomaly score, but which feature?) | Medium (reconstruction gap per feature) |
| **Threshold** | Contamination parameter (manual) | μ + kσ on reconstruction error (tunable) |
| **New anomaly types** | Can detect (if extreme on a feature) | Can detect (any poorly reconstructed pattern) |

---

# Part III — Deep Learning

---

## Chapter 5: Neural Networks — The Foundation

### 5.1 What Is a Neural Network?

A neural network is a function composed of layers of linear transformations followed by nonlinear activations:

```
Input: x = [x1, x2, ..., xN]    (your 42 features)

Layer 1:  h1 = activation(W1 × x + b1)
Layer 2:  h2 = activation(W2 × h1 + b2)
...
Output:   y = Wout × hL + bout
```

**W** (weights) and **b** (biases) are the learnable parameters. Training adjusts these to minimize a loss function.

**Activation functions — why they matter:**

Without activations, stacking layers is pointless: `W2 × (W1 × x) = (W2×W1) × x = W_combined × x` — it collapses to one linear layer. Activations introduce nonlinearity, allowing the network to learn curved decision boundaries.

```
ReLU(x)    = max(0, x)        — simple, fast, used in hidden layers
Sigmoid(x) = 1 / (1 + e^-x)  — outputs 0-1, used for probabilities
Tanh(x)    = (e^x - e^-x) / (e^x + e^-x)  — outputs -1 to 1
```

### 5.2 How Training Works — Backpropagation

```
1. FORWARD PASS:
   Feed input through network → get prediction

2. COMPUTE LOSS:
   loss = Loss_function(prediction, actual)
   For regression: MSE = mean((prediction - actual)²)
   For classification: CrossEntropy = -Σ actual × log(prediction)

3. BACKWARD PASS (backpropagation):
   Compute ∂loss/∂W for every weight in every layer
   Using the chain rule:
   ∂loss/∂W1 = ∂loss/∂h2 × ∂h2/∂h1 × ∂h1/∂W1

4. UPDATE WEIGHTS:
   W_new = W_old - learning_rate × ∂loss/∂W
   (This is gradient descent — move weights in the direction that reduces loss)

5. REPEAT for many epochs (full passes through training data)
```

**Batch size:** Instead of computing gradients on all 500K samples (slow, memory-hungry), you compute on mini-batches (e.g., 256 samples). This gives a noisy but faster gradient estimate. The noise actually helps escape local minima.

**Learning rate:** Too high → oscillates, never converges. Too low → converges too slowly. Adam optimizer (used in most modern networks) adapts the learning rate per parameter.

### 5.3 BatchNorm — Why It's in Your Autoencoder

BatchNorm normalizes each layer's activations across the batch:
```
h_normalized = (h - batch_mean) / batch_std
h_output = γ × h_normalized + β    (γ and β are learnable)
```

**Why:** Without BatchNorm, the distribution of each layer's inputs shifts as earlier layers update (internal covariate shift). The later layers are constantly chasing a moving target. BatchNorm stabilizes the input distribution, allowing:
- Higher learning rates (faster training)
- Less sensitivity to weight initialization
- Mild regularization effect (batch statistics add noise)

### 5.4 Dropout — Preventing Overfitting

During training, randomly set a fraction of neurons to zero:
```
Training:  h_dropped = h × mask    (mask = random 0s and 1s, 20% zeros for Dropout(0.2))
Inference: h_scaled = h × (1 - dropout_rate)    (no dropout, but scale down)
```

**Why:** Forces the network to not rely on any single neuron. Every neuron must learn something useful independently. This prevents co-adaptation (where neurons only work in combination but individually are useless) and reduces overfitting.

**Your Autoencoder uses Dropout(0.2):** 20% of neurons are randomly zeroed each training step. This is mild — enough to regularize but not so much that the reconstruction quality suffers.

---

## Chapter 6: Autoencoders — Learning Normal

### 6.1 The Architecture

```
      INPUT                BOTTLENECK              OUTPUT
   (42 features)          (32 latent)           (42 reconstructed)
       │                      │                       │
   ┌───▼───┐             ┌───▼───┐              ┌───▼───┐
   │  128  │             │  32   │              │  128  │
   │neurons│             │neurons│              │neurons│
   │ ReLU  │             │ ReLU  │              │ ReLU  │
   │BatchN │             │       │              │BatchN │
   │Drop0.2│             │       │              │Drop0.2│
   └───┬───┘             └───┬───┘              └───┬───┘
       │                     │                      │
   ┌───▼───┐                 │                 ┌───▼───┐
   │  64   │                 │                 │  64   │
   │neurons│                 │                 │neurons│
   │ ReLU  │                 │                 │ ReLU  │
   │BatchN │                 │                 │BatchN │
   │Drop0.2│                 │                 │Drop0.2│
   └───┬───┘                 │                 └───┬───┘
       │                     │                      │
       └──────► ENCODE ►─────┘────► DECODE ►────────┘
                                                    │
                                               ┌───▼───┐
                                               │  42   │
                                               │Sigmoid│
                                               └───────┘

         ENCODER                              DECODER
   (compress 42 → 32)                   (reconstruct 32 → 42)
```

### 6.2 Why the Bottleneck Matters

The bottleneck (32 neurons) is smaller than the input (42 features). The encoder MUST compress 42 features into 32 numbers. It can only do this by learning which features are correlated and encoding them jointly.

Example: `traffic_2g + traffic_3g + traffic_4g + traffic_5g ≈ dou_total`. The encoder might learn to store the total and the ratios rather than all 5 values. This compression forces the network to learn the STRUCTURE of normal subscriber profiles.

When an anomalous subscriber arrives (one where the feature relationships violate the learned structure), the decoder cannot reconstruct it accurately — because the bottleneck representation doesn't capture the anomalous pattern. The reconstruction error spikes.

### 6.3 Reconstruction Error — The Anomaly Signal

```python
reconstruction_error = mean((input - reconstructed)²)

# Per-feature:
feature_errors = (input - reconstructed)²
# → [attach_composite: 0.001, rat_gap: 0.002, ..., traffic_4g: 0.45, ...]
#                                                    ↑ HIGH — this feature is anomalous
```

The per-feature error tells you WHICH features the model couldn't reconstruct — pointing at what makes this subscriber anomalous. This is why the Autoencoder provides interpretable anomaly detection despite being a neural network.

### 6.4 Training on Clean Data Only — Why This Is Critical

```
Training distribution:
  Only "healthy" subscribers (attach > 0.8, active, rat_gap ≤ 1)
  → Model learns: "normal subscribers have these feature relationships"

At inference (all 500K):
  Normal subscriber → low reconstruction error (model knows this pattern)
  Anomalous subscriber → high reconstruction error (pattern not in training)
```

If you train on ALL data (including anomalies), the model learns to reconstruct anomalies too. The error distribution becomes uniform — everything reconstructs equally well — and you can't set a threshold. Training on clean data creates a clear separation between normal (low error) and anomalous (high error).

### 6.5 Threshold Selection

```
After training, compute reconstruction_error for all validation data:

healthy_errors = [0.001, 0.002, 0.003, 0.001, ...]   (tight distribution)
anomaly_errors = [0.05, 0.12, 0.08, 0.15, ...]        (spread, higher)

         │                    ▓▓
         │                   ▓▓▓▓
         │   ░░░░           ▓▓▓▓▓▓
         │  ░░░░░░         ▓▓▓▓▓▓▓▓
         │ ░░░░░░░░       ▓▓▓▓▓▓▓▓▓▓
         └──────────┼─────────────────→ error
                threshold (μ + kσ)

░ = healthy subscribers
▓ = anomalous subscribers
```

You pick k such that the threshold separates the two distributions with maximum F1 score. k=2 means "anomalous if error exceeds 2 standard deviations above the mean" — catching clear anomalies while minimizing false positives.

---

## Chapter 7: LSTM — Learning Sequences

### 7.1 Why Sequences Need Special Architecture

Standard neural networks take a fixed-size input and produce a fixed-size output. They have no concept of order. If you feed `[usage_t1, usage_t2, usage_t3]` as a flat vector, the model treats t1, t2, t3 as interchangeable features — it doesn't know t1 comes before t2.

For churn prediction, ORDER IS EVERYTHING:
- `[high, high, low]` = sudden drop (possible network issue)
- `[high, medium, low]` = gradual decline (churn trajectory)
- `[low, medium, high]` = growth (opposite of churn)

Same values, different order, completely different meaning. You need a model that processes sequences step by step, maintaining state across steps.

### 7.2 RNN — The Basic Idea

A Recurrent Neural Network processes one timestep at a time, maintaining a hidden state:

```
    h_t = tanh(W_h × h_{t-1} + W_x × x_t + b)

At each timestep t:
  - Take current input x_t (subscriber's features at window t)
  - Combine with previous hidden state h_{t-1} (memory of past windows)
  - Produce new hidden state h_t (updated memory)
```

```
    x_1        x_2        x_3        x_4
     │          │          │          │
     ▼          ▼          ▼          ▼
   ┌───┐     ┌───┐     ┌───┐     ┌───┐
   │RNN├────→│RNN├────→│RNN├────→│RNN├───→ h_4 (final state)
   └───┘     └───┘     └───┘     └───┘        │
    h_0       h_1       h_2       h_3          ▼
                                           prediction
```

**The problem: vanishing gradients.** During backpropagation, gradients are multiplied through each timestep. After 10-20 steps, the gradient becomes exponentially small → the model can't learn long-range dependencies. A pattern from window 1 that matters for prediction at window 20 gets lost.

### 7.3 LSTM — Solving Vanishing Gradients

LSTM (Long Short-Term Memory) adds a **cell state** — a highway that carries information across timesteps with minimal modification:

```
┌─────────────────────────────────────────────────────┐
│                    LSTM Cell                          │
│                                                      │
│   c_{t-1} ────[×]────────[+]──────────→ c_t         │
│              forget     add new                      │
│              gate       information                  │
│                ↑            ↑                         │
│             f_t          i_t × c̃_t                   │
│                                                      │
│   h_{t-1}──┐                                         │
│   x_t  ──┐ │                                         │
│           ▼ ▼                                         │
│     ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│     │  Forget   │   │  Input   │   │  Output  │     │
│     │  Gate     │   │  Gate    │   │  Gate    │     │
│     │ σ(Wf×[h,x])│  │ σ(Wi×[h,x])│  │ σ(Wo×[h,x])│ │
│     └────┬─────┘   └────┬─────┘   └────┬─────┘     │
│          │              │              │             │
│         f_t            i_t            o_t            │
│                                        │             │
│                              h_t = o_t × tanh(c_t)   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

**Three gates (all learned during training):**

**Forget Gate (f_t):** "What to forget from the cell state"
```
f_t = σ(W_f × [h_{t-1}, x_t] + b_f)    → values between 0 and 1
c_t = f_t × c_{t-1}  (element-wise multiply)
```
If f=0, the information is completely forgotten. If f=1, it's completely kept.

Example: If a subscriber's usage suddenly spikes (anomaly), the forget gate might learn to discard the previous "stable usage" memory because the context has changed.

**Input Gate (i_t):** "What new information to add to the cell state"
```
i_t = σ(W_i × [h_{t-1}, x_t] + b_i)        → gate (0-1)
c̃_t = tanh(W_c × [h_{t-1}, x_t] + b_c)     → candidate new info (-1 to 1)
c_t = f_t × c_{t-1} + i_t × c̃_t             → updated cell state
```

Example: When a subscriber's attach_composite drops from 1.0 to 0.5, the input gate learns to write "quality degradation event" into the cell state.

**Output Gate (o_t):** "What to output from the cell state"
```
o_t = σ(W_o × [h_{t-1}, x_t] + b_o)
h_t = o_t × tanh(c_t)
```

The output gate controls what part of the cell state becomes the visible hidden state h_t. Not all information in the cell needs to be output at every step.

**Why this solves vanishing gradients:**
The cell state c_t flows through time with only additions and element-wise multiplications (no matrix multiplications that compound). Gradients flow back through the cell state almost unchanged — the forget gate learns to keep the gradient alive for as long as needed.

### 7.4 GRU — The Lightweight Alternative

GRU (Gated Recurrent Unit) simplifies LSTM by merging the forget and input gates into a single "update gate" and merging the cell state with the hidden state:

```
z_t = σ(W_z × [h_{t-1}, x_t])          — update gate (what to keep vs. replace)
r_t = σ(W_r × [h_{t-1}, x_t])          — reset gate (how much past to consider)
h̃_t = tanh(W × [r_t × h_{t-1}, x_t])  — candidate hidden state
h_t = (1 - z_t) × h_{t-1} + z_t × h̃_t — final hidden state
```

**LSTM vs GRU:**
- LSTM: 3 gates, separate cell state → more expressive, slightly slower
- GRU: 2 gates, merged state → simpler, faster, often performs comparably

For your churn model (W=10-20 steps, 8 features), the difference is negligible. The plan says "LSTM/GRU" because either works — you'll try both and pick whichever gives better F1 on validation.

### 7.5 Sequence Classification — Your Churn Model

```
Window 1    Window 2    Window 3    ...    Window W
[8 feats]   [8 feats]   [8 feats]         [8 feats]
    │           │           │                  │
    ▼           ▼           ▼                  ▼
 ┌──────┐   ┌──────┐   ┌──────┐          ┌──────┐
 │LSTM  │──→│LSTM  │──→│LSTM  │──→ ... ──→│LSTM  │──→ h_W
 │(64)  │   │(64)  │   │(64)  │          │(64)  │   (64-dim)
 └──────┘   └──────┘   └──────┘          └──────┘
    │           │           │                  │
    h_1         h_2         h_3               h_W
    │           │           │                  │
    ▼           ▼           ▼                  ▼
 ┌──────┐   ┌──────┐   ┌──────┐          ┌──────┐
 │LSTM  │──→│LSTM  │──→│LSTM  │──→ ... ──→│LSTM  │──→ summary
 │(32)  │   │(32)  │   │(32)  │          │(32)  │   (32-dim)
 └──────┘   └──────┘   └──────┘          └──────┘
                                               │
                                          Dense(16, ReLU)
                                               │
                                          Dense(1, Sigmoid)
                                               │
                                        churn probability
```

Layer 1 (64 units, return_sequences=True): Outputs h_t at every timestep → feeds into Layer 2  
Layer 2 (32 units, return_sequences=False): Only outputs the FINAL h_W → summary of entire sequence

The final summary vector captures the entire trajectory in 32 dimensions. Dense layers project it to a single probability.

---

# Part IV — Time Series and Sliding Windows

---

## Chapter 8: Time Series Concepts

### 8.1 What Is a Time Series?

An ordered sequence of observations over time:
```
t=1: dou_total=18GB, attach=0.95
t=2: dou_total=17GB, attach=0.93
t=3: dou_total=12GB, attach=0.85   ← degradation begins
t=4: dou_total=5GB,  attach=0.40   ← rapid decline
t=5: dou_total=0,    attach=0.0    ← churn
```

**Key properties:**
- **Trend:** long-term direction (increasing, decreasing, stable)
- **Seasonality:** repeating patterns at fixed intervals (daily, weekly)
- **Stationarity:** statistical properties (mean, variance) don't change over time. Most ML models assume stationarity. Non-stationary series need differencing or normalization.
- **Autocorrelation:** how correlated a value is with its past values. High autocorrelation means past values are predictive of future values.

### 8.2 Sliding Window — Your Engine's Core

A sliding window takes a fixed-size chunk of the time series and moves it forward:

```
Full series: [W1, W2, W3, W4, W5, W6, W7, W8, W9, W10]

Window size = 5:
  Step 1: [W1, W2, W3, W4, W5] → features → predict W6
  Step 2: [W2, W3, W4, W5, W6] → features → predict W7
  Step 3: [W3, W4, W5, W6, W7] → features → predict W8
```

**Your engine creates the series from a static snapshot:**
```
Pipeline cycle 1: Sample batch → compute features → store as W1
Pipeline cycle 2: Sample batch → compute features → store as W2
...
Pipeline cycle W: Buffer = [W1, W2, ..., WW] → feed to LSTM
Pipeline cycle W+1: Buffer = [W2, W3, ..., W(W+1)] → window slides forward
```

### 8.3 Window Features — What You Compute Across Windows

For each subscriber, across the last W windows:

**Trend features:**
```
Δ_usage = (usage_t - usage_{t-1}) / usage_{t-1}     — relative change
trend = linear_regression_slope(usage over W windows)  — overall direction
```

**Volatility features:**
```
std_usage = std(usage over W windows)     — how much does usage fluctuate?
cv = std_usage / mean_usage               — coefficient of variation
```

**Degradation features:**
```
consecutive_drops = count of windows where usage_t < usage_{t-1}
max_drawdown = (peak_usage - current_usage) / peak_usage
```

These are the features that make the LSTM powerful — without them, each window is independent.

### 8.4 Granger Causality — Temporal Direction

Granger causality tests whether time series X helps predict time series Y beyond Y's own history.

**The test:**
```
Restricted model:  Y_t = α₁Y_{t-1} + α₂Y_{t-2} + ... + ε    (Y predicts itself)
Full model:        Y_t = α₁Y_{t-1} + ... + β₁X_{t-1} + β₂X_{t-2} + ... + ε

If the full model is significantly better (F-test, p < 0.05):
  → "X Granger-causes Y" (past X values help predict Y)
```

**In your project:**
```
X = OSS cell throughput (aggregated by delegation)
Y = BSS mean CEM score (aggregated by delegation)

Test: Does past throughput help predict future CEM scores?
  If yes → network degradation CAUSES subscriber experience drops
  If no  → they might co-occur but network isn't the driver
```

**Lag selection:** You test multiple lags (1 to 5 windows). Lag=2 means "throughput 2 windows ago predicts CEM score now." The optimal lag tells you the delay between network degradation and subscriber impact — useful for the L4 Agent to know how urgently to act.

---

# Part V — Evaluation Metrics

---

## Chapter 9: How to Know If Your Models Work

### 9.1 Regression Metrics (CEM Score Model)

**R² (Coefficient of Determination):**
```
R² = 1 - (SS_residual / SS_total)
   = 1 - Σ(actual - predicted)² / Σ(actual - mean)²

R² = 1.0  → perfect predictions
R² = 0.0  → model predicts the mean every time (useless)
R² < 0    → model is worse than just guessing the mean
```
Your current SLA model: R² = 0.979 → explains 97.9% of variance. Excellent.

**MAE (Mean Absolute Error):**
```
MAE = mean(|actual - predicted|)
```
Your model: MAE = 0.018 → predictions are off by 0.018 on average (on a 0-1 scale). Interpretable in the same units as the target.

**RMSE (Root Mean Squared Error):**
```
RMSE = sqrt(mean((actual - predicted)²))
```
Penalizes large errors more than MAE (squaring amplifies big misses). If RMSE >> MAE, you have some large outlier errors.

**MSE (Mean Squared Error):**
```
MSE = mean((actual - predicted)²) = RMSE²
```
Same as RMSE but squared. Used as the loss function during training (differentiable), but RMSE is more interpretable for reporting.

### 9.2 Classification Metrics (Underservice, Anomaly, Churn)

**Confusion Matrix — the foundation of everything:**
```
                    Predicted
                 Positive  Negative
Actual Positive [   TP    |   FN   ]
Actual Negative [   FP    |   TN   ]

TP (True Positive):  Model said anomaly, it was anomaly ✓
FP (False Positive): Model said anomaly, it was normal ✗ (false alarm)
FN (False Negative): Model said normal, it was anomaly ✗ (missed detection)
TN (True Negative):  Model said normal, it was normal ✓
```

**Precision:** "Of everything the model flagged, how many were real?"
```
Precision = TP / (TP + FP)

High precision = few false alarms
Low precision = many false alarms → L4 Agent generates junk actions
```

**Recall (Sensitivity):** "Of all real anomalies, how many did the model catch?"
```
Recall = TP / (TP + FN)

High recall = catches most anomalies
Low recall = misses many anomalies → dangerous for CEM monitoring
```

**F1 Score:** Harmonic mean of precision and recall
```
F1 = 2 × (Precision × Recall) / (Precision + Recall)

F1 balances both. High F1 requires BOTH high precision and high recall.
```

**Why F1 and not accuracy?**
```
If 5% of subscribers are anomalous:
  A model that says "nobody is anomalous" has 95% accuracy but 0% recall.
  Useless. F1 would be 0.

F1 forces the model to find the anomalies (recall) without flooding with false alarms (precision).
```

**ROC-AUC:** Area Under the Receiver Operating Characteristic Curve
```
ROC curve: plot True Positive Rate vs False Positive Rate at every threshold

AUC = 1.0: perfect separation (all anomalies score higher than all normals)
AUC = 0.5: random (no discrimination)
AUC < 0.5: worse than random (model is inverted)
```

Your current OSS anomaly model: ROC-AUC = 1.0 → perfect separation on synthetic data. On real data, expect this to decrease — the complexity of 42 features makes perfect separation harder.

### 9.3 Metrics by Model

| Model | Primary Metric | Why This Metric | Target |
|-------|---------------|----------------|--------|
| CEM Score (GBR) | R² + MAE | Regression — measures prediction accuracy | R² > 0.85, MAE < 0.05 |
| Experience Anomaly (AE) | F1 + ROC-AUC | Imbalanced detection — need balance of precision/recall | F1 > 0.80, AUC > 0.90 |
| Churn LSTM | F1 + Recall | Missing a churner is costlier than a false alarm | Recall > 0.85 (catch churners), F1 > 0.75 |
| RAT Underservice (XGB) | Macro-F1 + Per-class F1 | Multi-class — each root cause must be detected | Macro-F1 > 0.80 |
| O+B Correlation | p-value + effect size | Statistical significance of correlations | p < 0.05, |r| > 0.3 |

### 9.4 Cross-Validation — Don't Trust a Single Split

```
Standard train/test split:
  [═══════ Train (80%) ═══════][══ Test (20%) ══]
  → One test result. Might be lucky or unlucky.

5-Fold Cross-Validation:
  Fold 1: [══Test══][═══════════ Train ═══════════]
  Fold 2: [══Train══][══Test══][══════ Train ══════]
  Fold 3: [═══ Train ═══][══Test══][═══ Train ═══]
  Fold 4: [═══════ Train ═══════][══Test══][═Train═]
  Fold 5: [═══════════ Train ═══════════][══Test══]

  → 5 test results. Report mean ± std.
```

Your current model: CV R² = 0.977 ± 0.003 → consistent across folds. The ± 0.003 means the model isn't sensitive to which data it sees — good generalization.

### 9.5 Temporal Cross-Validation (for LSTM)

Standard CV shuffles data randomly. For time series, this leaks future information into training:

```
WRONG (random CV):
  Train: [W1, W3, W5, W7, W9]   Test: [W2, W4, W6, W8, W10]
  → Training on W3 to predict W2 is cheating (W3 is in the future of W2)

RIGHT (temporal CV — walk-forward):
  Fold 1: Train [W1-W5]   Test [W6-W7]
  Fold 2: Train [W1-W7]   Test [W8-W9]
  Fold 3: Train [W1-W9]   Test [W10-W11]
  → Training always on past, testing on future
```

For your LSTM churn model, always use walk-forward validation. Otherwise the metrics will be inflated and the model will underperform in production.

---

# Part VI — MLOps

---

## Chapter 10: Getting Models to Production

### 10.1 What Is MLOps?

MLOps = ML + DevOps. The practices for deploying, monitoring, and maintaining ML models in production.

```
Traditional software:
  Code → Build → Test → Deploy → Monitor
  (Code doesn't change behavior after deployment)

ML systems:
  Data → Train → Evaluate → Deploy → Monitor → Retrain
  (Model behavior changes when data distribution shifts)
```

### 10.2 The ML Lifecycle in Your Platform

```
┌─────────────────────────────────────────────────────────────┐
│                    ML Lifecycle                               │
│                                                              │
│  1. DATA           notebooks/ or pipeline-worker              │
│     Collect, clean, feature-engineer                         │
│         │                                                    │
│  2. TRAIN          notebooks/ (Jupyter)                      │
│     Train model, tune hyperparameters, cross-validate        │
│         │                                                    │
│  3. EVALUATE       notebooks/ (metrics, plots)               │
│     F1, R², AUC, confusion matrix                           │
│         │                                                    │
│  4. SERIALIZE      .joblib (sklearn) or .pt (PyTorch)       │
│     Save model to disk                                       │
│         │                                                    │
│  5. DEPLOY         ai-service container                      │
│     Load model, serve via FastAPI endpoints                  │
│         │                                                    │
│  6. SERVE          pipeline-worker calls ai-service          │
│     Inference on each pipeline cycle                         │
│         │                                                    │
│  7. MONITOR        Prometheus metrics + Grafana              │
│     Track prediction distributions, latency, error rates     │
│         │                                                    │
│  8. RETRAIN        L4 Agent playbook (pb-model-retrain)      │
│     When drift detected → hot-reload models                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 10.3 Model Serialization — joblib vs TorchScript

**joblib (scikit-learn models):**
```python
# Save
import joblib
joblib.dump(model, "cem_score_model.joblib")

# Load
model = joblib.load("cem_score_model.joblib")
prediction = model.predict(features)
```
Saves the entire Python object (model + parameters + preprocessing). Simple, but requires the exact same Python environment to load.

**TorchScript (PyTorch models):**
```python
# Save
scripted = torch.jit.script(model)
scripted.save("autoencoder.pt")

# Load (no Python dependency at inference!)
model = torch.jit.load("autoencoder.pt")
output = model(input_tensor)
```
Converts the PyTorch model to an intermediate representation that can run without Python. Faster inference, portable, production-grade.

### 10.4 Model Versioning

```
models/
  cem_score/
    v2.0_synthetic.joblib       ← current (synthetic data)
    v3.0_real_bss.joblib        ← after retraining on real TT data
  anomaly_detector/
    v2.0_isolation_forest.joblib ← current
    v3.0_autoencoder.pt          ← after DL upgrade
  model_registry.json           ← tracks which version is active
```

The `model_registry` table in PostgreSQL tracks:
- Model name, version, algorithm, training date
- Training data hash (ensures you know which data trained which model)
- Evaluation metrics at training time
- Active/inactive status

### 10.5 Data Drift — Why Models Degrade

**Concept drift:** The relationship between features and target changes. Example: a new 5G rollout changes what "normal" usage looks like. The Autoencoder trained on pre-5G data would flag all 5G subscribers as anomalous.

**Feature drift:** The distribution of input features changes. Example: a new iPhone launch shifts the brand distribution from Samsung-heavy to Apple-heavy.

**How to detect drift:**
```python
# Compare current batch feature distributions with training distributions
from scipy.stats import ks_2samp

# Kolmogorov-Smirnov test
stat, p_value = ks_2samp(training_dou_gb, current_batch_dou_gb)
if p_value < 0.05:
    alert("dou_gb distribution has shifted — consider retraining")
```

**Your L4 Agent handles this:** When drift is detected, the agent can trigger `pb-model-retrain` to hot-reload models. In the future, this could automatically retrain on recent data.

### 10.6 A/B Testing Models

When deploying v3.0 alongside v2.0:
```
Incoming subscriber batch
    ├── 90% → Model v2.0 (production, proven)
    └── 10% → Model v3.0 (canary, being validated)

Compare:
  - v3.0 prediction distribution vs v2.0
  - v3.0 anomaly rate vs v2.0
  - If v3.0 is stable after N cycles → promote to 100%
```

This is shadow deployment — the new model runs in parallel but doesn't affect actions until validated.

---

# Part VII — Docker and Microservices

---

## Chapter 11: Containerization

### 11.1 What Is Docker?

Docker packages an application with ALL its dependencies into an isolated, portable unit called a container.

```
WITHOUT Docker:
  "Works on my machine"
  Python 3.11 on dev, Python 3.9 on server → breaks
  Library version conflicts between services

WITH Docker:
  Each service has its own isolated environment
  Exact same Python, exact same libraries, everywhere
  If it runs locally, it runs on HCS
```

### 11.2 How a Docker Container Works

```
┌─────────────────────────────────────────┐
│           Host OS (Linux)                │
│  ┌──────────┐  ┌──────────┐  ┌────────┐│
│  │Container │  │Container │  │Contain. ││
│  │api-gw    │  │ai-service│  │postgres ││
│  │          │  │          │  │         ││
│  │Python3.11│  │Python3.11│  │PG 16   ││
│  │FastAPI   │  │PyTorch   │  │         ││
│  │psycopg2  │  │sklearn   │  │         ││
│  │Port 8000 │  │Port 8001 │  │Port 5432││
│  └──────────┘  └──────────┘  └────────┘│
│      ↑              ↑            ↑      │
│      └──── Docker Engine ────────┘      │
└─────────────────────────────────────────┘
```

**Container vs VM:**
- VM: Runs a full OS (2-10 GB overhead per VM). Minutes to start.
- Container: Shares the host OS kernel (50-500 MB overhead). Seconds to start.

### 11.3 Dockerfile — The Build Recipe

Your ai-service Dockerfile (conceptual):
```dockerfile
FROM python:3.11-slim            # Base image: minimal Python
WORKDIR /app                      # Working directory in container
COPY requirements.txt .           # Copy dependency list
RUN pip install -r requirements.txt  # Install dependencies
COPY . .                          # Copy service code
EXPOSE 8001                       # Declare port
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

**Layer caching:** Each line is a layer. Docker caches unchanged layers. If only your code changes (last COPY), Docker reuses the cached pip install layer → fast rebuilds.

**Multi-stage builds** (for production):
```dockerfile
# Stage 1: Build
FROM python:3.11-slim AS builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Stage 2: Runtime (smaller image)
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY . .
CMD ["uvicorn", "main:app"]
```
Build tools aren't in the final image → smaller container → faster deployment on HCS.

### 11.4 Docker Compose — Orchestrating 10 Services

```yaml
version: '3.8'
services:
  api-gateway:
    build: ./services/api-gateway
    ports: ["8000:8000"]
    depends_on: [postgres, ai-service]
    environment:
      DB_HOST: postgres
      AI_SERVICE_URL: http://ai-service:8001

  ai-service:
    build: ./services/ai-service
    ports: ["8001:8001"]
    volumes:
      - ./models:/app/models       # Model files mounted from host

  postgres:
    image: postgres:16
    volumes:
      - pg_data:/var/lib/postgresql/data   # Persistent volume
    environment:
      POSTGRES_DB: telecom_intel
```

**Key concepts:**
- `depends_on`: Start order (postgres before api-gateway). Note: doesn't wait for readiness, only for container start.
- `volumes`: Persistent storage that survives container restarts. Without volumes, all data is lost when the container stops.
- Service names (`postgres`, `ai-service`) are DNS names within the Docker network. Services find each other by name, not IP.

### 11.5 Docker Networking

```
┌──── Docker Bridge Network (telecom-net) ────────────────┐
│                                                          │
│  api-gateway ──→ ai-service     (http://ai-service:8001)│
│       │                                                  │
│       ├──→ postgres              (postgres:5432)         │
│       │                                                  │
│       ├──→ minio                 (minio:9000)            │
│       │                                                  │
│  pipeline-worker ──→ ai-service                          │
│       │                                                  │
│       ├──→ postgres                                      │
│       │                                                  │
│       └──→ minio                                         │
│                                                          │
│  dashboard ──→ api-gateway       (api-gateway:8000)      │
│                                                          │
└──────────────────────────────────────────────────────────┘
       │
   Exposed ports (host access):
   localhost:8000 → api-gateway
   localhost:3001 → dashboard
   localhost:9090 → prometheus
```

Services communicate over the internal bridge network using container names. Only explicitly exposed ports are accessible from the host.

---

## Chapter 12: Microservices Architecture

### 12.1 Monolith vs Microservices

```
MONOLITH:
┌─────────────────────────┐
│  ONE application         │
│  - API routes            │
│  - ML inference          │
│  - Data pipeline         │
│  - Authentication        │
│  - All in one process    │
│  - One database          │
│  - Deploy all or nothing │
└─────────────────────────┘

MICROSERVICES:
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ api-gw   │ │ ai-svc   │ │ auth-svc │ │ pipeline │
│          │ │          │ │          │ │          │
│ Routes   │ │ ML models│ │ JWT+OAuth│ │ ETL      │
│ only     │ │ only     │ │ only     │ │ only     │
└──────────┘ └──────────┘ └──────────┘ └──────────┘
     │              │            │            │
     └──────── Shared Database + Message Queue ─┘
```

**Why microservices for your project:**

1. **Independent scaling:** The ai-service (heavy compute for DL inference) can scale to 4 instances while auth-service stays at 1. On HCS, this means different ECS instance sizes per service.

2. **Independent deployment:** Update the Autoencoder model → redeploy only ai-service. Dashboard change → redeploy only dashboard. No risk of breaking unrelated services.

3. **Technology freedom:** api-gateway uses psycopg2 (lightweight). ai-service uses PyTorch (heavyweight). They don't interfere. You could even write a service in Go or Rust if needed.

4. **Fault isolation:** If ai-service crashes (OOM from large batch), api-gateway continues serving cached results. The pipeline-worker retries on the next cycle. In a monolith, one crash kills everything.

5. **Cloud mapping:** Each microservice maps to one ECS instance on HCS. Docker Compose → Kubernetes/HCS orchestration. The architecture IS the deployment.

### 12.2 Communication Patterns

**Synchronous (REST API — your current approach):**
```
pipeline-worker → HTTP POST → ai-service:/infer/anomaly
                 ← HTTP 200 ← { anomalies: [...] }
```
Simple, easy to debug. The caller waits for the response. Used for inference calls where the pipeline needs the result before continuing.

**Asynchronous (Message Queue — future enhancement):**
```
pipeline-worker → publishes message → Queue (Redis/RabbitMQ)
ai-service → subscribes → processes → publishes result
pipeline-worker → consumes result
```
The caller doesn't wait. Better for high-throughput scenarios where you want to process many batches in parallel. Relevant when you scale to millions of subscribers.

### 12.3 Stateless Services — The Cloud-Native Rule

**Stateless:** The service stores NO data locally. All state is in external stores (PostgreSQL, MinIO, Redis).

```
STATEFUL (bad for cloud):
  ai-service keeps model in memory
  If container restarts → model gone → manual reload needed
  If you scale to 3 instances → each has different model version

STATELESS (cloud-native):
  ai-service loads model from MinIO/volume on startup
  If container restarts → reloads from store → same behavior
  If you scale to 3 instances → all load same model → consistent
```

Your services are already stateless:
- Models stored on disk (Docker volume) or MinIO
- All data in PostgreSQL
- Auth tokens are JWT (stateless by design — the token carries the session)
- Pipeline state in PostgreSQL (pipeline_runs table)

### 12.4 Health Checks and Readiness

```python
@app.get("/health")
def health():
    return {"status": "ok"}
```

Every service exposes `/health`. Docker Compose (and Kubernetes/HCS) uses this to:
- **Liveness:** Is the container running? If `/health` fails → restart container.
- **Readiness:** Is the container ready to serve? If models aren't loaded yet → don't route traffic.

### 12.5 The 12-Factor App — Cloud-Native Principles

Your platform follows these (most relevant ones):

| Factor | Principle | Your Implementation |
|--------|-----------|-------------------|
| **Codebase** | One repo, many deploys | One git repo, 10 services built from it |
| **Dependencies** | Explicitly declared | requirements.txt per service |
| **Config** | Store config in environment | DB_HOST, AI_SERVICE_URL as env vars |
| **Backing services** | Treat as attached resources | PostgreSQL, MinIO, Redis are external — swap by changing env var |
| **Port binding** | Export services via port | Each service binds its own port |
| **Concurrency** | Scale by adding processes | Scale ai-service to N containers |
| **Disposability** | Fast startup, graceful shutdown | Containers start in seconds, can be killed and restarted |
| **Logs** | Treat logs as event streams | stdout/stderr → Docker collects → Prometheus scrapes |

---

# Part VIII — Putting It All Together

---

## Chapter 13: How Everything Connects in Your Platform

```
                        REAL TT DATA
                    ┌───────────────────┐
                    │ BSS: 500K subs    │
                    │ OSS: (waiting)    │
                    └────────┬──────────┘
                             │
                    ┌────────▼──────────┐
                    │  Rolling Window    │
                    │  Engine            │
                    │  (pipeline-worker) │  ← Chapter 8: Sliding Window
                    │                    │
                    │  Stratified batch  │
                    │  → Feature eng.    │  ← Chapter 2: Feature Engineering
                    │  → Window buffer   │
                    └────────┬──────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                  │
    ┌──────▼──────┐  ┌──────▼──────┐  ┌───────▼───────┐
    │ GBR         │  │ Autoencoder │  │ XGBoost       │
    │ CEM Score   │  │ Anomaly     │  │ Underservice  │
    │ (Ch.2)      │  │ (Ch.6)      │  │ (Ch.2)        │
    └──────┬──────┘  └──────┬──────┘  └───────┬───────┘
           │                 │                  │
           └────────┬────────┘──────────────────┘
                    │
           ┌────────▼──────────┐
           │  Window Buffer     │
           │  (Redis)           │  ← Chapter 11: Docker, Stateless
           └────────┬──────────┘
                    │
    ┌───────────────┼───────────────┐
    │               │               │
    ▼               ▼               ▼
┌────────┐   ┌──────────┐   ┌─────────────┐
│ LSTM   │   │ Granger  │   │ PostgreSQL  │
│ Churn  │   │ Causality│   │ (results)   │
│(Ch.7)  │   │ (Ch.8)   │   │             │
└───┬────┘   └────┬─────┘   └──────┬──────┘
    │              │                │
    └──────┬───────┘                │
           │                        │
    ┌──────▼──────┐          ┌──────▼──────┐
    │ L4 Agent    │          │ API Gateway │
    │ (Ch.1: ADN) │          │ (Ch.12)     │
    │             │          │             │
    │ Auto-approve│          │ REST API    │
    │ / Human     │          │ JWT auth    │
    └──────┬──────┘          └──────┬──────┘
           │                        │
           └────────┬───────────────┘
                    │
             ┌──────▼──────┐
             │  Dashboard   │
             │  (Next.js)   │
             │              │
             │  15+ pages   │
             │  Real-time   │
             └──────────────┘
                    │
             ┌──────▼──────┐
             │  HCS Deploy  │
             │  (Ch.11-12)  │
             │              │
             │  OBS + RDS   │
             │  + ECS       │
             └──────────────┘
```

Every chapter connects to a concrete component in your platform. The theory isn't abstract — it's implemented.

---

## Quick Reference Card

| Concept | One-line definition | Where in your project |
|---------|-------------------|---------------------|
| RAT | Wireless protocol generation (2G/3G/4G/5G) | generation, highest_rat columns |
| S1/Iu/Gb | Network interfaces between base stations and core | s1_mme_sr, iu_attach_sr, gb_attach_sr |
| USIM | 3G/4G-capable SIM card | usim_flag — 74% are legacy 2G SIM |
| CEM | Customer Experience Management | Your platform's orientation |
| ADN L4 | Autonomous with human oversight for critical | Your L4 Agent |
| GradientBoosting | Ensemble of trees, each correcting previous errors | CEM Score model |
| XGBoost | Optimized gradient boosting with regularization | RAT Underservice model |
| IsolationForest | Anomaly = easy to isolate with random splits | Current v2.0, being replaced |
| Autoencoder | Neural net that compresses and reconstructs | Experience Anomaly model |
| LSTM | RNN with gates for long-range sequence memory | Churn Trajectory model |
| Sliding Window | Fixed-size moving chunk over time series | Your rolling window engine |
| Granger Causality | Past X predicts future Y → X causes Y | O+B correlation engine |
| R² | % of variance explained by model | CEM Score evaluation |
| F1 | Balance of precision and recall | Anomaly/Churn evaluation |
| ROC-AUC | Separation quality across all thresholds | Anomaly model evaluation |
| Docker | Package app + dependencies into isolated container | All 10 services |
| Microservices | Small independent services communicating via API | Your architecture |
| Stateless | No local state, everything in external stores | Cloud-native requirement |
| MLOps | Practices for deploying and maintaining ML models | Your full pipeline |
