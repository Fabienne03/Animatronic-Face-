/*
 * mouth_servo_driver.ino
 *
 * Arduino Mega 2560 driver for the 4-servo TPU-bar mouth, controlled over
 * serial by face_to_servo.py.
 *
 * Protocol (one char per line, newline-terminated):
 *     N = neutral   H = happy   S = sad   A = anger   P = surprise
 *
 * Wiring (default):
 *     Mouth servo UL (upper-left)   -> digital pin 2, signal
 *     Mouth servo UR (upper-right)  -> digital pin 3, signal
 *     Mouth servo LL (lower-left)   -> digital pin 4, signal
 *     Mouth servo LR (lower-right)  -> digital pin 5, signal
 *     All servo V+   -> external 5 V / 5 A supply (NOT Mega's 5V pin)
 *     All servo GND  -> supply GND AND Mega GND (common ground mandatory)
 *     1000 uF cap across the servo rail near the servos.
 *
 * Expects: face_to_servo.py sending at 115200 baud.
 */

#include <Servo.h>

// ===========================================================================
// Per-servo config.  Edit one row to change everything about that servo.
// ===========================================================================

struct MouthServo {
  uint8_t pin;      // Mega digital pin carrying the PWM signal
  int     center;   // microseconds at NEUTRAL (bar is flat)
  int     span;     // microseconds of max offset from center
  int8_t  dir;      // +1 or -1 -- flip if a servo moves the wrong way
  Servo   servo;
};

MouthServo mouth[4] = {
  { 2, 1500, 400, +1 },   // UL - upper left
  { 3, 1500, 400, -1 },   // UR - upper right
  { 4, 1500, 400, +1 },   // LL - lower left
  { 5, 1500, 400, -1 },   // LR - lower right
};
enum { UL = 0, UR = 1, LL = 2, LR = 3 };

// Safety clamp: never command outside this window regardless of math.
static const int PULSE_MIN = 1000;
static const int PULSE_MAX = 2000;

// ===========================================================================
// Expression keyframes.  Values are normalized -1.0 .. +1.0; the toPulse()
// function converts them to microseconds using each servo's own calibration.
// Convention:  +1.0 = that bar end rotates UP, -1.0 = that bar end rotates DOWN.
// ===========================================================================

struct Expression { float ul, ur, ll, lr; };

const Expression NEUTRAL   = {  0.0,  0.0,  0.0,  0.0 };  // both bars flat
const Expression HAPPY     = { +0.8, +0.8, +0.8, +0.8 };  // both bars bow up (smile)
const Expression SAD       = { -0.8, -0.8, -0.8, -0.8 };  // both bars bow down (frown)
const Expression ANGRY     = { -0.3, -0.3, +0.3, +0.3 };  // bars press together
const Expression SURPRISED = { +0.6, +0.6, -0.9, -0.9 };  // upper up, lower down (open O)

// ===========================================================================
// Non-blocking animator state
// ===========================================================================

Expression startPose     = NEUTRAL;
Expression targetPose    = NEUTRAL;
Expression currentPose   = NEUTRAL;
unsigned long animStart  = 0;
unsigned long animLen    = 400;
bool          animating  = false;

// ---- Conversion & write ----
int toPulse(int i, float norm) {
  if (norm >  1.0) norm =  1.0;
  if (norm < -1.0) norm = -1.0;
  int p = mouth[i].center + mouth[i].dir * (int)(norm * mouth[i].span);
  if (p < PULSE_MIN) p = PULSE_MIN;
  if (p > PULSE_MAX) p = PULSE_MAX;
  return p;
}

void writePose(const Expression& e) {
  mouth[UL].servo.writeMicroseconds(toPulse(UL, e.ul));
  mouth[UR].servo.writeMicroseconds(toPulse(UR, e.ur));
  mouth[LL].servo.writeMicroseconds(toPulse(LL, e.ll));
  mouth[LR].servo.writeMicroseconds(toPulse(LR, e.lr));
}

// ---- Smoothstep interpolation (ease in / out) ----
Expression lerpPose(const Expression& a, const Expression& b, float t) {
  if (t < 0) t = 0;
  if (t > 1) t = 1;
  float k = t * t * (3.0f - 2.0f * t);
  return {
    a.ul + (b.ul - a.ul) * k,
    a.ur + (b.ur - a.ur) * k,
    a.ll + (b.ll - a.ll) * k,
    a.lr + (b.lr - a.lr) * k,
  };
}

void startTransition(const Expression& target, unsigned long durationMs) {
  startPose   = currentPose;
  targetPose  = target;
  animStart   = millis();
  animLen     = durationMs;
  animating   = true;
}

// Called every loop iteration.  Advances the current pose a step closer to
// the target and writes it out.  Non-blocking -- no delay() involved.
void tickAnimation() {
  if (!animating) return;
  unsigned long elapsed = millis() - animStart;
  if (elapsed >= animLen) {
    currentPose = targetPose;
    animating   = false;
  } else {
    float t     = (float)elapsed / (float)animLen;
    currentPose = lerpPose(startPose, targetPose, t);
  }
  writePose(currentPose);
}

// ===========================================================================
// Command handling
// ===========================================================================

void handleCommand(char c) {
  switch (c) {
    case 'N': startTransition(NEUTRAL,   400); Serial.println("ok N"); break;
    case 'H': startTransition(HAPPY,     400); Serial.println("ok H"); break;
    case 'S': startTransition(SAD,       400); Serial.println("ok S"); break;
    case 'A': startTransition(ANGRY,     400); Serial.println("ok A"); break;
    case 'P': startTransition(SURPRISED, 300); Serial.println("ok P"); break;  // snappier
    default:
      Serial.print("?? unknown: ");
      Serial.println(c);
      break;
  }
}

// ===========================================================================
// Setup / main loop
// ===========================================================================

void setup() {
  for (int i = 0; i < 4; i++) {
    mouth[i].servo.attach(mouth[i].pin, PULSE_MIN, PULSE_MAX);
  }

  // Land on neutral immediately on power-up.
  writePose(NEUTRAL);
  currentPose = NEUTRAL;

  Serial.begin(115200);
  Serial.println("ready");
}

void loop() {
  // Parse one character at a time; ignore CR/LF.  We only act on A-Z.
  while (Serial.available()) {
    char c = Serial.read();
    if (c >= 'A' && c <= 'Z') {
      handleCommand(c);
    }
    // '\n', '\r', spaces, and other bytes are silently ignored.
  }

  tickAnimation();

  // 100 Hz tick is plenty for servos and leaves CPU free for future features
  // (brow and eyelid servos, sensors, etc.)
  delay(10);
}
