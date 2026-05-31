// =====================================================
// ESP32 Fall Detection Buzzer — FINAL STABLE VERSION
// =====================================================

#define BUZZER_PIN 25

// 🔥 CHANGE THIS BASED ON YOUR BUZZER TYPE
// 1 = active buzzer (HIGH = ON)
// 0 = passive buzzer (tone)
#define ACTIVE_BUZZER 1

#define PASSIVE_FREQ 2000
#define SAFETY_TIMEOUT_MS 10000
#define DEBOUNCE_MS 80

// ---------------- FSM ----------------

enum State : uint8_t {
  IDLE,
  BEEP_ON,
  BEEP_OFF,
  INFINITE
};

struct Buzzer {
  State state = IDLE;
  unsigned long nextTime = 0;

  int target = 0;
  int count = 0;

  unsigned int onMs = 0;
  unsigned int offMs = 0;

  bool toggle = false;
} buz;

// ---------------- TIME ----------------

unsigned long lastCmdTime = 0;
unsigned long lastRxTime = 0;

// ---------------- BUZZER LOW LEVEL ----------------

void buzzerOn() {
#if ACTIVE_BUZZER
  digitalWrite(BUZZER_PIN, HIGH);
#else
  tone(BUZZER_PIN, PASSIVE_FREQ);
#endif
}

void buzzerOff() {
#if ACTIVE_BUZZER
  digitalWrite(BUZZER_PIN, LOW);
#else
  noTone(BUZZER_PIN);
#endif
}

// ---------------- STOP ----------------

void stopBuzzer() {
  buzzerOff();
  buz.state = IDLE;
  buz.count = 0;
  buz.target = 0;
  Serial.println("[ESP32] STOP");
}

// ---------------- START PATTERN ----------------

void startPattern(int count, int onMs, int offMs) {

  buz.state = (count == 0) ? INFINITE : BEEP_ON;
  buz.target = count;
  buz.count = 0;

  buz.onMs = onMs;
  buz.offMs = offMs;

  buz.toggle = true;
  buz.nextTime = millis() + onMs;

  buzzerOn();

  Serial.print("[ESP32] START count=");
  Serial.println(count == 0 ? -1 : count);
}

// ---------------- FSM TICK ----------------

void tick() {

  if (buz.state == IDLE) return;

  unsigned long now = millis();
  if (now < buz.nextTime) return;

  switch (buz.state) {

    case BEEP_ON:
      buzzerOff();
      buz.state = BEEP_OFF;
      buz.nextTime = now + buz.offMs;
      break;

    case BEEP_OFF:
      buz.count++;

      if (buz.count >= buz.target) {
        stopBuzzer();
      } else {
        buzzerOn();
        buz.state = BEEP_ON;
        buz.nextTime = now + buz.onMs;
      }
      break;

    case INFINITE:
      buz.toggle = !buz.toggle;

      if (buz.toggle) {
        buzzerOn();
        buz.nextTime = now + buz.onMs;
      } else {
        buzzerOff();
        buz.nextTime = now + buz.offMs;
      }
      break;

    default:
      stopBuzzer();
      break;
  }
}

// ---------------- HANDLE COMMAND ----------------

void handle(char c) {

  Serial.print("[ESP32] CMD=");
  Serial.println(c);

  switch (c) {

    case '0':
      stopBuzzer();
      break;

    case '1':
      startPattern(2, 400, 400);
      break;

    case '2':
      startPattern(5, 150, 150);
      break;

    case '3':
      startPattern(0, 100, 100);
      break;
  }
}

// ---------------- SETUP ----------------

void setup() {

  pinMode(BUZZER_PIN, OUTPUT);
  buzzerOff();

  Serial.begin(115200);
  delay(1000);

  Serial.println("[ESP32] READY");
}

// ---------------- LOOP ----------------

void loop() {

  // ---------- Serial ----------
  while (Serial.available()) {

    char c = Serial.read();

    if (c == '\n' || c == '\r' || c == ' ') continue;

    unsigned long now = millis();

    if (now - lastRxTime < DEBOUNCE_MS) return;

    lastRxTime = now;
    lastCmdTime = now;

    handle(c);

    while (Serial.available()) Serial.read();
    break;
  }

  // ---------- FSM ----------
  tick();

  // ---------- Safety timeout ----------
  if (buz.state != IDLE) {
    if (millis() - lastCmdTime > SAFETY_TIMEOUT_MS) {
      Serial.println("[ESP32] TIMEOUT STOP");
      stopBuzzer();
    }
  }
}