#include <LiquidCrystal_I2C.h>

#define SPRINKLER1 2
#define SPRINKLER2 3
#define SPRINKLER3 4
#define SPRINKLER4 5

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

struct serialInput {
  char key[10];
  char value[10];
};

struct serialInput serInput;

bool ecoMode = false;
char str[16]; // For LCD Output
char buf[8]; // For String.toCharArray()

void setup() { 
  Serial.begin(9600);

  pinMode(SPRINKLER1, OUTPUT);
  pinMode(SPRINKLER2, OUTPUT);
  pinMode(SPRINKLER3, OUTPUT);
  pinMode(SPRINKLER4, OUTPUT);

  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);
  pinMode(LED3, OUTPUT);
  pinMode(LED4, OUTPUT);

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
  if (sprinklerOn[0] && millis() % 500 >= 250) digitalWrite(SPRINKLER1, HIGH);
  else digitalWrite(SPRINKLER1, LOW);

  if (sprinklerOn[1] && millis() % 500 >= 250) digitalWrite(SPRINKLER2, HIGH);
  else digitalWrite(SPRINKLER2, LOW);

  if (sprinklerOn[2] && millis() % 500 >= 250) digitalWrite(SPRINKLER3, HIGH);
  else digitalWrite(SPRINKLER3, LOW);

  if (sprinklerOn[3] && millis() % 500 >= 250) digitalWrite(SPRINKLER4, HIGH);
  else digitalWrite(SPRINKLER4, LOW);

  //////// LED ////////
  if (ledOn[0] && !ecoMode) digitalWrite(LED1, HIGH);
  else digitalWrite(LED1, LOW);

  if (ledOn[1] && !ecoMode) digitalWrite(LED2, HIGH);
  else digitalWrite(LED2, LOW);

  if (ledOn[2] && !ecoMode) digitalWrite(LED3, HIGH);
  else digitalWrite(LED3, LOW);

  if (ledOn[3] && !ecoMode) digitalWrite(LED4, HIGH);
  else digitalWrite(LED4, LOW);

  /*
  if (!(millis() % 1000)) {
    Serial.print("SC1:");
    Serial.println(sprinklerOn[0] && millis() / 500 >= 250);
    Serial.print("SC2:");
    Serial.println(sprinklerOn[1] && millis() / 500 >= 250);
    Serial.print("SC3:");
    Serial.println(sprinklerOn[2] && millis() / 500 >= 250);
    Serial.print("SC4:");
    Serial.println(sprinklerOn[3] && millis() / 500 >= 250);

    Serial.print("LED1:");
    Serial.println(ledOn[0] && !ecoMode);
    Serial.print("LED2:");
    Serial.println(ledOn[1] && !ecoMode);
    Serial.print("LED3:");
    Serial.println(ledOn[2] && !ecoMode);
    Serial.print("LED4:");
    Serial.println(ledOn[3] && !ecoMode);
  } */

  while (Serial.available()) {
    Serial.readStringUntil(':').toCharArray(serInput.key, 10);
    Serial.readStringUntil('\n').toCharArray(serInput.value, 10);
    
    Serial.print("key:");
    Serial.println(serInput.key);
    Serial.print("value:");
    Serial.println(serInput.value);

    lcd1.setCursor(0, 0);
    lcd2.setCursor(0, 0);
    lcd3.setCursor(0, 0);
    lcd4.setCursor(0, 0);

    if (strcmp(serInput.key, "FireAt") == 0) { // "FireAt:3"
      lcd1.clear();
      lcd2.clear();
      lcd3.clear();
      lcd4.clear();

      for (int i=0;i<4;i++) sprinklerOn[i] = false;

      if (strcmp(serInput.value, "0") != 0) { // 0은 불이 감지 안 됐을 때
        Serial.println("Detected Fire");
        bool fireFloors[4] = { false, false, false, false };
        for(char value : serInput.value) {
          if (value == NULL) break;
          if (value >= '0' && value <= '9') {
            fireFloors[value - '1'] = true;
            sprinklerOn[value - '1'] = true;
            Serial.println(value);
          }
        }

        sprintf(str, "Fire on %sF", serInput.value);
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

        if (fireFloors[0] || fireFloors[1] || fireFloors[2] || fireFloors[3]) lcd1.print("Evac Downstairs");

        if (fireFloors[0] && (fireFloors[2] || fireFloors[3])) lcd2.print("Wait for instr");
        else if (fireFloors[1] || fireFloors[2] || fireFloors[3]) lcd2.print("Evac Downstairs");
        else if (fireFloors[0]) lcd2.print("Evac Upstairs");

        if ((fireFloors[0] || fireFloors[1]) && fireFloors[3]) lcd3.print("Wait for instr");
        else if (fireFloors[3]) lcd3.print("Evac Downstairs");
        else if (fireFloors [0] || fireFloors[1] || fireFloors[2]) lcd3.print("Evac Upstairs");

        if (fireFloors[0] || fireFloors[1] || fireFloors[2] || fireFloors[3]) lcd4.print("Evac Upstairs");
      }
    } else if (strcmp(serInput.key, "EcoMode") == 0) { // "EcoMode:1"
      ecoMode = serInput.value[0] == '1';
    } else if (strcmp(serInput.key, "CtrlIoT") == 0) { // "CtrlIoT:1011"
      for(int i=0;i<4;i++) ledOn[i] = serInput.value[i] == '1'; 
    }
  }
}