// Gesture Controlled LED Blinking
// Receives finger data from Python via Serial

const int pins[5] = {2, 3, 4, 5, 6};  
// index, middle, ring, pinky, thumb

void setup() {
  Serial.begin(115200);

  // Set LED pins as output
  for (int i = 0; i < 5; i++) {
    pinMode(pins[i], OUTPUT);
    digitalWrite(pins[i], LOW);
  }
}

void loop() {

  if (Serial.available()) {

    int mask = Serial.parseInt();  
    // Python sends numbers like 0–31

    for (int i = 0; i < 5; i++) {

      if (mask & (1 << i)) {
        digitalWrite(pins[i], HIGH);   // LED ON
      }
      else {
        digitalWrite(pins[i], LOW);    // LED OFF
      }

    }
  }

}
