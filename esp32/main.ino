// =============================================================================
// AIoT Fall Detection — ESP32 BUZZER FINAL
// =============================================================================

#define BUZZER_PIN     25
#define ACTIVE_BUZZER  1
#define PASSIVE_FREQ   2000

#define SAFETY_TIMEOUT_MS  10000UL
#define DEBOUNCE_MS        20UL

// ── FSM STATES ───────────────────────────────────────────────────────────────

// FIX: removed ALARM_INFINITE — it was dead code. All three active commands
// (1, 2, 3) call startBeep(0, …) which routes to ALARM_BEEP_ON, so
// ALARM_INFINITE was unreachable. A single BEEP_ON / BEEP_OFF pair with
// beepTarget == 0 meaning "loop forever" covers every real use-case cleanly.

typedef enum : uint8_t {
  ALARM_IDLE = 0,
  ALARM_BEEP_ON,
  ALARM_BEEP_OFF,
} AlarmState;

static struct {
  AlarmState   state;
  unsigned long phaseUntil;

  int          beepCount;
  int          beepTarget;   // 0 = loop forever

  unsigned int onMs;
  unsigned int offMs;
} buz;

// ── TIMERS ───────────────────────────────────────────────────────────────────

static unsigned long lastCmdReceived = 0;   // for debounce
static unsigned long lastCommandTime = 0;   // for safety timeout

// =============================================================================
// BUZZER LOW LEVEL
// =============================================================================

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
// STOP ALARM (NORMAL)
// =============================================================================

void stopAlarm() {
  buzzerOff();

  buz.state      = ALARM_IDLE;
  buz.phaseUntil = 0;
  buz.beepCount  = 0;
  buz.beepTarget = 0;

  Serial.println("[ESP32] STOP (NORMAL)");
}

// =============================================================================
// START ALARM
// =============================================================================

void startBeep(int count, unsigned int onMs, unsigned int offMs) {
  buzzerOff();

  buz.beepTarget = count;   // 0 = loop forever
  buz.beepCount  = 0;
  buz.onMs       = onMs;
  buz.offMs      = offMs;

  // Always begin in the ON phase so the buzzer fires immediately.
  buz.state      = ALARM_BEEP_ON;
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
      buz.state      = ALARM_BEEP_OFF;
      buz.phaseUntil = now + buz.offMs;
      break;

    case ALARM_BEEP_OFF:
      buz.beepCount++;

      // Stop only when a finite target is reached.
      if (buz.beepTarget != 0 && buz.beepCount >= buz.beepTarget) {
        stopAlarm();
        return;
      }

      // Loop (or continue counting).
      buz.state      = ALARM_BEEP_ON;
      buz.phaseUntil = now + buz.onMs;
      buzzerOn();
      break;

    default:
      stopAlarm();
      break;
  }
}

// =============================================================================
// COMMAND HANDLER
// =============================================================================

void handleCommand(char cmd) {
  Serial.print("[CMD] ");
  Serial.println(cmd);

  switch (cmd) {
    case '0':                         // NORMAL — silence
      stopAlarm();
      break;

    case '1':                         // MINOR — slow pulse
      startBeep(0, 200, 3000);
      break;

    case '2':                         // DANGEROUS — medium pulse
      startBeep(0, 200, 1200);
      break;

    case '3':                         // CRITICAL — rapid pulse
      startBeep(0, 200, 400);
      break;

    default:
      Serial.print("[ESP32] Unknown command: ");
      Serial.println(cmd);
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

  lastCmdReceived = millis();
  lastCommandTime = millis();

  Serial.println("[ESP32] READY");
}

// =============================================================================
// LOOP
// =============================================================================

void loop() {

  // ── SERIAL INPUT ───────────────────────────────────────────────────────────
  if (Serial.available() > 0) {

    char c   = (char)Serial.read();
    unsigned long now = millis();

    // FIX: skip whitespace BEFORE the debounce check so control characters
    // consumed here don't reset lastCmdReceived and don't count as a command
    // for the purposes of the debounce window.
    if (c == '\n' || c == '\r' || c == ' ') {
      // consume and move on — don't touch timestamps
    }
    else if (now - lastCmdReceived < DEBOUNCE_MS) {
      // FIX: was `break` (left char in buffer → re-read every loop until
      // 20 ms elapsed → command fires repeatedly). Now we consume the char
      // and skip it so it is processed exactly once after the window clears.
      // Character is already consumed by Serial.read() above — do nothing.
    }
    else {
      lastCmdReceived = now;
      lastCommandTime = now;   // valid command resets the safety timer
      handleCommand(c);
    }
  }

  // ── FSM RUN ────────────────────────────────────────────────────────────────
  tickBeep();

  // ── SAFETY AUTO-STOP ───────────────────────────────────────────────────────
  // FIX: do NOT reset lastCommandTime here. The old code reset it after every
  // timeout, which meant that if the MCU had been idle (ALARM_IDLE) for >10 s
  // and then received an alarm command, the very next loop tick would see
  // (millis() - lastCommandTime) > SAFETY_TIMEOUT_MS and immediately stop the
  // alarm that just started.  By NOT resetting lastCommandTime in the timeout
  // handler, the timer only restarts when a real command arrives (above).
  if (buz.state != ALARM_IDLE) {
    if (millis() - lastCommandTime > SAFETY_TIMEOUT_MS) {
      Serial.println("[ESP32] TIMEOUT STOP");
      stopAlarm();
      // Do NOT touch lastCommandTime here — see note above.
    }
  }
}
