/*
 * as5600_diagnostic.ino — AS5600 bench diagnostic (Serial only)
 * ─────────────────────────────────────────────────────────────────────────────
 * Standalone health check for the AS5600 on the Swimnetics reel hardware.
 * NO BLE, NO motor, NO buffer — just polls every 3 s and prints to Serial:
 *   1. Wiring     — does the AS5600 ACK on the I2C bus at 0x36?
 *   2. Magnet     — STATUS register (MD/ML/MH bits) + AGC gain reading.
 *   3. Angle      — raw 12-bit angle (0..4095) and its degree value.
 *
 * Wiring (identical to ESP_32_V5.ino):
 *   AS5600 SDA → GPIO21    AS5600 SCL → GPIO22    AS5600 VCC → 3V3    GND → GND
 *
 * Open Serial Monitor at 115200 baud.
 */

#include <Wire.h>

// ── Pins (match ESP_32_V5.ino) ─────────────────────────────────────────────────
#define PIN_SDA 21
#define PIN_SCL 22

// ── AS5600 ──────────────────────────────────────────────────────────────────────
#define AS5600_ADDR    0x36
#define REG_STATUS     0x0B
#define REG_RAWANGLE_H 0x0C
#define REG_AGC        0x1A   // automatic gain control — proxy for magnet gap
#define MD_BIT (1 << 5)       // magnet detected
#define ML_BIT (1 << 4)       // magnet too weak (gap too large)
#define MH_BIT (1 << 3)       // magnet too strong (gap too small)

#define POLL_INTERVAL_MS 3000

// Read a single register byte. Returns true on success, value in *out.
static bool readReg(uint8_t reg, uint8_t *out) {
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;   // no ACK on the write
  if (Wire.requestFrom(AS5600_ADDR, 1) != 1) return false;
  *out = Wire.read();
  return true;
}

// Read the raw 12-bit angle (0x0C/0x0D). Returns true on success.
static bool readAngle(uint16_t *out) {
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(REG_RAWANGLE_H);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(AS5600_ADDR, 2) != 2) return false;
  uint16_t hi = Wire.read();
  uint16_t lo = Wire.read();
  *out = ((hi & 0x0F) << 8) | lo;
  return true;
}

// Returns true if the AS5600 ACKs its address on the bus (wiring/power OK).
static bool deviceAcks() {
  Wire.beginTransmission(AS5600_ADDR);
  return Wire.endTransmission() == 0;
}

static void poll() {
  Serial.println(F("──────────────────────────────────────────────"));

  // 1. Wiring — bus presence
  if (!deviceAcks()) {
    Serial.println(F("[1] WIRING  : FAIL — no ACK from AS5600 @ 0x36"));
    Serial.println(F("              Check SDA→GPIO21, SCL→GPIO22, 3V3, GND,"));
    Serial.println(F("              and that VCC/DIR are not floating."));
    return;   // nothing else is meaningful without a bus
  }
  Serial.println(F("[1] WIRING  : OK   — AS5600 ACKs @ 0x36 (SDA=21 SCL=22)"));

  // 2. Magnet — STATUS bits + AGC
  uint8_t status, agc;
  if (!readReg(REG_STATUS, &status) || !readReg(REG_AGC, &agc)) {
    Serial.println(F("[2] MAGNET  : FAIL — ACK but register read failed (intermittent wiring?)"));
    return;
  }
  bool md = status & MD_BIT;
  bool ml = status & ML_BIT;
  bool mh = status & MH_BIT;
  Serial.printf("[2] MAGNET  : status=0x%02X  MD=%d ML=%d MH=%d  AGC=%u\n",
                status, md, ml, mh, agc);
  if (!md)      Serial.println(F("              → NOT DETECTED — place/align the magnet over the chip"));
  else if (ml)  Serial.println(F("              → TOO WEAK — magnet too far; reduce the air gap"));
  else if (mh)  Serial.println(F("              → TOO STRONG — magnet too close; increase the air gap"));
  else          Serial.println(F("              → OK — magnet detected, gap in range"));

  // 3. Angle — raw counts + degrees
  uint16_t angle;
  if (!readAngle(&angle)) {
    Serial.println(F("[3] ANGLE   : FAIL — register read failed"));
    return;
  }
  Serial.printf("[3] ANGLE   : raw=%u / 4095   (%.1f deg)\n",
                angle, angle * 360.0f / 4096.0f);
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(400000);

  Serial.println();
  Serial.println(F("AS5600 diagnostic — polling every 3 s (Serial only)"));
  Serial.printf("I2C: SDA=GPIO%d  SCL=GPIO%d  addr=0x%02X  400kHz\n",
                PIN_SDA, PIN_SCL, AS5600_ADDR);
}

void loop() {
  poll();
  delay(POLL_INTERVAL_MS);
}
