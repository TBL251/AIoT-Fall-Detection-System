# =========================
# SEQUENCE
# =========================

SEQUENCE_LENGTH = 30          # primary window (30 frames @ 30fps = 1 second)
STRIDE          = 1           # stride=1 for training (dense overlap windows)
FEATURES        = 74          # feature set: 34 norm_xy + 34 vel + 6 joint_angles = 74
                              # NOTE: accel (+34), spatial_ratios (+3), body_bbox (+4)
                              # can be re-enabled to reach 115D (update FEATURES accordingly)

# Multi-scale windows fed to TCN branches
MULTI_SCALE_WINDOWS = [15, 30, 60]   # short / mid / long-range context

# =========================
# MODEL
# =========================

CONFIDENCE_THRESHOLD  = 0.50
CALIBRATION_TEMP      = 1.0

YOLO_MODEL   = "AI_Training/models/yolov8s-pose.pt"
TCN_MODEL    = "AI_Training/models/tcn_fall.keras"
SCALER_PATH  = "AI_Training/models/scaler.pkl"

# Legacy compatibility alias
LSTM_MODEL = TCN_MODEL

# =========================
# SMOOTHING / POST-PROCESSING
# =========================

EMA_ALPHA        = 0.6
VOTE_WINDOW      = 7
VOTE_THRESHOLD   = 4
HYSTERESIS_ON    = 0.55
HYSTERESIS_OFF   = 0.35

# =========================
# DATASET PATHS
# =========================

UR_RAW_PATH   = "AI_Training/dataset/raw/ur"
LE2I_RAW_PATH = "AI_Training/dataset/raw/le2i"

SEQUENCES_DIR = "AI_Training/dataset/sequences"
POSE_DIR      = "AI_Training/dataset/pose"
PROCESSED_DIR = "AI_Training/dataset/processed"

SAVE_X      = "AI_Training/dataset/processed/X.npy"
SAVE_Y      = "AI_Training/dataset/processed/y.npy"
SAVE_LABELS = "AI_Training/dataset/processed/labels.json"

# =========================
# LABELS
# =========================

LABELS = {
    "normal": 0,
    "fall":   1,
}

# =========================
# INFERENCE SPEED
# =========================

YOLO_IMGSZ  = 320
YOLO_CONF   = 0.40
SKIP_FRAMES = 2

# =========================
# TRAINING
# =========================

FOCAL_GAMMA   = 2.0
FOCAL_ALPHA   = 0.75

EPOCHS        = 80
BATCH_SIZE    = 32
LEARNING_RATE = 3e-4
WEIGHT_DECAY  = 1e-4

LR_WARMUP_EPOCHS = 5
LR_MIN           = 1e-6

CLASS_WEIGHT_FALL   = 3.0
CLASS_WEIGHT_NORMAL = 1.0

# =========================
# TCN ARCHITECTURE
# =========================

TCN_FILTERS       = [64, 128, 256, 128]
TCN_KERNEL_SIZE   = 3
TCN_DROPOUT       = 0.20
TCN_DENSE_UNITS   = 128
ATTENTION_HEADS   = 4
ATTENTION_KEY_DIM = 32

# =========================
# AUGMENTATION
# =========================

AUG_NOISE_STD     = 0.008
AUG_FLIP_PROB     = 0.50
AUG_TIMEWARP_PROB = 0.40
AUG_DROP_PROB     = 0.35
AUG_SPEED_RANGE   = (0.75, 1.25)
AUG_MAX_DROP_KP   = 4

# =========================
# OUTPUT PATHS
# =========================

OUTPUT_DIR = "AI_Training/output"
VIDEO_DIR  = "AI_Training/output/videos"
LOG_DIR    = "AI_Training/output/logs"
PRED_DIR   = "AI_Training/output/predictions"