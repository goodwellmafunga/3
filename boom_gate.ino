#include <Servo.h>

Servo myServo;
String command;

void setup() {
  Serial.begin(9600);
  myServo.attach(9);
  myServo.write(0); // Ensure the servo is initially closed
}

void loop() {
  if (Serial.available() > 0) {
    command = Serial.readStringUntil('\n');
    if (command == "open") {
      myServo.write(90); // Move servo to 90 degrees
      delay(5000);       // Wait for 5 seconds
      myServo.write(0);  // Move servo back to 0 degrees
    }
  }
}
