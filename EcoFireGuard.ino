#include <LiquidCrystal_I2C.h>

#define SPRINKLER1 2
#define SPRINKLER2 3
#define SPRINKLER3 4
#define SPRINKLER4 5

#define MOTOR1 6
#define MOTOR2 7

#define LED1 9
#define LED2 10
#define LED3 11
#define LED4 12

LiquidCrystal_I2C lcd1(0x27, 16, 2);
LiquidCrystal_I2C lcd2(0x26, 16, 2);
LiquidCrystal_I2C lcd3(0x25, 16, 2);
LiquidCrystal_I2C lcd4(0x24, 16, 2);

bool sprinklerOn[] = { false, false, false, false };
bool ledOn[] = { false, false, false, false };
bool motorOn[] = { false, false };

struct serialInput {
  String key;
  String value;
};

struct serialInput serInput;

bool ecoMode = false;
char str[16]; // For LCD Output
char buf[16]; // For String.toCharArray()

String* splitString(const String& inputString, const char delimiter, byte& tokenCount) {
  const int maxTokens = 10; // Maximum number of tokens
  String* tokens = new String[maxTokens]; // Array of String objects
  
  int tokenIndex = 0; // Index of current token
  
  int length = inputString.length();
  int startIndex = 0; // Start index of the token
  
  for (int i = 0; i < length; i++) {
    if (inputString.charAt(i) == delimiter) {
      tokens[tokenIndex++] = inputString.substring(startIndex, i);
      startIndex = i + 1;
    }
  }
  
  // Add the last token
  if (startIndex < length) {
    tokens[tokenIndex++] = inputString.substring(startIndex, length);
  }
  
  tokenCount = tokenIndex; // Update the tokenCount variable
  
  return tokens;
}

void setup() { 
  Serial.begin(115200);

  pinMode(SPRINKLER1, OUTPUT);
  pinMode(SPRINKLER2, OUTPUT);
  pinMode(SPRINKLER3, OUTPUT);
  pinMode(SPRINKLER4, OUTPUT);

  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);
  pinMode(LED3, OUTPUT);
  pinMode(LED4, OUTPUT);

  pinMode(MOTOR1, OUTPUT);
  pinMode(MOTOR2, OUTPUT);

  // 화면 초기화
  lcd1.init();
  lcd2.init();
  lcd3.init();
  lcd4.init();

  // 화면 LED ON
  lcd1.backlight();
  lcd2.backlight();
  lcd3.backlight();
  lcd4.backlight();

  lcd1.setCursor(0, 0);
  lcd2.setCursor(0, 0);
  lcd3.setCursor(0, 0);
  lcd4.setCursor(0, 0);

  lcd1.print("Floor set 1F");
  lcd2.print("Floor set 2F");
  lcd3.print("Floor set 3F");
  lcd4.print("Floor set 4F");

  lcd1.setCursor(0, 1);
  lcd2.setCursor(0, 1);
  lcd3.setCursor(0, 1);
  lcd4.setCursor(0, 1);
  
  lcd1.print("Ready");
  lcd2.print("Ready");
  lcd3.print("Ready");
  lcd4.print("Ready");
}

void loop() {
  //////// SPRINKLER ////////
  if (sprinklerOn[0]) digitalWrite(SPRINKLER1, HIGH);
  else digitalWrite(SPRINKLER1, LOW);

  if (sprinklerOn[1]) digitalWrite(SPRINKLER2, HIGH);
  else digitalWrite(SPRINKLER2, LOW);

  if (sprinklerOn[2]) digitalWrite(SPRINKLER3, HIGH);
  else digitalWrite(SPRINKLER3, LOW);

  if (sprinklerOn[3]) digitalWrite(SPRINKLER4, HIGH);
  else digitalWrite(SPRINKLER4, LOW);

  //////// LED ////////
  if (ledOn[0] && !ecoMode) digitalWrite(LED1, HIGH);
  else digitalWrite(LED1, LOW);

  if (ledOn[1] && !ecoMode) digitalWrite(LED2, HIGH);
  else digitalWrite(LED2, LOW);

  if (ledOn[2] && !ecoMode) digitalWrite(LED3, HIGH);
  else digitalWrite(LED3, LOW);

  if (ledOn[4] && !ecoMode) digitalWrite(LED4, HIGH);
  else digitalWrite(LED4, LOW);

  //////// DC MOTOR ////////
  if (motorOn[0] && !ecoMode) digitalWrite(MOTOR1, HIGH);
  else digitalWrite(MOTOR1, LOW);

  if (motorOn[1] && !ecoMode) digitalWrite(MOTOR2, HIGH);
  else digitalWrite(MOTOR2, LOW);

  if (Serial.available()) {
    serInput.key = Serial.readStringUntil(':');
    serInput.value = Serial.readStringUntil('\n');

    lcd1.setCursor(0, 0);
    lcd2.setCursor(0, 0);
    lcd3.setCursor(0, 0);
    lcd4.setCursor(0, 0);

    if (serInput.key == "FireAt") { // "FireAt:3"
      lcd1.clear();
      lcd2.clear();
      lcd3.clear();
      lcd4.clear();

      if (serInput.value != "0") { // -1은 불이 감지 안 됐을 때
        Serial.println("Detected Fire");
        byte fireArrLength, fireFloors[4];
        String *fireArr = splitString(serInput.value, ',', fireArrLength);
        Serial.println("text split done");
        for(int i=0;i<fireArrLength;i++) fireFloors[i] = fireArr[i].toInt();
        bool fireAboveBelow[4][2] = {
          {false, false},
          {false, false},
          {false, false},
          {false, false}
        };
        Serial.println(serInput.value);
        for (int i=0;i<fireArrLength;i++) Serial.println(fireArr[i]);

        serInput.value.toCharArray(buf, 16);
        sprintf(str, "Fire on %sF", buf);
        lcd1.print(str);
        lcd2.print(str);
        lcd3.print(str);
        lcd4.print(str);
        Serial.print("LCD: ");
        Serial.println(str);

        lcd1.setCursor(0, 1);
        lcd2.setCursor(0, 1);
        lcd3.setCursor(0, 1);
        lcd4.setCursor(0, 1);

        for (int i=0;i<4;i++) {
          for (int floor : fireFloors) {
            if (floor > i+1) fireAboveBelow[i][0] = true; // Above
            if (floor < i+1) fireAboveBelow[i][1] = true; // Below
          }
        }

        for (int i=0;i<4;i++) sprinklerOn[i] = false;
        for (int floor : fireFloors) sprinklerOn[floor-1] = true;

        Serial.println(sprinklerOn[0]);
        Serial.println(sprinklerOn[1]);
        Serial.println(sprinklerOn[2]);
        Serial.println(sprinklerOn[3]);

        if (fireAboveBelow[0][0]) lcd1.print("Evac Downstairs");
        else if (fireAboveBelow[0][1]) lcd1.print("Evac Upstairs");
        else lcd1.print("Wait for instr");

        if (fireAboveBelow[1][0]) lcd2.print("Evac Downstairs");
        else if (fireAboveBelow[1][1]) lcd2.print("Evac Upstairs");
        else lcd1.print("Wait for instr");

        if (fireAboveBelow[2][0]) lcd3.print("Evac Downstairs");
        else if (fireAboveBelow[2][1]) lcd3.print("Evac Upstairs");
        else lcd1.print("Wait for instr");

        if (fireAboveBelow[3][0]) lcd4.print("Evac Downstairs");
        else if (fireAboveBelow[3][1]) lcd4.print("Evac Upstairs");
        else lcd1.print("Wait for instr");
      }
    } else if (serInput.key == "EcoMode") { // "EcoMode:1"
      ecoMode = serInput.value == "1";
    } else if (serInput.key == "CtrlIoT") { // "CtrlIoT:M1"
      switch (serInput.value[0]) {
        case '0':
        case '1':
        case '2':
        case '3':
          ledOn[serInput.value[0] - '0'] = serInput.value[1] == '1';
          break;
        case 'X':
          motorOn[0] = serInput.value[1] == '1';
          break;
        case 'Y':
          motorOn[1] = serInput.value[1] == '1';
      }
    }
  }
}