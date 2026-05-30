"""
lstm/model.py
─────────────
TCN + Multi-Head Attention binary classifier for fall detection.

Architecture:
  Input (T, F)
  → TCN Block ×4  [64 → 128 → 256 → 128 filters, causal, dilated]
  → Multi-Head Self-Attention
  → Global Average Pooling
  → Dense(128) → Dropout → Dense(1, sigmoid)
"""

import tensorflow as tf
from configs.config import (
    SEQUENCE_LENGTH, FEATURES,
    TCN_FILTERS, TCN_KERNEL_SIZE, TCN_DROPOUT,
    TCN_DENSE_UNITS, ATTENTION_HEADS, ATTENTION_KEY_DIM,
    LEARNING_RATE, WEIGHT_DECAY,
    FOCAL_GAMMA, FOCAL_ALPHA,
)


# ─── Focal Loss ─────────────────────────────────────────────────────────────

def focal_loss(gamma: float = FOCAL_GAMMA, alpha: float = FOCAL_ALPHA):
    """
    Binary focal loss:
        FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)

    Down-weights easy negatives (normal frames) so the model focuses
    on hard positives (ambiguous fall onset), which is critical when
    the fall class is rare in the wild.
    """
    def loss_fn(y_true, y_pred):
        y_true = tf.cast(y_true, tf.float32)
        y_pred = tf.clip_by_value(y_pred, 1e-7, 1.0 - 1e-7)

        bce     = -y_true * tf.math.log(y_pred) \
                  - (1.0 - y_true) * tf.math.log(1.0 - y_pred)
        p_t     = y_true * y_pred + (1.0 - y_true) * (1.0 - y_pred)
        alpha_t = y_true * alpha  + (1.0 - y_true) * (1.0 - alpha)
        fl      = alpha_t * tf.pow(1.0 - p_t, gamma) * bce

        return tf.reduce_mean(fl)

    loss_fn.__name__ = "focal_loss"
    return loss_fn


# ─── TCN Residual Block ──────────────────────────────────────────────────────

def _tcn_block(
    x: tf.Tensor,
    filters: int,
    kernel_size: int,
    dilation_rate: int,
    dropout_rate: float,
) -> tf.Tensor:
    """
    One residual TCN block:
        Conv1D (causal, dilated) → BatchNorm → ReLU → Dropout
        → Conv1D (causal, dilated) → BatchNorm → ReLU → Dropout
        → 1×1 projection (if channel mismatch) → Add → ReLU

    Causal padding ensures no future leakage during inference.
    Dilation enlarges the receptive field without extra parameters.
    """
    # ─ main path ─────────────────────────────────────────────────────────
    h = tf.keras.layers.Conv1D(
        filters, kernel_size,
        padding="causal", dilation_rate=dilation_rate, activation=None,
    )(x)
    h = tf.keras.layers.BatchNormalization()(h)
    h = tf.keras.layers.Activation("relu")(h)
    h = tf.keras.layers.Dropout(dropout_rate)(h)

    h = tf.keras.layers.Conv1D(
        filters, kernel_size,
        padding="causal", dilation_rate=dilation_rate, activation=None,
    )(h)
    h = tf.keras.layers.BatchNormalization()(h)
    h = tf.keras.layers.Activation("relu")(h)
    h = tf.keras.layers.Dropout(dropout_rate)(h)

    # ─ skip connection: project x if channel dim differs ─────────────────
    if x.shape[-1] != filters:
        x = tf.keras.layers.Conv1D(filters, 1, padding="same")(x)

    return tf.keras.layers.Activation("relu")(
        tf.keras.layers.Add()([x, h])
    )


# ─── Build Model ─────────────────────────────────────────────────────────────

def build_model(
    input_shape: tuple = (SEQUENCE_LENGTH, FEATURES),
) -> tf.keras.Model:
    """
    Build, compile, and return the TCN-Attention fall-detection model.

    Parameters
    ----------
    input_shape : (T, F)
        T = SEQUENCE_LENGTH, F = FEATURES

    Returns
    -------
    tf.keras.Model  (compiled, ready for .fit)
    """
    inputs = tf.keras.Input(shape=input_shape, name="pose_sequence")
    x      = inputs

    # ── TCN stack with exponential dilation ──────────────────────────────
    for i, filters in enumerate(TCN_FILTERS):
        dilation = 2 ** i          # 1, 2, 4, 8  → receptive field = 45 frames
        x = _tcn_block(
            x, filters, TCN_KERNEL_SIZE,
            dilation_rate=dilation,
            dropout_rate=TCN_DROPOUT,
        )

    # ── Multi-Head Self-Attention ─────────────────────────────────────────
    att = tf.keras.layers.MultiHeadAttention(
        num_heads=ATTENTION_HEADS,
        key_dim=ATTENTION_KEY_DIM,
        dropout=TCN_DROPOUT,
        name="temporal_attention",
    )(x, x)
    x = tf.keras.layers.Add()([x, att])
    x = tf.keras.layers.LayerNormalization()(x)

    # ── Temporal pooling ──────────────────────────────────────────────────
    x = tf.keras.layers.GlobalAveragePooling1D()(x)

    # ── Dense head ────────────────────────────────────────────────────────
    x = tf.keras.layers.Dense(TCN_DENSE_UNITS, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.4)(x)
    x = tf.keras.layers.Dense(32, activation="relu")(x)

    outputs = tf.keras.layers.Dense(1, activation="sigmoid", name="fall_prob")(x)

    model = tf.keras.Model(inputs, outputs, name="TCN_FallDetector")

    optimizer = tf.keras.optimizers.AdamW(
        learning_rate=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
    )

    model.compile(
        optimizer=optimizer,
        loss=focal_loss(gamma=FOCAL_GAMMA, alpha=FOCAL_ALPHA),
        metrics=[
            "accuracy",
            tf.keras.metrics.AUC(name="auc"),
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )

    return model