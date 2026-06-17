/*
 * ESP_32_V5.ino — ESP32-WROOM-32 reel-motor + AS5600 BLE buffer-and-dump logger
 * ─────────────────────────────────────────────────────────────────────────────
 * Based on motor_logger_esp32.ino (same hardware), with recording changed from
 * live BLE streaming to buffer-and-dump: the device records into RAM with NO
 * phone present (button start/stop), then dumps the buffered session over BLE
 * on request. Sample format unchanged: 7 bytes
 * <IHB = uint32 timestamp_us LE | uint16 angle_counts LE | uint8 magnet_ok.
 *
 * Wiring (identical to motor_logger_esp32):
 *   AS5600 SDA  → GPIO21     AS5600 SCL  → GPIO22
 *   DRV8833 IN1 → GPIO25     DRV8833 IN2 → GPIO26
 *   LED anode   → GPIO27 → 330Ω → GND
 *   Button      → GPIO32 → GND  (internal pull-up, no external resistor)
 *   DRV8833 EEP (nSLEEP) hardwired to VCC — always enabled.
 *   Power: USB-C battery (5V) → ESP32 Vin + DRV8833 VCC.
 *
 * LED states (priority order):
 *   2 Hz blink         — motor running
 *   10 Hz rapid blink  — error (magnet not detected / buffer full)
 *   5 Hz fast blink    — recording into RAM buffer
 *   Double-pulse / 2 s — data ready (session buffered, awaiting dump)
 *   Solid ON           — BLE connected, idle
 *   1 Hz slow blink    — advertising
 *
 * Button (GPIO32 — recording does NOT require a BLE connection):
 *   Short press                  → toggle recording
 *     while idle/data-ready      → start a NEW recording (buffer overwritten)
 *     while recording            → stop, keep buffer, enter data-ready
 *   Long press (hold ≥ 800 ms)   → toggle reel motor
 *
 * BLE commands (write to RX characteristic, ASCII):
 *   "START"    → begin recording (same as short press)
 *   "STOP"     → stop recording  (same as short press)
 *   "META"     → notify one 8-byte packet:
 *                [session_start_us: uint32 LE][device_now_us: uint32 LE]
 *                session_start_us == 0 means no buffered session.
 *                (8 bytes is not a multiple of 7 → sample parsers ignore it.)
 *   "DUMP"     → stream the buffered samples via TX notify in packets of
 *                DUMP_SAMPLES_PER_PACKET × 7 bytes, then a single-byte 0xEE
 *                end-of-dump marker. Buffer cleared after a complete dump;
 *                a dump aborted by disconnect retains the buffer for retry.
 *   "STATUS"   → notify one 15-byte live-diagnostics packet:
 *                [0]      0xDD  (status marker — distinct from the 0xEE end marker)
 *                [1]      AS5600 status register (0x0B; MD/ML/MH bits)
 *                [2]      magnet_ok (0/1, same logic as readMagnetOk)
 *                [3]      AS5600 AGC register (0x1A; gain → magnet-gap health)
 *                [4..5]   raw angle uint16 LE (0x0C, 12-bit)
 *                [6]      flags: bit0=recording bit1=dataReady bit2=motorRunning
 *                [7..10]  bufCount    uint32 LE
 *                [11..14] maxSamples  uint32 LE
 *                15 is not 8, not 1, not a multiple of 7 → sample/META/end
 *                parsers ignore it. Lets the phone show magnet/wiring/buffer
 *                health with no laptop or serial monitor.
 *   "REEL_ON"  → start motor CW
 *   "REEL_OFF" → stop motor
 *
 * BLE read characteristics:
 *   ID_UUID → 6-char ASCII chip ID (e.g. "A1B2C3"), stable across reboots
 *   FW_UUID → firmware version string
 *
 * Buffer: sized at boot from the largest free heap block (minus a reserve for
 * BLE runtime allocations), capped at BUFFER_SECONDS at ~270 Hz × 7 B/sample.
 * The achieved capacity in seconds is printed at boot. Total free heap
 * overstates what malloc can give — only the largest contiguous block matters.
 *
 * Requires: ESP32 Arduino core (BLEDevice, BLEServer, BLE2902)
 */

#include <Wire.h>
#include <esp_heap_caps.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>

// ── Debug ─────────────────────────────────────────────────────────────────────
#define DEBUG 1
#if DEBUG
  #define DBG(fmt, ...) Serial.printf("[%7lu] " fmt "\n", millis(), ##__VA_ARGS__)
#else
  #define DBG(fmt, ...)
#endif

// ── Pins ──────────────────────────────────────────────────────────────────────
#define PIN_SDA    21
#define PIN_SCL    22
#define PIN_LED    27
#define PIN_BUTTON 32   // internal pull-up — wire button to GND only, no resistor
#define PIN_IN1    25   // DRV8833 IN1
#define PIN_IN2    26   // DRV8833 IN2

// ── Motor config ──────────────────────────────────────────────────────────────
#define CW_FORWARD  false   // flip to false if motor turns wrong way
#define MAX_RUN_S  120     // auto-stop timeout (seconds)
#define BRAKE_MS    80     // brake hold before coast-off

// ── AS5600 ────────────────────────────────────────────────────────────────────
#define AS5600_ADDR    0x36
#define REG_STATUS     0x0B
#define REG_RAWANGLE_H 0x0C
#define REG_AGC        0x1A   // automatic gain control — proxy for magnet gap
#define MD_BIT (1 << 5)   // magnet detected
#define ML_BIT (1 << 4)   // too weak
#define MH_BIT (1 << 3)   // too strong

// ── BLE (Nordic UART Service + device ID) ────────────────────────────────────
// Device name is built at runtime: "SwimLogger-XXXXXX"
#define SERVICE_UUID "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
#define TX_UUID      "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"  // ESP32 → app (notify)
#define RX_UUID      "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"  // app → ESP32 (write)
#define ID_UUID      "6E400004-B5A3-F393-E0A9-E50E24DCCA9E"  // chip ID (read-only)
#define FW_UUID      "6E400005-B5A3-F393-E0A9-E50E24DCCA9E"  // firmware version (read-only)
#define FIRMWARE_VERSION "1.1.0"

// ── Timing ────────────────────────────────────────────────────────────────────
#define SAMPLE_INTERVAL_US 3704   // ~270 Hz
#define DEBOUNCE_MS        50
#define LONG_PRESS_MS      800    // hold this long → motor toggle instead of record
#define ERROR_DISPLAY_MS   2000
#define STATUS_INTERVAL_MS 5000

// ── Buffer ────────────────────────────────────────────────────────────────────
#define SAMPLE_RATE_HZ     270
#define BUFFER_SECONDS     60     // upper cap; actual size from largest free block
#define MAX_SAMPLES_CAP    ((uint32_t)SAMPLE_RATE_HZ * BUFFER_SECONDS)
#define BLE_HEAP_HEADROOM  32768  // bytes left free for BLE runtime allocations
#define MIN_BUFFER_SECONDS 10     // fatal if even this doesn't fit

// ── Dump ──────────────────────────────────────────────────────────────────────
// 24 samples × 7 = 168 bytes per notify. Any multiple of 7 is valid for all
// existing parsers. Requires negotiated MTU ≥ 171 (bleak and iOS both provide).
// If bench testing shows truncated packets, drop to 4 — correctness over speed.
#define DUMP_SAMPLES_PER_PACKET 24
#define DUMP_PACKET_DELAY_MS    5     // avoid Bluedroid TX-queue saturation
#define END_OF_DUMP_MARKER      0xEE  // 1 byte ≠ multiple of 7 → ignored by sample parsers

// ── Diagnostics (STATUS) ───────────────────────────────────────────────────────
#define STATUS_MARKER      0xDD   // first byte of the STATUS packet; ≠ END_OF_DUMP_MARKER
#define STATUS_PACKET_SIZE 15     // not 8 (META), not 1 (end), not a multiple of 7

// ── LED states ────────────────────────────────────────────────────────────────
enum LedState {
  LED_MOTOR,
  LED_ERROR,
  LED_RECORDING,
  LED_READY,      // session buffered, awaiting dump
  LED_IDLE,
  LED_PAIRING,
};

static const char* ledStateName(LedState s) {
  switch (s) {
    case LED_MOTOR:     return "MOTOR";
    case LED_ERROR:     return "ERROR";
    case LED_RECORDING: return "RECORDING";
    case LED_READY:     return "READY";
    case LED_IDLE:      return "IDLE";
    case LED_PAIRING:   return "PAIRING";
    default:            return "UNKNOWN";
  }
}

// ── Global state ──────────────────────────────────────────────────────────────
static volatile bool  deviceConnected = false;
static volatile bool  recording       = false;
static volatile bool  dataReady       = false;   // buffered session awaiting dump
static volatile bool  motorRunning    = false;

// Deferred BLE command flags — set in BLE callback, executed in loop() on main task.
// Prevents blocking or I2C calls on the BLE FreeRTOS task.
static volatile bool  pendingMotorStart  = false;
static volatile bool  pendingMotorStop   = false;
static volatile bool  pendingRecordStart = false;
static volatile bool  pendingRecordStop  = false;
static volatile bool  pendingMeta        = false;
static volatile bool  pendingDump        = false;
static volatile bool  pendingStatus      = false;

static LedState  ledState     = LED_PAIRING;
static uint32_t  errorClearMs = 0;
static uint32_t  motorStartMs = 0;

// Chip ID — last 3 bytes of ESP32 MAC, e.g. "A1B2C3"
static char chipId[7];

// BLE
static BLEServer         *pServer = nullptr;
static BLECharacteristic *pTxChar = nullptr;

// Sample buffer — packed so an array slice is byte-identical to the wire format
// (<IHB, 7 bytes) and can be notified straight from the buffer.
struct __attribute__((packed)) Sample { uint32_t ts; uint16_t angle; uint8_t mag; };
static Sample  *sampleBuf      = nullptr;
static uint32_t maxSamples     = 0;   // actual buffer capacity, set in setup()
static uint32_t bufCount       = 0;
static uint32_t sessionStartUs = 0;   // timestamp_us of the buffered session's first sample
static uint32_t lastSampleUs   = 0;

// Button debounce + short/long press
static bool     btnLastRaw     = HIGH;   // last raw read (for edge detection)
static bool     btnStable      = HIGH;   // debounced state
static uint32_t btnDebounceMs  = 0;
static uint32_t btnPressMs     = 0;      // when the debounced press began
static bool     btnLongFired   = false;  // long-press action already taken this hold

// Heartbeat
static uint32_t lastStatusMs = 0;

// ── AS5600 helpers ────────────────────────────────────────────────────────────
static uint16_t readAngle() {
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(REG_RAWANGLE_H);
  Wire.endTransmission(false);
  Wire.requestFrom(AS5600_ADDR, 2);
  return ((uint16_t)(Wire.read() & 0x0F) << 8) | Wire.read();
}

static uint8_t readMagnetStatus() {
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(REG_STATUS);
  Wire.endTransmission(false);
  Wire.requestFrom(AS5600_ADDR, 1);
  return Wire.read();
}

static uint8_t readMagnetOk() {
  uint8_t s = readMagnetStatus();
  return ((s & MD_BIT) && !(s & ML_BIT) && !(s & MH_BIT)) ? 1 : 0;
}

static uint8_t readAgc() {
  Wire.beginTransmission(AS5600_ADDR);
  Wire.write(REG_AGC);
  Wire.endTransmission(false);
  Wire.requestFrom(AS5600_ADDR, 1);
  return Wire.read();
}

// ── LED helpers ───────────────────────────────────────────────────────────────
static void setLedState(LedState next) {
  if (next != ledState) {
    DBG("[LED] %s → %s", ledStateName(ledState), ledStateName(next));
    ledState = next;
  }
}

static void syncLed() {
  if (motorRunning)         setLedState(LED_MOTOR);
  else if (recording)       setLedState(LED_RECORDING);
  else if (dataReady)       setLedState(LED_READY);
  else if (deviceConnected) setLedState(LED_IDLE);
  else                      setLedState(LED_PAIRING);
}

// ── Motor control ─────────────────────────────────────────────────────────────
static void motorStart() {
  if (motorRunning) { DBG("[MOTOR] Start ignored — already running"); return; }
  uint8_t a = CW_FORWARD ? HIGH : LOW;
  uint8_t b = CW_FORWARD ? LOW  : HIGH;
  digitalWrite(PIN_IN1, a);
  digitalWrite(PIN_IN2, b);
  motorRunning = true;
  motorStartMs = millis();
  setLedState(LED_MOTOR);
  DBG("[MOTOR] Start — IN1=%d IN2=%d (%s)", a, b, CW_FORWARD ? "CW" : "CCW");
}

static void motorStop() {
  if (!motorRunning) { DBG("[MOTOR] Stop ignored — not running"); return; }
  uint32_t ranMs = millis() - motorStartMs;
  DBG("[MOTOR] Brake — IN1=HIGH IN2=HIGH");
  digitalWrite(PIN_IN1, HIGH);
  digitalWrite(PIN_IN2, HIGH);
  delay(BRAKE_MS);   // brief sampling stall if recording — timestamps stay real, resampling handles it
  DBG("[MOTOR] Coast — IN1=LOW IN2=LOW");
  digitalWrite(PIN_IN1, LOW);
  digitalWrite(PIN_IN2, LOW);
  motorRunning = false;
  DBG("[MOTOR] Stopped — ran for %lu ms", ranMs);
  syncLed();
}

static void checkMotorTimeout() {
  if (!motorRunning) return;
  uint32_t elapsed = millis() - motorStartMs;
  static uint32_t lastMotorLogMs = 0;
  if (elapsed - lastMotorLogMs >= 5000) {
    DBG("[MOTOR] Running... %lu s elapsed (limit %d s)", elapsed / 1000, MAX_RUN_S);
    lastMotorLogMs = elapsed;
  }
  if (elapsed >= (uint32_t)MAX_RUN_S * 1000) {
    DBG("[MOTOR] AUTO-STOP — %d s timeout exceeded", MAX_RUN_S);
    motorStop();
    lastMotorLogMs = 0;
  }
}

// ── Recording control (buffer mode — no BLE connection required) ─────────────
static void startRecording(const char *source) {
  if (recording) { DBG("[REC] Start ignored — already recording"); return; }
  uint8_t magStatus = readMagnetStatus();
  uint8_t magOk     = readMagnetOk();
  DBG("[REC] Magnet status byte=0x%02X ok=%d", magStatus, magOk);
  if (!magOk) {
    DBG("[REC] ERROR — magnet not detected, cannot record (via %s)", source);
    setLedState(LED_ERROR);
    errorClearMs = millis() + ERROR_DISPLAY_MS;
    return;
  }
  if (dataReady)
    DBG("[REC] Previous buffered session (%lu samples) overwritten", (unsigned long)bufCount);
  dataReady      = false;
  bufCount       = 0;
  sessionStartUs = 0;
  recording      = true;
  lastSampleUs   = micros();
  syncLed();
  DBG("[REC] Started (via %s) — capacity %lu samples (%.1f s)",
      source, (unsigned long)maxSamples, maxSamples / (float)SAMPLE_RATE_HZ);
}

static void stopRecording(const char *source) {
  if (!recording) { DBG("[REC] Stop ignored — not recording"); return; }
  recording = false;
  dataReady = (bufCount > 0);
  syncLed();
  DBG("[REC] Stopped (via %s) — %lu samples buffered (%.1f s)",
      source, (unsigned long)bufCount, bufCount / (float)SAMPLE_RATE_HZ);
}

// ── META / DUMP (run from loop() on the main task) ────────────────────────────
static void sendMeta() {
  uint8_t  pkt[8];
  uint32_t startUs = dataReady ? sessionStartUs : 0;
  uint32_t nowUs   = micros();   // captured at send time
  memcpy(pkt,     &startUs, 4);
  memcpy(pkt + 4, &nowUs,   4);
  pTxChar->setValue(pkt, 8);
  pTxChar->notify();
  DBG("[META] session_start_us=%lu device_now_us=%lu (%.2f s ago)",
      (unsigned long)startUs, (unsigned long)nowUs,
      startUs ? (uint32_t)(nowUs - startUs) / 1e6 : 0.0f);
}

// Live diagnostics snapshot — reads the AS5600 fresh and reports device state so the
// phone can show magnet/wiring/buffer health with no serial monitor. See STATUS in the
// header comment for the byte layout. Runs on the main task (I2C), like META/DUMP.
static void sendStatus() {
  uint8_t  magStatus = readMagnetStatus();
  uint8_t  magOk     = readMagnetOk();
  uint8_t  agc       = readAgc();
  uint16_t angle     = readAngle();
  uint8_t  flags     = (recording   ? 0x01 : 0)
                     | (dataReady    ? 0x02 : 0)
                     | (motorRunning ? 0x04 : 0);

  uint8_t pkt[STATUS_PACKET_SIZE];
  pkt[0] = STATUS_MARKER;
  pkt[1] = magStatus;
  pkt[2] = magOk;
  pkt[3] = agc;
  memcpy(pkt + 4,  &angle,      2);   // ESP32 is little-endian — matches sendMeta()
  pkt[6] = flags;
  memcpy(pkt + 7,  &bufCount,   4);
  memcpy(pkt + 11, &maxSamples, 4);
  pTxChar->setValue(pkt, STATUS_PACKET_SIZE);
  pTxChar->notify();
  DBG("[STATUS] mag=0x%02X ok=%d agc=%u angle=%u flags=0x%02X buf=%lu/%lu",
      magStatus, magOk, agc, angle, flags,
      (unsigned long)bufCount, (unsigned long)maxSamples);
}

static void sendEndOfDumpMarker() {
  uint8_t marker = END_OF_DUMP_MARKER;
  pTxChar->setValue(&marker, 1);
  pTxChar->notify();
}

static void dumpBuffer() {
  if (!dataReady || bufCount == 0) {
    DBG("[DUMP] No buffered session — sending end marker only");
    sendEndOfDumpMarker();
    return;
  }
  DBG("[DUMP] Streaming %lu samples...", (unsigned long)bufCount);
  uint32_t sent = 0;
  while (sent < bufCount) {
    if (!deviceConnected) {
      // Abort but retain the buffer so retrieval can be retried
      DBG("[DUMP] Aborted at %lu/%lu — disconnected (buffer retained)",
          (unsigned long)sent, (unsigned long)bufCount);
      syncLed();
      return;
    }
    uint32_t n = bufCount - sent;
    if (n > DUMP_SAMPLES_PER_PACKET) n = DUMP_SAMPLES_PER_PACKET;
    // Packed struct → buffer slice is already wire-format bytes
    pTxChar->setValue((uint8_t *)&sampleBuf[sent], n * sizeof(Sample));
    pTxChar->notify();
    sent += n;
    vTaskDelay(pdMS_TO_TICKS(DUMP_PACKET_DELAY_MS));
  }
  sendEndOfDumpMarker();
  DBG("[DUMP] Complete: %lu samples", (unsigned long)sent);
  bufCount       = 0;
  dataReady      = false;
  sessionStartUs = 0;
  syncLed();
}

// ── Deferred command processor — call from loop() only ───────────────────────
// BLE callbacks set these flags; actual hardware/I2C/notify work happens here
// on the main task, avoiding blocking the BLE FreeRTOS task and I2C bus races.
static void processPending() {
  if (pendingMotorStart)  { pendingMotorStart  = false; motorStart();           }
  if (pendingMotorStop)   { pendingMotorStop   = false; motorStop();            }
  if (pendingRecordStart) { pendingRecordStart = false; startRecording("BLE");  }
  if (pendingRecordStop)  { pendingRecordStop  = false; stopRecording("BLE");   }
  if (pendingMeta)        { pendingMeta        = false; if (deviceConnected) sendMeta();   }
  if (pendingDump)        { pendingDump        = false; if (deviceConnected) dumpBuffer(); }
  if (pendingStatus)      { pendingStatus      = false; if (deviceConnected) sendStatus(); }
}

// ── BLE callbacks ─────────────────────────────────────────────────────────────
class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *) override {
    deviceConnected = true;
    DBG("[BLE] Connected");
    if (!recording && !motorRunning) syncLed();
  }
  void onDisconnect(BLEServer *) override {
    deviceConnected = false;
    pendingMeta = false;
    pendingDump = false;
    pendingStatus = false;
    DBG("[BLE] Disconnected — restarting advertising");
    // Recording is independent of the connection in buffer mode — keep going.
    if (!recording && !motorRunning) syncLed();
    BLEDevice::startAdvertising();
  }
};

class RxCallbacks : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *pChar) override {
    String val = String(pChar->getValue().c_str());
    val.trim();
    DBG("[BLE] CMD received: \"%s\"", val.c_str());

    // Only set flags here — no hardware, no I2C, no delay on the BLE task.
    if      (val == "START"    && !recording)    { pendingRecordStart = true;  DBG("[BLE] CMD queued: START"); }
    else if (val == "STOP"     &&  recording)    { pendingRecordStop  = true;  DBG("[BLE] CMD queued: STOP"); }
    else if (val == "META")                      { pendingMeta        = true;  DBG("[BLE] CMD queued: META"); }
    else if (val == "DUMP")                      { pendingDump        = true;  DBG("[BLE] CMD queued: DUMP"); }
    else if (val == "STATUS")                    { pendingStatus      = true;  DBG("[BLE] CMD queued: STATUS"); }
    else if (val == "REEL_ON"  && !motorRunning) { pendingMotorStart  = true;  DBG("[BLE] CMD queued: REEL_ON"); }
    else if (val == "REEL_OFF" &&  motorRunning) { pendingMotorStop   = true;  DBG("[BLE] CMD queued: REEL_OFF"); }
    else if (val == "START"    &&  recording)    DBG("[BLE] CMD ignored — already recording");
    else if (val == "STOP"     && !recording)    DBG("[BLE] CMD ignored — not recording");
    else if (val == "REEL_ON"  &&  motorRunning) DBG("[BLE] CMD ignored — motor already running");
    else if (val == "REEL_OFF" && !motorRunning) DBG("[BLE] CMD ignored — motor not running");
    else                                         DBG("[BLE] CMD unrecognized: \"%s\"", val.c_str());
  }
};

// ── Button (debounced; short press = record toggle, long press = motor) ──────
// Raw reads feed the debounce timer; actions fire from the debounced state.
// Short press acts on RELEASE (so it can be distinguished from a long press);
// long press fires once when the hold crosses LONG_PRESS_MS.
static void checkButton() {
  bool raw = digitalRead(PIN_BUTTON);
  if (raw != btnLastRaw) {
    DBG("[BTN] Raw state change → %s (starting debounce)", raw == LOW ? "LOW" : "HIGH");
    btnLastRaw    = raw;
    btnDebounceMs = millis();
  }

  if ((millis() - btnDebounceMs) > DEBOUNCE_MS && raw != btnStable) {
    btnStable = raw;
    if (btnStable == LOW) {
      btnPressMs   = millis();
      btnLongFired = false;
      DBG("[BTN] Press confirmed — waiting for release (short=record) or %d ms hold (long=motor)",
          LONG_PRESS_MS);
    } else {
      if (!btnLongFired) {
        DBG("[BTN] Short press — recording is %s", recording ? "ON → stopping" : "OFF → starting");
        if (recording) stopRecording("button");
        else           startRecording("button");
      } else {
        DBG("[BTN] Released after long press");
      }
    }
  }

  // Long press fires while still held
  if (btnStable == LOW && !btnLongFired && (millis() - btnPressMs) >= LONG_PRESS_MS) {
    btnLongFired = true;
    DBG("[BTN] Long press — motor is %s", motorRunning ? "ON → stopping" : "OFF → starting");
    if (motorRunning) motorStop();
    else              motorStart();
  }
}

// ── LED (non-blocking timer patterns) ────────────────────────────────────────
static void updateLED() {
  if (ledState == LED_ERROR && millis() >= errorClearMs) {
    DBG("[LED] Error cleared");
    syncLed();
  }
  uint32_t now = millis();
  switch (ledState) {
    case LED_MOTOR:
      digitalWrite(PIN_LED, (now % 500) < 250 ? HIGH : LOW);   // 2 Hz
      break;
    case LED_ERROR:
      digitalWrite(PIN_LED, (now % 100) < 50  ? HIGH : LOW);   // 10 Hz
      break;
    case LED_RECORDING:
      digitalWrite(PIN_LED, (now % 200) < 100 ? HIGH : LOW);   // 5 Hz
      break;
    case LED_READY: {
      // Slow double-pulse: two 100ms pulses every 2 s
      uint32_t phase = now % 2000;
      digitalWrite(PIN_LED, (phase < 100 || (phase >= 200 && phase < 300)) ? HIGH : LOW);
      break;
    }
    case LED_IDLE:
      digitalWrite(PIN_LED, HIGH);
      break;
    case LED_PAIRING:
      digitalWrite(PIN_LED, (now % 1000) < 500 ? HIGH : LOW);  // 1 Hz
      break;
  }
}

// ── Status heartbeat ──────────────────────────────────────────────────────────
static void printStatus() {
  if (millis() - lastStatusMs < STATUS_INTERVAL_MS) return;
  lastStatusMs = millis();
  DBG("[STATUS] motor=%s rec=%s ready=%s ble=%s led=%s buf=%lu/%lu btn=%d heap=%u",
      motorRunning    ? "ON"        : "OFF",
      recording       ? "ON"        : "OFF",
      dataReady       ? "YES"       : "no",
      deviceConnected ? "CONNECTED" : "DISCONNECTED",
      ledStateName(ledState),
      (unsigned long)bufCount, (unsigned long)maxSamples,
      (int)digitalRead(PIN_BUTTON), ESP.getFreeHeap());
}

// ── Setup ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(200);

  // Motor pins — safe LOW before anything else
  pinMode(PIN_IN1, OUTPUT);  digitalWrite(PIN_IN1, LOW);
  pinMode(PIN_IN2, OUTPUT);  digitalWrite(PIN_IN2, LOW);

  Wire.begin(PIN_SDA, PIN_SCL);
  Wire.setClock(400000);

  pinMode(PIN_LED,    OUTPUT);
  pinMode(PIN_BUTTON, INPUT_PULLUP);

  // Derive unique chip ID from the ESP32's eFuse MAC address.
  uint64_t mac = ESP.getEfuseMac();
  snprintf(chipId, sizeof(chipId), "%02X%02X%02X",
           (uint8_t)(mac >> 40),
           (uint8_t)(mac >> 32),
           (uint8_t)(mac >> 24));

  char bleName[24];
  snprintf(bleName, sizeof(bleName), "SwimLogger-%s", chipId);

  DBG("[SETUP] Boot — firmware %s (buffer-and-dump)", FIRMWARE_VERSION);
  DBG("[SETUP] Motor pins LOW — GPIO%d=0  GPIO%d=0", PIN_IN1, PIN_IN2);
  DBG("[SETUP] I2C init — SDA=GPIO%d  SCL=GPIO%d  400kHz", PIN_SDA, PIN_SCL);
  DBG("[SETUP] Chip ID: %s", chipId);
  DBG("[SETUP] LED=GPIO%d  Button=GPIO%d (INPUT_PULLUP, short=record, long=motor)",
      PIN_LED, PIN_BUTTON);

  // Magnet check — surface wiring problems before BLE starts
  uint8_t magStatus = readMagnetStatus();
  uint8_t magOk     = readMagnetOk();
  DBG("[SETUP] AS5600 magnet status byte=0x%02X  ok=%d%s",
      magStatus, magOk, magOk ? "" : "  ← CHECK WIRING / MAGNET POSITION");

  // BLE
  BLEDevice::init(bleName);
  pServer = BLEDevice::createServer();
  pServer->setCallbacks(new ServerCallbacks());
  DBG("[SETUP] BLE name: \"%s\"", bleName);

  BLEService *pService = pServer->createService(SERVICE_UUID);

  // TX: encoder data → app (notify)
  pTxChar = pService->createCharacteristic(TX_UUID, BLECharacteristic::PROPERTY_NOTIFY);
  pTxChar->addDescriptor(new BLE2902());

  // RX: commands from app (write)
  BLECharacteristic *pRxChar =
      pService->createCharacteristic(RX_UUID, BLECharacteristic::PROPERTY_WRITE);
  pRxChar->setCallbacks(new RxCallbacks());

  // ID: read-only chip identifier for management system
  BLECharacteristic *pIdChar =
      pService->createCharacteristic(ID_UUID, BLECharacteristic::PROPERTY_READ);
  pIdChar->setValue(String(chipId));
  DBG("[SETUP] ID characteristic set: \"%s\"", chipId);

  BLECharacteristic *pFwChar =
      pService->createCharacteristic(FW_UUID, BLECharacteristic::PROPERTY_READ);
  pFwChar->setValue(String(FIRMWARE_VERSION));
  DBG("[SETUP] Firmware version: %s", FIRMWARE_VERSION);

  pService->start();

  BLEAdvertising *pAdv = BLEDevice::getAdvertising();
  pAdv->addServiceUUID(SERVICE_UUID);
  pAdv->setScanResponse(true);
  BLEDevice::startAdvertising();
  DBG("[SETUP] BLE advertising started");

  // Sample buffer — sized at boot from the largest contiguous free block.
  // Total free heap overstates what one malloc can return (heap is split
  // across regions); ask the allocator what actually fits.
  size_t largest = heap_caps_get_largest_free_block(MALLOC_CAP_8BIT);
  DBG("[SETUP] Free heap after BLE init: %u bytes (largest block: %u)",
      ESP.getFreeHeap(), (unsigned)largest);

  size_t avail = (largest > BLE_HEAP_HEADROOM) ? largest - BLE_HEAP_HEADROOM : 0;
  maxSamples = avail / sizeof(Sample);
  if (maxSamples > MAX_SAMPLES_CAP) maxSamples = MAX_SAMPLES_CAP;

  while (maxSamples >= (uint32_t)SAMPLE_RATE_HZ * MIN_BUFFER_SECONDS) {
    sampleBuf = (Sample *)malloc(maxSamples * sizeof(Sample));
    if (sampleBuf != nullptr) break;
    maxSamples /= 2;   // largest-block estimate raced another alloc — back off
  }
  if (sampleBuf == nullptr) {
    DBG("[SETUP] FATAL: cannot fit even %u s of buffer (largest block %u bytes)",
        MIN_BUFFER_SECONDS, (unsigned)largest);
    while (true) {                     // halt with rapid error blink
      digitalWrite(PIN_LED, (millis() % 100) < 50 ? HIGH : LOW);
      delay(10);
    }
  }
  DBG("[SETUP] Sample buffer: %lu samples = %.1f s (%u bytes). Free heap now: %u bytes",
      (unsigned long)maxSamples, maxSamples / (float)SAMPLE_RATE_HZ,
      (unsigned)(maxSamples * sizeof(Sample)), ESP.getFreeHeap());

  DBG("[SETUP] Ready");
}

// ── Loop ──────────────────────────────────────────────────────────────────────
void loop() {
  processPending();   // execute deferred BLE commands on main task
  checkButton();
  checkMotorTimeout();
  printStatus();

  if (recording) {
    uint32_t now = micros();
    if (now - lastSampleUs >= SAMPLE_INTERVAL_US) {
      lastSampleUs += SAMPLE_INTERVAL_US;   // drift-corrected anchor

      if (bufCount >= maxSamples) {
        // Buffer full — stop sampling, retain data (truncated, not lost)
        recording    = false;
        dataReady    = true;
        setLedState(LED_ERROR);
        errorClearMs = millis() + ERROR_DISPLAY_MS;   // error flash, then READY via syncLed
        DBG("[REC] Buffer full — recording stopped at %lu samples (truncated)",
            (unsigned long)bufCount);
      } else {
        Sample s = { now, readAngle(), readMagnetOk() };
        if (bufCount == 0) sessionStartUs = s.ts;
        sampleBuf[bufCount++] = s;

        if (bufCount % 1024 == 0)
          DBG("[REC] %lu samples buffered (~%.1f s)",
              (unsigned long)bufCount, bufCount / (float)SAMPLE_RATE_HZ);
      }
    }
  }

  updateLED();
}