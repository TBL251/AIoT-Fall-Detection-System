// =============================================================================
//  fall_detection_buzzer.ino
//  AIoT Fall Detection — ESP32 Buzzer Alarm System
//
//  Serial Protocol (Python → ESP32):
//    '0'  Normal          — stop alarm
//    '1'  Minor Fall      — 2 slow beeps  (400 ms on / 400 ms off)
//    '2'  Dangerous Fall  — 5 fast beeps  (150 ms on / 150 ms off)
//    '3'  Critical        — infinite rapid beeps (100 ms on / 100 ms off)
//                           stops ONLY on command '0' or safety timeout
//
//  Buzzer support:
//    ACTIVE_BUZZER  1  → uses digitalWrite()   (active buzzer)
//    ACTIVE_BUZZER  0  → uses tone()/noTone()  (passive buzzer)
//
//  Architecture: fully non-blocking FSM, no delay() anywhere.
//  Tested on: ESP32 Dev Module, Arduino IDE 2.x, ESP32 core ≥ 2.0
//
//  NOTE: The variable holding FSM state is named 'buz' (not 'alarm') to
//  avoid a collision with the POSIX alarm() function declared in
//  <sys/unistd.h>, which is pulled in transitively by ESP32's newlib headers.
// =============================================================================

// ── Configuration ─────────────────────────────────────────────────────────────

#define BUZZER_PIN        25        // GPIO connected to buzzer
#define ACTIVE_BUZZER     1         // 1 = active (digitalWrite), 0 = passive (tone)
#define PASSIVE_FREQ      2000      // Hz — used only when ACTIVE_BUZZER == 0

#define SAFETY_TIMEOUT_MS 10000UL  // Auto-stop if no command received (ms)
#define DEBOUNCE_MS       80UL     // Ignore repeated commands within this window

// ── Alarm FSM states ──────────────────────────────────────────────────────────

typedef enum : uint8_t {
  ALARM_IDLE = 0,   // buzzer off, nothing running
  ALARM_BEEP_ON,    // buzzer currently sounding
  ALARM_BEEP_OFF,   // buzzer in inter-beep silence
  ALARM_INFINITE    // critical: beep loop, never stops until '0'
} AlarmState;

// ── Runtime state ─────────────────────────────────────────────────────────────
// Named 'buz' to avoid collision with POSIX alarm() in ESP32 newlib headers.

static struct {
  AlarmState    state;
  unsigned long phaseUntil;     // millis() when current ON/OFF phase ends
  int           beepCount;      // beeps completed so far
  int           beepTarget;     // total beeps to play  (0 = infinite)
  unsigned int  onMs;           // buzzer-on duration (ms)
  unsigned int  offMs;          // buzzer-off duration (ms)
  bool          infOn;          // ALARM_INFINITE: tracks current ON/OFF phase
} buz;

static unsigned long lastCommandTime = 0;  // millis() of last valid command
static unsigned long lastCmdReceived = 0;  // millis() for debounce window

// ── Low-level buzzer helpers ──────────────────────────────────────────────────

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
//  stopAlarm()  — hard-stop: silence buzzer and reset ALL state
// =============================================================================

void stopAlarm() {
  buzzerOff();
  buz.state      = ALARM_IDLE;
  buz.phaseUntil = 0;
  buz.beepCount  = 0;
  buz.beepTarget = 0;
  buz.onMs       = 0;
  buz.offMs      = 0;
  buz.infOn      = false;
  Serial.println(F("[ESP32] STOP ALARM"));
}

// =============================================================================
//  startBeep()  — initialise and kick off a beep pattern
//    count == 0  → infinite (Critical Emergency mode)
// =============================================================================

void startBeep(int count, unsigned int onMs, unsigned int offMs) {
  // Hard-stop any currently running pattern so no stale phase leaks through
  if (buz.state != ALARM_IDLE) {
    buzzerOff();
  }

  buz.beepTarget = count;
  buz.beepCount  = 0;
  buz.onMs       = onMs;
  buz.offMs      = offMs;
  buz.infOn      = true;   // always start with buzzer ON
  buz.state      = (count == 0) ? ALARM_INFINITE : ALARM_BEEP_ON;
  buz.phaseUntil = millis() + onMs;

  buzzerOn();

  Serial.print(F("[ESP32] START ALARM — count="));
  Serial.print(count == 0 ? -1 : count);
  Serial.print(F(" on="));
  Serial.print(onMs);
  Serial.print(F("ms off="));
  Serial.print(offMs);
  Serial.println(F("ms"));
}

// =============================================================================
//  tickBeep()  — FSM tick; call every loop(), costs < 1 µs when idle
// =============================================================================

void tickBeep() {
  if (buz.state == ALARM_IDLE) return;

  const unsigned long now = millis();
  if (now < buz.phaseUntil) return;   // still inside current phase

  switch (buz.state) {

    // ── ON phase complete → go OFF ─────────────────────────────────────────
    case ALARM_BEEP_ON:
      buzzerOff();
      buz.state      = ALARM_BEEP_OFF;
      buz.phaseUntil = now + buz.offMs;
      break;

    // ── OFF phase complete → next beep or finish ───────────────────────────
    case ALARM_BEEP_OFF:
      buz.beepCount++;
      if (buz.beepCount >= buz.beepTarget) {
        // Pattern finished naturally — go idle
        buzzerOff();
        buz.state = ALARM_IDLE;
      } else {
        buzzerOn();
        buz.state      = ALARM_BEEP_ON;
        buz.phaseUntil = now + buz.onMs;
      }
      break;

    // ── INFINITE: toggle ON/OFF forever until command '0' ─────────────────
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
      stopAlarm();   // unexpected state — safe fallback
      break;
  }
}

// =============================================================================
//  handleCommand()  — process a validated single-char command
// =============================================================================

void handleCommand(const char cmd) {
  Serial.print(F("[ESP32] RECEIVED COMMAND: '"));
  Serial.print(cmd);
  Serial.println(F("'"));

  switch (cmd) {
    case '0':                              // Normal — stop everything
      stopAlarm();
      break;

    case '1':                              // Minor Fall — 2 slow beeps
      startBeep(2, 400, 400);
      break;

    case '2':                              // Dangerous Fall — 5 fast beeps
      startBeep(5, 150, 150);
      break;

    case '3':                              // Critical Emergency — infinite
      startBeep(0, 100, 100);
      break;

    default:                               // Unknown — log and ignore safely
      Serial.print(F("[ESP32] IGNORED UNKNOWN COMMAND: 0x"));
      Serial.println((uint8_t)cmd, HEX);
      break;
  }
}

// =============================================================================
//  setup()
// =============================================================================

void setup() {
  // Silence the buzzer FIRST — before Serial init — to prevent boot glitch
  pinMode(BUZZER_PIN, OUTPUT);
  buzzerOff();

  Serial.begin(115200);

  // Initialise FSM state
  buz.state      = ALARM_IDLE;
  buz.phaseUntil = 0;
  buz.beepCount  = 0;
  buz.beepTarget = 0;
  buz.onMs       = 0;
  buz.offMs      = 0;
  buz.infOn      = false;

  // Stamp command timer — prevents safety timeout firing immediately at boot
  lastCommandTime = millis();
  lastCmdReceived = millis();

  Serial.println(F("[ESP32] READY — Fall Detection Buzzer v2.1"));
}

// =============================================================================
//  loop()  — high-frequency, minimal overhead
// =============================================================================

void loop() {

  // ── 1. Drain serial buffer ─────────────────────────────────────────────────
  while (Serial.available()) {
    const char c = (char)Serial.read();

    // Discard whitespace / line-endings / null bytes
    if (c == '\n' || c == '\r' || c == ' ' || c == '\0') continue;

    // Serial debounce — ignore if a command arrived too recently
    const unsigned long now = millis();
    if (now - lastCmdReceived < DEBOUNCE_MS) {
      while (Serial.available()) Serial.read();  // flush burst
      break;
    }
    lastCmdReceived = now;
    lastCommandTime = now;   // valid command resets safety timeout

    handleCommand(c);

    // Flush trailing bytes from same burst (e.g. "3\r\n" → only '3' handled)
    while (Serial.available()) Serial.read();
    break;
  }

  // ── 2. Tick buzzer FSM ─────────────────────────────────────────────────────
  tickBeep();

  // ── 3. Safety timeout — auto-stop if no command for SAFETY_TIMEOUT_MS ─────
  if (buz.state != ALARM_IDLE) {
    if (millis() - lastCommandTime > SAFETY_TIMEOUT_MS) {
      Serial.println(F("[ESP32] SAFETY TIMEOUT — no command for 10 s"));
      stopAlarm();
      lastCommandTime = millis();  // re-stamp so message isn't spammed
    }
  }
}
