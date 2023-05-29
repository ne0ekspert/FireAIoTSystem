#include <LiquidCrystal_I2C.h>

#define SPRINKLER1 2
#define SPRINKLER2 3

#define LED1 9
#define LED2 10
#define MOTOR 11

LiquidCrystal_I2C lcd1(0x26, 16, 2); // 납땜된 LCD
LiquidCrystal_I2C lcd2(0x27, 16, 2); // 납땜없는 LCD

struct floorSettings {
  byte lcd1=1;
  byte lcd2=2;
};

bool led1On = false;
bool led2On = false;
bool motorOn = false;

struct serialInput {
  String key;
  String value;
};

struct floorSettings floorInfo;
struct serialInput serInput;

String stylednum(int num) {
  switch (num) {
    case 1:
      return "1st";
    case 2:
      return "2nd";
    case 3:
      return "3rd";
    case 4:
      return "4th";
    default:
      return "<UNK>";
  }
}

bool ecoMode = false;
char str[16];

void countdown(LiquidCrystal_I2C lcd) {

  lcd.setCursor(0, 1);

  for(int i=3;i>0;i--) {
    sprintf(str, "%d... ", i);
    lcd.print(str);

    delay(1000);
  }

  lcd.clear();
}

void setup() { 
  Serial.begin(115200);

  pinMode(MOTOR, OUTPUT);
  pinMode(LED1, OUTPUT);
  pinMode(LED2, OUTPUT);

  // 화면 1, 2 초기화
  lcd1.init();
  lcd2.init();

  // 화면 1, 2 LED ON
  lcd1.backlight();
  lcd2.backlight();

  lcd1.setCursor(0, 0);
  lcd2.setCursor(0, 0);

  sprintf(str, "Floor set to %d", floorInfo.lcd1);
  lcd1.print(str);
  sprintf(str, "Floor set to %d", floorInfo.lcd2);
  lcd2.print(str);

  lcd1.setCursor(0, 1);
  lcd2.setCursor(0, 1);
  
  lcd1.print("Ready");
  lcd2.print("Ready");
}

void loop() {
  if (led1On && !ecoMode) digitalWrite(LED1, HIGH);
  else digitalWrite(LED1, LOW);

  if (led2On && !ecoMode) digitalWrite(LED2, HIGH);
  else digitalWrite(LED2, LOW);

  if (motorOn && !ecoMode) digitalWrite(MOTOR, HIGH);
  else digitalWrite(MOTOR, LOW);

  if (Serial.available()) {
    serInput.key = Serial.readStringUntil(':');
    serInput.value = Serial.readStringUntil('\n');

    lcd1.setCursor(0, 0);
    lcd2.setCursor(0, 0);

    if (serInput.key == "FireAt") { // "FireAt:3"
      lcd1.clear();
      lcd2.clear();

      if (serInput.value != "-1") { // -1은 불이 감지 안 됐을 때
        sprintf(str, "Fire on %dF", serInput.value.toInt());
        lcd1.print(str);
        lcd2.print(str);

        lcd1.setCursor(0, 1);
        lcd2.setCursor(0, 1);

        if (serInput.value.toInt() >= floorInfo.lcd1) lcd1.print("Evac Downstairs");
        else lcd1.print("Evac Upstairs");

        if (serInput.value.toInt() >= floorInfo.lcd2) lcd2.print("Evac Downstairs");
        else lcd2.print("Evac Upstairs");
      }
    } else if (serInput.key == "EcoMode") { // "EcoMode:1"
      ecoMode = serInput.value == "1";
    } else if (serInput.key == "CtrlIoT") { // "CtrlIoT:M1"
      switch (serInput.value[0]) {
        case '0':
          led1On = serInput.value[1] == '1';
          break;
        case '1':
          led2On = serInput.value[1] == '1';
          break;
        case 'M':
          motorOn = serInput.value[1] == '1';
          break;
      }
    } else if (serInput.key == "SetFloor") { // LCD 층 설정 "SetFloor:00"
      if (serInput.value[0] == '0') {
        lcd1.clear();

        floorInfo.lcd1 = atoi(&serInput.value[1]);
        sprintf(str, "Floor set to %d", floorInfo.lcd1);
        lcd1.print(str);

        countdown(lcd1);
      } else if (serInput.value[0] == '1') {
        lcd2.clear();

        floorInfo.lcd2 = atoi(&serInput.value[1]);
        sprintf(str, "Floor set to %d", floorInfo.lcd2);
        lcd2.print(str);

        countdown(lcd2);
      }
    }
  }
}