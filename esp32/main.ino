#define BUZZER_PIN 25

// Initialise to millis() equivalent — done in setup()
unsigned long lastCommandTime = 0;

bool alarmActive = false;

// Non-blocking alarm state
unsigned long alarmUntil   = 0;   // millis() when current beep phase ends
bool          buzzerOn     = 0;
int           beepCount    = 0;
int           beepTarget   = 0;
unsigned int  beepOnMs     = 0;
unsigned int  beepOffMs    = 0;
bool          inBeepOn     = false;


// =====================
// SETUP
// =====================

void setup() {

  Serial.begin(115200);

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  lastCommandTime = millis();   // FIX: prevent spurious safety-stop at boot

  Serial.println("[ESP32] READY");
}


// =====================
// START A BEEP PATTERN (non-blocking)
// =====================

void startBeep(int count, unsigned int onMs, unsigned int offMs) {
  beepTarget  = count;
  beepCount   = 0;
  beepOnMs    = onMs;
  beepOffMs   = offMs;
  inBeepOn    = true;
  alarmActive = true;                     // FIX: actually set the flag
  digitalWrite(BUZZER_PIN, HIGH);
  alarmUntil  = millis() + onMs;
}


// =====================
// TICK BEEP STATE MACHINE  (call every loop)
// =====================

void tickBeep() {

  if (!alarmActive) return;

  if (millis() < alarmUntil) return;     // still waiting in current phase

  if (inBeepOn) {
    // ON phase done → go OFF
    digitalWrite(BUZZER_PIN, LOW);
    inBeepOn   = false;
    alarmUntil = millis() + beepOffMs;
  } else {
    // OFF phase done → next beep or finish
    beepCount++;
    if (beepCount >= beepTarget) {
      alarmActive = false;               // pattern complete
    } else {
      digitalWrite(BUZZER_PIN, HIGH);
      inBeepOn   = true;
      alarmUntil = millis() + beepOnMs;
    }
  }
}


// =====================
// STOP ALARM
// =====================

void stopAlarm() {
  digitalWrite(BUZZER_PIN, LOW);
  alarmActive = false;
  beepCount   = beepTarget;             // abort any running pattern
}


// =====================
// HANDLE COMMAND
// =====================

void handleCommand(char cmd) {

  Serial.print("[ESP32] RECEIVED: ");
  Serial.println(cmd);

  switch (cmd) {

    // NORMAL
    case '0':
      stopAlarm();
      break;

    // MINOR FALL  — 2 slow beeps
    case '1':
      startBeep(2, 400, 400);
      break;

    // DANGEROUS FALL — 5 fast beeps
    case '2':
      startBeep(5, 150, 150);
      break;

    // CRITICAL EMERGENCY — 20 rapid beeps
    case '3':
      startBeep(20, 100, 100);
      break;

    default:
      Serial.println("[ESP32] UNKNOWN COMMAND");
  }
}


// =====================
// MAIN LOOP
// =====================

void loop() {

  // =====================
  // RECEIVE SERIAL
  // =====================

  if (Serial.available()) {

    char command = Serial.read();       // FIX: local variable, not stale global

    lastCommandTime = millis();

    handleCommand(command);
  }

  // =====================
  // TICK NON-BLOCKING BEEP
  // =====================

  tickBeep();

  // =====================
  // AUTO SAFETY STOP
  // =====================

  if (millis() - lastCommandTime > 10000) {
    stopAlarm();
  }
}
