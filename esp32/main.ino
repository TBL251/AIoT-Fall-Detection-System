// =============================================================================
// AIoT Fall Detection — ESP32 Buzzer FIXED FINAL
// =============================================================================

#define BUZZER_PIN 25
#define ACTIVE_BUZZER 1
#define PASSIVE_FREQ 2000

#define SAFETY_TIMEOUT_MS 10000UL
#define DEBOUNCE_MS 20UL

// ── FSM STATES ───────────────────────────────────────────────────────────────

typedef enum : uint8_t {
  ALARM_IDLE = 0,
  ALARM_BEEP_ON,
  ALARM_BEEP_OFF,
  ALARM_INFINITE
} AlarmState;

static struct {
  AlarmState state;
  unsigned long phaseUntil;

  int beepCount;
  int beepTarget;

  unsigned int onMs;
  unsigned int offMs;

  bool infOn;
} buz;

static unsigned long lastCommandTime = 0;
static unsigned long lastCmdReceived = 0;

// ── BUZZER CONTROL ───────────────────────────────────────────────────────────

static inline void buzzerOn() {
#if ACTIVE_BUZZER
  digitalWrite(BUZZER_PIN, HIGH);
#else
  tone(BUZZER_PIN, PASSIVE_FREQ);
#endif
}

static inline void buzzerOff() {
#if ACTIVE_BUZZER
  digitalWrite(BUZZER_PIN, LOW);
#else
  noTone(BUZZER_PIN);
#endif
}

// =============================================================================
// STOP
// =============================================================================

void stopAlarm() {
  buzzerOff();

  buz.state = ALARM_IDLE;
  buz.phaseUntil = 0;

  buz.beepCount = 0;
  buz.beepTarget = 0;

  buz.onMs = 0;
  buz.offMs = 0;

  buz.infOn = false;

  Serial.println("[ESP32] STOP");
}

// =============================================================================
// START PATTERN
// =============================================================================

void startBeep(int count, unsigned int onMs, unsigned int offMs) {

  if (buz.state != ALARM_IDLE) {
    buzzerOff();
  }

  buz.beepTarget = count;
  buz.beepCount = 0;

  buz.onMs = onMs;
  buz.offMs = offMs;

  buz.infOn = true;

  buz.state = (count == 0) ? ALARM_INFINITE : ALARM_BEEP_ON;
  buz.phaseUntil = millis() + onMs;

  buzzerOn();
}

// =============================================================================
// FSM TICK
// =============================================================================

void tickBeep() {

  if (buz.state == ALARM_IDLE) return;

  unsigned long now = millis();
  if (now < buz.phaseUntil) return;

  switch (buz.state) {

    case ALARM_BEEP_ON:
      buzzerOff();
      buz.state = ALARM_BEEP_OFF;
      buz.phaseUntil = now + buz.offMs;
      break;

    case ALARM_BEEP_OFF:

      buz.beepCount++;

      // finish pattern
      if (buz.beepTarget != 0 && buz.beepCount >= buz.beepTarget) {
        stopAlarm();
        return;
      }

      buz.state = ALARM_BEEP_ON;
      buz.phaseUntil = now + buz.onMs;
      buzzerOn();
      break;

    case ALARM_INFINITE:

      buz.infOn = !buz.infOn;

      if (buz.infOn) {
        buzzerOn();
        buz.phaseUntil = now + buz.onMs;
      } else {
        buzzerOff();
        buz.phaseUntil = now + buz.offMs;
      }
      break;

    default:
      stopAlarm();
      break;
  }
}

// =============================================================================
// COMMAND HANDLER (FIXED TIMING)
// =============================================================================

void handleCommand(char cmd) {

  Serial.print("[CMD] ");
  Serial.println(cmd);

  switch (cmd) {

    case '0':
      stopAlarm();
      break;

    case '1':   // nhẹ → nghỉ 3s
      startBeep(1, 200, 3000);
      break;

    case '2':   // trung bình → nghỉ 2s
      startBeep(2, 200, 2000);
      break;

    case '3':   // nguy hiểm → chu kỳ 1s
      startBeep(0, 150, 1000);
      break;
  }
}

// =============================================================================
// SETUP
// =============================================================================

void setup() {

  pinMode(BUZZER_PIN, OUTPUT);
  buzzerOff();

  Serial.begin(115200);

  buz.state = ALARM_IDLE;

  lastCommandTime = millis();
  lastCmdReceived = millis();

  Serial.println("[ESP32] READY");
}

// =============================================================================
// LOOP
// =============================================================================

void loop() {

  // ── SERIAL READ ───────────────────────────────────────────────────────────
  while (Serial.available() > 0) {

    char c = (char)Serial.read();

    if (c == '\n' || c == '\r' || c == ' ') continue;

    unsigned long now = millis();

    if (now - lastCmdReceived < DEBOUNCE_MS) break;

    lastCmdReceived = now;
    lastCommandTime = now;

    handleCommand(c);
    break;
  }

  // ── FSM ───────────────────────────────────────────────────────────────────
  tickBeep();

  // ── SAFETY STOP ───────────────────────────────────────────────────────────
  if (buz.state != ALARM_IDLE) {
    if (millis() - lastCommandTime > SAFETY_TIMEOUT_MS) {
      Serial.println("[ESP32] TIMEOUT STOP");
      stopAlarm();
      lastCommandTime = millis();
    }
  }
}