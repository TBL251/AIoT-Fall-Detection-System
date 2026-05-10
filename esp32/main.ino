#define BUZZER_PIN 25

int command = 0;

void setup() {
  Serial.begin(115200);
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
}

// =====================
// BEEP FUNCTIONS
// =====================

void beepSlow() {
  for (int i = 0; i < 2; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(400);
    digitalWrite(BUZZER_PIN, LOW);
    delay(400);
  }
}

void beepFast() {
  for (int i = 0; i < 5; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(150);
    digitalWrite(BUZZER_PIN, LOW);
    delay(150);
  }
}

void alarmContinuous() {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(3000);
  digitalWrite(BUZZER_PIN, LOW);
}

// =====================
// MAIN LOOP
// =====================

void loop() {

  if (Serial.available()) {

    command = Serial.read();

    // LEVEL 0
    if (command == '0') {
      digitalWrite(BUZZER_PIN, LOW);
    }

    // LEVEL 1 - Minor
    else if (command == '1') {
      beepSlow();
    }

    // LEVEL 2 - Dangerous
    else if (command == '2') {
      beepFast();
    }

    // LEVEL 3 - Critical
    else if (command == '3') {
      alarmContinuous();
    }
  }
}