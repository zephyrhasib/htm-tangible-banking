#include <SPI.h>
#include <MFRC522.h>
#include <DFRobotDFPlayerMini.h>
#include <Adafruit_NeoPixel.h>

#define RST_PIN 22
#define SS_PIN  5
#define RING_PIN 4
#define NUMPIXELS 12
#define CONFIRM_BUTTON_PIN 15
#define BALANCE_BUTTON_PIN 13
#define HOLD_THRESHOLD_MS 2000
#define DEBOUNCE_MS 40

MFRC522 mfrc522(SS_PIN, RST_PIN);
HardwareSerial mySerial(2);
DFRobotDFPlayerMini myDFPlayer;
Adafruit_NeoPixel ring(NUMPIXELS, RING_PIN, NEO_GRB + NEO_KHZ800);

bool deviceUnlocked = false;
unsigned long lastTapTime = 0;
const unsigned long TAP_COOLDOWN_MS = 1500;

unsigned long lastActivityTime = 0;
const unsigned long IDLE_TIMEOUT_MS = 60000;
const unsigned long WARNING_START_MS = 55000;
bool warningActive = false;
int lastCountdownPrinted = -1;

int accountBalance = 10000;
const int MAX_TRANSFER = 10000;

String keyfobUID = "50 2F F3 53";

String recipientUIDs[5] = {
  "C0 71 5A 5C","B1 4C 46 0A","B0 56 3F 5C","B0 EB 9C 5C","C0 BB AF 5C"
};
String recipientNames[5] = {"Shanto", "Tonmoy", "Kabir", "Puja", "Hasib"};
int recipientAudioTrack[5] = {6, 7, 8, 9, 10};

String denominationUIDs[4] = {
  "B0 66 57 5C","B0 80 96 5C","B0 9B 36 5C","C1 5B 59 0A"
};
int denominationValues[4] = {1000, 500, 200, 100};

String cancelCardUID = "C0 5A 26 5C";

String selectedRecipient = "";
int transferAmount = 0;

int amountHistory[20];
int historyCount = 0;

bool amountInstructionPlayed = false;
bool holdInstructionPlayed = false;

unsigned long pressStart = 0;
bool wasPressed = false;
bool awaitingRelease = false;
bool lastRawStateConfirm = false;
unsigned long lastDebounceConfirm = 0;
bool stableStateConfirm = false;
int lastLitCountSent = -1;

bool lastRawStateBalance = false;
unsigned long lastDebounceBalance = 0;
bool stableStateBalance = false;
bool balanceWasPressed = false;

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();

  delay(1500);
  mySerial.begin(9600, SERIAL_8N1, 16, 17);

  int dfPlayerAttempts = 0;
  while (!myDFPlayer.begin(mySerial) && dfPlayerAttempts < 5) {
    Serial.println("DFPlayer not detected, retrying...");
    dfPlayerAttempts++;
    delay(1000);
  }
  if (dfPlayerAttempts >= 5) {
    Serial.println("DFPlayer failed after retries!");
    while (true) delay(100);
  }
  myDFPlayer.volume(28);

  pinMode(CONFIRM_BUTTON_PIN, INPUT_PULLUP);
  pinMode(BALANCE_BUTTON_PIN, INPUT_PULLUP);

  ring.begin();
  ring.setBrightness(30);
  ring.clear();
  ring.show();

  Serial.println("Device ready. Waiting for keyfob.");
  Serial.println("EVT:type=boot;balance=" + String(accountBalance));
}

void loop() {
  if (deviceUnlocked) {
    unsigned long idleElapsed = millis() - lastActivityTime;
    if (idleElapsed >= IDLE_TIMEOUT_MS) {
      Serial.println("Idle timeout");
      warningActive = false;
      lastCountdownPrinted = -1;
      Serial.println("EVT:type=idle_warning_clear");
      lockDevice("idle");
    } else if (idleElapsed >= WARNING_START_MS) {
      warningActive = true;
      int secondsLeft = (IDLE_TIMEOUT_MS - idleElapsed) / 1000 + 1;
      if (secondsLeft != lastCountdownPrinted) {
        Serial.print("Idle warning - locking in ");
        Serial.print(secondsLeft);
        Serial.println("s");
        Serial.println("EVT:type=idle_warning;seconds_left=" + String(secondsLeft));
        lastCountdownPrinted = secondsLeft;
      }
      rapidFlashTick();
    } else {
      if (warningActive) {
        ring.clear();
        ring.show();
        Serial.println("EVT:type=idle_warning_clear");
      }
      warningActive = false;
      lastCountdownPrinted = -1;
    }
  }

  handleRFID();
  if (deviceUnlocked) {
    handleConfirmButton();
    handleBalanceButton();
  }
}

void rapidFlashTick() {
  unsigned long phase = millis() % 400;
  uint32_t color = (phase < 200) ? ring.Color(255,0,0) : 0;
  for (int i = 0; i < NUMPIXELS; i++) ring.setPixelColor(i, color);
  ring.show();
}

void feedback(bool success, int track, int holdMs) {
  uint32_t color = success ? ring.Color(0,255,0) : ring.Color(255,0,0);
  for (int i = 0; i < NUMPIXELS; i++) ring.setPixelColor(i, color);
  ring.show();
  myDFPlayer.play(track);
  delay(holdMs);
  ring.clear();
  ring.show();
}

void resetTransaction() {
  selectedRecipient = "";
  transferAmount = 0;
  historyCount = 0;
}

void announceBalance() {
  myDFPlayer.play(31);
  delay(1500);
  announceTotal(accountBalance);
}

void handleRFID() {
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) return;

  if (millis() - lastTapTime < TAP_COOLDOWN_MS) {
    mfrc522.PICC_HaltA();
    mfrc522.PCD_StopCrypto1();
    return;
  }
  lastTapTime = millis();
  lastActivityTime = millis();

  String tappedUID = getUIDString();

  if (!deviceUnlocked) {
    if (tappedUID == keyfobUID) {
      deviceUnlocked = true;
      lastActivityTime = millis();
      Serial.println("Keyfob recognized - Welcome");
      Serial.println("EVT:type=unlocked;balance=" + String(accountBalance));
      feedback(true, 3, 2000);
    } else {
      Serial.println("Locked - tap keyfob first");
      Serial.println("EVT:type=locked_attempt");
      feedback(false, 2, 2200);
    }
  } else {
    if (tappedUID == keyfobUID) {
      lockDevice("keyfob");

    } else if (tappedUID == cancelCardUID) {
      if (historyCount > 0) {
        int removed = amountHistory[historyCount - 1];
        historyCount--;
        transferAmount -= removed;
        Serial.print("Undo - removed ");
        Serial.print(removed);
        Serial.print(". New total: ");
        Serial.println(transferAmount);
        Serial.println("EVT:type=amount_updated;amount=" + String(transferAmount) + ";last_token=-" + String(removed));
        feedback(true, 39, 900);

        if (transferAmount > 0) {
          announceTotal(transferAmount);
        } else {
          Serial.println("Amount back to zero - transaction cancelled");
          Serial.println("EVT:type=transaction_cancelled");
          myDFPlayer.play(35);
          delay(1800);
        }
      } else {
        Serial.println("Nothing to undo");
        Serial.println("EVT:type=undo_empty");
        feedback(false, 40, 900);
      }

    } else {
      int recipientIndex = findRecipientIndex(tappedUID);
      int denomIndex = findDenominationIndex(tappedUID);

      if (recipientIndex != -1) {
        selectedRecipient = recipientNames[recipientIndex];
        transferAmount = 0;
        historyCount = 0;
        Serial.print("Recipient selected: ");
        Serial.println(selectedRecipient);
        Serial.println("EVT:type=recipient_selected;name=" + selectedRecipient);
        feedback(true, recipientAudioTrack[recipientIndex], 3500);

        if (!amountInstructionPlayed) {
          myDFPlayer.play(4);
          delay(3000);
          amountInstructionPlayed = true;
        }

      } else if (denomIndex != -1) {
        if (selectedRecipient == "") {
          Serial.println("BLOCKED - select recipient first");
          Serial.println("EVT:type=blocked_no_recipient");
          feedback(false, 40, 1200);
        } else {
          bool wasAmountZero = (transferAmount == 0);
          int proposedAmount = transferAmount + denominationValues[denomIndex];

          if (proposedAmount > MAX_TRANSFER || proposedAmount > accountBalance) {
            Serial.println("REJECTED - exceeds limit");
            Serial.println("EVT:type=rejected_limit");
            feedback(false, 33, 1800);
          } else {
            transferAmount = proposedAmount;
            if (historyCount < 20) {
              amountHistory[historyCount] = denominationValues[denomIndex];
              historyCount++;
            }
            Serial.print("Running total: ");
            Serial.println(transferAmount);
            Serial.println("EVT:type=amount_updated;amount=" + String(transferAmount) + ";last_token=" + String(denominationValues[denomIndex]));
            flashRing(true);
            announceTotal(transferAmount);

            if (wasAmountZero && transferAmount > 0 && !holdInstructionPlayed) {
              myDFPlayer.play(36);
              delay(2500);
              holdInstructionPlayed = true;
            }
          }
        }
      } else {
        Serial.println("Unknown card");
        Serial.println("EVT:type=unknown_card");
        feedback(false, 32, 1800);
      }
    }
  }

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
}

void handleConfirmButton() {
  bool rawState = (digitalRead(CONFIRM_BUTTON_PIN) == LOW);
  if (rawState != lastRawStateConfirm) lastDebounceConfirm = millis();
  if ((millis() - lastDebounceConfirm) > DEBOUNCE_MS) stableStateConfirm = rawState;
  lastRawStateConfirm = rawState;
  bool isPressed = stableStateConfirm;

  if (awaitingRelease) {
    if (!isPressed) awaitingRelease = false;
    wasPressed = isPressed;
    return;
  }

  bool readyToConfirm = (selectedRecipient != "" && transferAmount > 0);

  if (isPressed) {
    if (!readyToConfirm) {
      if (!wasPressed) {
        Serial.println("Confirm pressed too early - not ready");
        Serial.println("EVT:type=confirm_not_ready");
        feedback(false, 40, 1200);
      }
      wasPressed = isPressed;
      return;
    }

    lastActivityTime = millis();
    if (!wasPressed) {
      pressStart = millis();
      lastLitCountSent = -1;
    }

    unsigned long held = millis() - pressStart;
    int litCount = map(held, 0, HOLD_THRESHOLD_MS, 0, NUMPIXELS);
    if (litCount > NUMPIXELS) litCount = NUMPIXELS;

    if (litCount != lastLitCountSent) {
      int percent = (litCount * 100) / NUMPIXELS;
      Serial.println("EVT:type=confirm_progress;percent=" + String(percent));
      lastLitCountSent = litCount;
    }

    for (int i = 0; i < NUMPIXELS; i++) {
      ring.setPixelColor(i, i < litCount ? ring.Color(0,255,0) : 0);
    }
    ring.show();

    if (held >= HOLD_THRESHOLD_MS) {
      completeTransfer();
      awaitingRelease = true;
    }
  } else {
    if (wasPressed && readyToConfirm) {
      Serial.println("Released early - reminding to hold for confirm");
      Serial.println("EVT:type=confirm_released_early");
      ring.clear();
      ring.show();
      feedback(false, 36, 2500);
    }
  }
  wasPressed = isPressed;
}

void handleBalanceButton() {
  bool rawState = (digitalRead(BALANCE_BUTTON_PIN) == LOW);
  if (rawState != lastRawStateBalance) lastDebounceBalance = millis();
  if ((millis() - lastDebounceBalance) > DEBOUNCE_MS) stableStateBalance = rawState;
  lastRawStateBalance = rawState;
  bool isPressed = stableStateBalance;

  if (isPressed && !balanceWasPressed) {
    lastActivityTime = millis();
    bool transactionInProgress = (selectedRecipient != "" || transferAmount > 0);

    if (transactionInProgress) {
      Serial.println("Transaction cancelled - restarting");
      resetTransaction();
      Serial.println("EVT:type=transaction_cancelled");
      feedback(false, 35, 1800);
    } else {
      Serial.print("Balance check: ");
      Serial.println(accountBalance);
      Serial.println("EVT:type=balance_checked;balance=" + String(accountBalance));
      announceBalance();
    }
  }
  balanceWasPressed = isPressed;
}

void completeTransfer() {
  accountBalance -= transferAmount;
  Serial.print("SUCCESS - sent ");
  Serial.print(transferAmount);
  Serial.print(" to ");
  Serial.println(selectedRecipient);
  Serial.println("EVT:type=transfer_success;recipient=" + selectedRecipient + ";amount=" + String(transferAmount) + ";balance=" + String(accountBalance));

  feedback(true, 34, 3200);
  announceBalance();

  selectedRecipient = "";
  transferAmount = 0;
  historyCount = 0;
  lastActivityTime = millis();
}

void lockDevice(String reason) {
  deviceUnlocked = false;
  selectedRecipient = "";
  transferAmount = 0;
  historyCount = 0;

  amountInstructionPlayed = false;
  holdInstructionPlayed = false;

  Serial.println("LOCKED");
  Serial.println("EVT:type=locked;reason=" + reason);
  ring.clear();
  ring.show();
  myDFPlayer.play(38);
  delay(2500);
}

void flashRing(bool success) {
  uint32_t color = success ? ring.Color(0,255,0) : ring.Color(255,0,0);
  for (int i = 0; i < NUMPIXELS; i++) ring.setPixelColor(i, color);
  ring.show();
  delay(250);
  ring.clear();
  ring.show();
}

void flashRingBlink(bool success, int times) {
  uint32_t color = success ? ring.Color(0,255,0) : ring.Color(255,0,0);
  for (int b = 0; b < times; b++) {
    for (int i = 0; i < NUMPIXELS; i++) ring.setPixelColor(i, color);
    ring.show();
    delay(150);
    ring.clear();
    ring.show();
    delay(150);
  }
}

void announceTotal(int amount) {
  int thousands = amount / 1000;
  int hundreds = (amount % 1000) / 100;
  if (thousands > 0) { myDFPlayer.play(19 + thousands); delay(1300); }
  if (hundreds > 0) { myDFPlayer.play(10 + hundreds); delay(1200); }
  myDFPlayer.play(30);
  delay(1000);
}

String getUIDString() {
  String result = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) result += "0";
    result += String(mfrc522.uid.uidByte[i], HEX);
    if (i < mfrc522.uid.size - 1) result += " ";
  }
  result.toUpperCase();
  return result;
}

int findRecipientIndex(String uid) {
  for (int i = 0; i < 5; i++) if (recipientUIDs[i] == uid) return i;
  return -1;
}

int findDenominationIndex(String uid) {
  for (int i = 0; i < 4; i++) if (denominationUIDs[i] == uid) return i;
  return -1;
}