"""
lstm/train.py
─────────────
Training script for the TCN fall-detection model.

Features:
  - Focal loss (combat class imbalance)
  - AdamW optimiser with cosine annealing LR schedule
  - Data augmentation (noise, flip, time-warp, speed, keypoint-drop)
  - Class-weighted sampling as additional safeguard
  - Best-model checkpoint + early stopping
"""

from __future__ import annotations

import os
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.utils.class_weight import compute_class_weight

from lstm.model import build_model
from configs.config import (
    SAVE_X, SAVE_Y,
    EPOCHS, BATCH_SIZE, LEARNING_RATE, LEARNING_RATE as LR,
    LR_MIN, LR_WARMUP_EPOCHS,
    CLASS_WEIGHT_FALL, CLASS_WEIGHT_NORMAL,
    AUG_NOISE_STD, AUG_FLIP_PROB,
    AUG_TIMEWARP_PROB, AUG_DROP_PROB,
    AUG_SPEED_RANGE, AUG_MAX_DROP_KP,
    SEQUENCE_LENGTH, FEATURES,
)


# ─── Data Augmentation ───────────────────────────────────────────────────────

def augment_sequence(x: np.ndarray) -> np.ndarray:
    """
    Apply stochastic augmentations to a single sequence (T, F).

    Augmentations
    ─────────────
    1. Gaussian noise  — adds small perturbations to all features
    2. Horizontal flip — mirrors x-coordinates (left↔right keypoints)
    3. Time warp       — resamples temporal axis with a random factor
    4. Speed variation — crops/stretches sequence to simulate speed change
    5. Keypoint drop   — zeros out random joints to simulate occlusion
    """
    x = x.copy()
    T, F = x.shape

    # 1. Gaussian noise
    x += np.random.normal(0, AUG_NOISE_STD, x.shape).astype(np.float32)

    # 2. Horizontal flip (negate x-coordinates, indices 0,2,4,… of norm block)
    if np.random.rand() < AUG_FLIP_PROB:
        x[:, 0::2] = -x[:, 0::2]

    # 3. Time warp (resample along time axis)
    if np.random.rand() < AUG_TIMEWARP_PROB:
        lo, hi   = AUG_SPEED_RANGE
        factor   = np.random.uniform(lo, hi)
        new_len  = max(2, int(T * factor))
        src_idx  = np.linspace(0, T - 1, new_len)
        tgt_idx  = np.linspace(0, new_len - 1, T)
        warped   = np.zeros_like(x)
        for f in range(F):
            warped[:, f] = np.interp(tgt_idx, np.arange(new_len),
                                     np.interp(src_idx, np.arange(T), x[:, f]))
        x = warped

    # 4. Random keypoint dropout (zero out up to AUG_MAX_DROP_KP joints)
    if np.random.rand() < AUG_DROP_PROB:
        n_drop = np.random.randint(1, AUG_MAX_DROP_KP + 1)
        for _ in range(n_drop):
            kp  = np.random.randint(0, 17)
            xi  = kp * 2          # x-coord index in 34D block
            yi  = kp * 2 + 1
            x[:, xi] = 0.0
            x[:, yi] = 0.0
            # also zero corresponding velocity indices
            if F >= 68:           # velocity block starts at 34
                x[:, 34 + xi] = 0.0
                x[:, 34 + yi] = 0.0

    return x.astype(np.float32)


# ─── Augmented tf.data pipeline ──────────────────────────────────────────────

def make_dataset(
    X: np.ndarray,
    y: np.ndarray,
    augment: bool = False,
    batch_size: int = BATCH_SIZE,
    shuffle: bool = True,
) -> tf.data.Dataset:
    """
    Build a tf.data.Dataset from numpy arrays.
    Augmentation is applied in CPU via tf.numpy_function for flexibility.
    """

    def _aug_fn(x_np, y_np):
        x_out = augment_sequence(x_np)
        return x_out.astype(np.float32), np.float32(y_np)

    def _aug_tf(x, y):
        x_aug, y_aug = tf.numpy_function(
            _aug_fn, [x, y], [tf.float32, tf.float32]
        )
        x_aug.set_shape([SEQUENCE_LENGTH, FEATURES])
        y_aug.set_shape([])
        return x_aug, y_aug

    ds = tf.data.Dataset.from_tensor_slices(
        (X.astype(np.float32), y.astype(np.float32))
    )

    if shuffle:
        ds = ds.shuffle(buffer_size=len(X), reshuffle_each_iteration=True)

    if augment:
        ds = ds.map(_aug_tf, num_parallel_calls=tf.data.AUTOTUNE)

    return ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)


# ─── Cosine Annealing with Warm-up ───────────────────────────────────────────

def cosine_lr_schedule(epoch: int) -> float:
    """Warm-up for LR_WARMUP_EPOCHS, then cosine anneal to LR_MIN."""
    if epoch < LR_WARMUP_EPOCHS:
        return LR * (epoch + 1) / LR_WARMUP_EPOCHS
    progress = (epoch - LR_WARMUP_EPOCHS) / max(1, EPOCHS - LR_WARMUP_EPOCHS)
    return LR_MIN + 0.5 * (LR - LR_MIN) * (1.0 + np.cos(np.pi * progress))


# ─── Training Entry Point ────────────────────────────────────────────────────

def train() -> None:
    # ── Load data ─────────────────────────────────────────────────────────
    X = np.load(SAVE_X)   # (N, T, F)
    y = np.load(SAVE_Y)   # (N,)

    print(f"Loaded  X={X.shape}  y={y.shape}")
    print(f"Class distribution: fall={int((y==1).sum())}  "
          f"normal={int((y==0).sum())}")

    # ── Train / val split ─────────────────────────────────────────────────
    X_tr, X_val, y_tr, y_val = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )

    # ── Class weights (extra safeguard on top of focal loss) ──────────────
    cw_arr = compute_class_weight(
        class_weight="balanced", classes=np.array([0, 1]), y=y_tr
    )
    class_weight = {
        0: cw_arr[0] * CLASS_WEIGHT_NORMAL,
        1: cw_arr[1] * CLASS_WEIGHT_FALL,
    }
    print(f"Class weights: {class_weight}")

    # ── tf.data pipelines ─────────────────────────────────────────────────
    train_ds = make_dataset(X_tr,  y_tr,  augment=True,  shuffle=True)
    val_ds   = make_dataset(X_val, y_val, augment=False, shuffle=False)

    # ── Model ─────────────────────────────────────────────────────────────
    model = build_model()
    model.summary()

    # ── Callbacks ─────────────────────────────────────────────────────────
    os.makedirs("models", exist_ok=True)

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            "models/tcn_fall_best.keras",
            monitor="val_auc", mode="max",
            save_best_only=True, verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_auc", patience=15,
            restore_best_weights=True, verbose=1,
        ),
        tf.keras.callbacks.LearningRateScheduler(cosine_lr_schedule, verbose=0),
        tf.keras.callbacks.TensorBoard(
            log_dir="output/logs/tensorboard", histogram_freq=0,
        ),
    ]

    # ── Fit ───────────────────────────────────────────────────────────────
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=EPOCHS,
        class_weight=class_weight,
        callbacks=callbacks,
        verbose=1,
    )

    # ── Save final model ──────────────────────────────────────────────────
    model.save("models/tcn_fall.keras")
    print("\n✔  Training complete. Models saved to models/")

    return history


if __name__ == "__main__":
    train()