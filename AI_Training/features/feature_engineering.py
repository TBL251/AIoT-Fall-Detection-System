"""
features/feature_engineering.py
────────────────────────────────
Produces a (T, F) feature matrix from a (T, 34) raw keypoint sequence.

Feature breakdown (default 74D):
  34  normalized keypoint coordinates  (norm_xy)
  34  frame-to-frame velocities        (vel)
   6  biomechanical joint angles       (angles)
  ──
  74  total

To expand to 115D, uncomment the accel / spatial / bbox blocks and set
FEATURES = 115 in config.py.
"""

import numpy as np
from AI_Training.configs.config import FEATURES

# ─── COCO keypoint indices ──────────────────────────────────────────────────
KP_NOSE  = 0
KP_LSHO, KP_RSHO = 5, 6
KP_LELB, KP_RELB = 7, 8
KP_LWRI, KP_RWRI = 9, 10
KP_LHIP, KP_RHIP = 11, 12
KP_LKNE, KP_RKNE = 13, 14
KP_LANK, KP_RANK = 15, 16


# ─── Helpers ────────────────────────────────────────────────────────────────

def _to_xy(kp: np.ndarray) -> np.ndarray:
    """Reshape (34,) → (17, 2)."""
    return kp.reshape(17, 2).astype(np.float32)


def _normalize(xy: np.ndarray) -> np.ndarray:
    """
    Hip-centred, torso-scale normalisation.
    Hip midpoint → origin; torso length (hip→shoulder) → unit scale.
    """
    hip      = (xy[KP_LHIP] + xy[KP_RHIP])   / 2.0
    shoulder = (xy[KP_LSHO] + xy[KP_RSHO])   / 2.0
    scale    = np.linalg.norm(shoulder - hip) + 1e-6
    return (xy - hip) / scale


def _angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Interior angle at vertex b (radians)."""
    ba  = a - b
    bc  = c - b
    cos = np.dot(ba, bc) / (
        (np.linalg.norm(ba) + 1e-6) * (np.linalg.norm(bc) + 1e-6)
    )
    return float(np.arccos(np.clip(cos, -1.0, 1.0)))


def _joint_angles(xy: np.ndarray) -> np.ndarray:
    """
    Six biomechanical angles (radians):
      0  trunk tilt   – arctan2 of spine vector
      1  left  knee
      2  right knee
      3  left  hip
      4  right hip
      5  shoulder span (via nose)
    """
    hip  = (xy[KP_LHIP] + xy[KP_RHIP]) / 2.0
    sho  = (xy[KP_LSHO] + xy[KP_RSHO]) / 2.0
    spine = sho - hip
    trunk = float(np.arctan2(spine[0], spine[1] + 1e-6))

    return np.array([
        trunk,
        _angle(xy[KP_LHIP],  xy[KP_LKNE], xy[KP_LANK]),
        _angle(xy[KP_RHIP],  xy[KP_RKNE], xy[KP_RANK]),
        _angle(xy[KP_LSHO],  xy[KP_LHIP], xy[KP_LKNE]),
        _angle(xy[KP_RSHO],  xy[KP_RHIP], xy[KP_RKNE]),
        _angle(xy[KP_LSHO],  xy[KP_NOSE], xy[KP_RSHO]),
    ], dtype=np.float32)


# ─── Main pipeline ──────────────────────────────────────────────────────────

def extract_features(seq) -> np.ndarray:
    """
    Parameters
    ----------
    seq : array-like, shape (T, 34)
        Raw keypoint sequence (flattened x,y per frame).

    Returns
    -------
    np.ndarray, shape (T, FEATURES)
    """
    seq = np.asarray(seq, dtype=np.float32)       # (T, 34)
    T   = len(seq)

    # 1. Hip-centred normalisation
    norm = np.zeros((T, 17, 2), dtype=np.float32)
    for t in range(T):
        norm[t] = _normalize(_to_xy(seq[t]))

    # 2. Velocity  (central difference, prepend first frame)
    vel = np.diff(norm, axis=0, prepend=norm[:1])  # (T, 17, 2)

    # 3. Flatten spatial + velocity
    x_flat = norm.reshape(T, 34)                   # (T, 34)
    v_flat = vel.reshape(T, 34)                    # (T, 34)

    # 4. Biomechanical joint angles
    angles = np.array(
        [_joint_angles(norm[t]) for t in range(T)],
        dtype=np.float32,
    )                                              # (T,  6)

    # ── Assemble feature matrix ──────────────────────────────────────────
    feat = np.concatenate([x_flat, v_flat, angles], axis=1)  # (T, 74)

    # ── Optional: accel / spatial ratios / bounding box ─────────────────
    # Uncomment the block below AND set FEATURES = 115 in config.py
    # to match the full 115D specification.
    #
    # accel = np.diff(vel, axis=0, prepend=vel[:1]).reshape(T, 34)  # (T,34)
    #
    # def _spatial_ratios(xy):
    #     hip_w  = np.linalg.norm(xy[KP_LHIP]  - xy[KP_RHIP])  + 1e-6
    #     sho_w  = np.linalg.norm(xy[KP_LSHO]  - xy[KP_RSHO])  + 1e-6
    #     leg_l  = (np.linalg.norm(xy[KP_LHIP] - xy[KP_LANK]) +
    #               np.linalg.norm(xy[KP_RHIP] - xy[KP_RANK])) / 2.0 + 1e-6
    #     torso  = np.linalg.norm((xy[KP_LSHO]+xy[KP_RSHO])/2 -
    #                              (xy[KP_LHIP]+xy[KP_RHIP])/2) + 1e-6
    #     return np.array([sho_w/hip_w, torso/leg_l, hip_w/leg_l], np.float32)
    #
    # def _body_bbox(xy):
    #     valid = xy[np.any(xy != 0, axis=1)]
    #     if len(valid) < 2:
    #         return np.zeros(4, np.float32)
    #     xmin, ymin = valid.min(axis=0)
    #     xmax, ymax = valid.max(axis=0)
    #     w, h = xmax - xmin + 1e-6, ymax - ymin + 1e-6
    #     return np.array([w, h, w/h, (xmin+xmax)/2], np.float32)
    #
    # spatial = np.array([_spatial_ratios(norm[t]) for t in range(T)])  # (T,3)
    # bbox    = np.array([_body_bbox(norm[t])       for t in range(T)])  # (T,4)
    # feat = np.concatenate([x_flat, v_flat, accel, angles, spatial, bbox], axis=1)  # (T,115)
    # ─────────────────────────────────────────────────────────────────────

    # Runtime shape guard
    if feat.shape[1] != FEATURES:
        raise ValueError(
            f"[feature_engineering] Expected {FEATURES}D features, "
            f"got {feat.shape[1]}D. "
            f"Check FEATURES in config.py matches the active pipeline."
        )

    return feat.astype(np.float32)