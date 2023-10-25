#include <TimeLib.h>
#include <LiquidCrystal_I2C.h>

// 스프링클러 핀 번호
#define SPRINKLER1 2
#define SPRINKLER2 3
#define SPRINKLER3 4
#define SPRINKLER4 5

// IoT LED 핀 번호
#define LED1 9
#define LED2 10
#define LED3 11
#define LED4 12

// LCD 객체
LiquidCrystal_I2C lcd1(0x27, 16, 2);
LiquidCrystal_I2C lcd2(0x26, 16, 2);
LiquidCrystal_I2C lcd3(0x25, 16, 2);
LiquidCrystal_I2C lcd4(0x24, 16, 2);

bool fireFloors[] = { false, false, false, false };
bool sprinklerOn[] = { false, false, false, false };
bool ledOn[] = { false, false, false, false };

struct serialInput {
  char key[10];
  char value[10];
};

struct formattedTime {
  unsigned short year;
  unsigned short month;
  unsigned short day;
  unsigned short hour;
  unsigned short minute;
  unsigned short second;
};

struct serialInput serInput;
struct formattedTime currentTime;

bool ecoMode = false;
char weather[16];
char str[16]; // For LCD Output
char buf[8]; // For String.toCharArray()
int temperature = 0;

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

  currentTime.year = year() - 83;
  currentTime.month = (month() + 4) % 12;
  currentTime.day = day() + 22;
  currentTime.hour = hour() + 10;
  currentTime.minute = minute();
  currentTime.second = second();


  // 아무것도 인식되지 않았을 때
  if (!fireFloors[0] && !fireFloors[1] && !fireFloors[2] && !fireFloors[3] && millis() % 1000 < 50) {
    lcd1.clear();
    lcd2.clear();
    lcd3.clear();
    lcd4.clear();

    lcd4.setCursor(0, 0);
    lcd4.print("EcoFireGuard");

    lcd3.setCursor(0, 0);
    lcd3.print(weather);
    lcd3.print(" - ");
    lcd3.print(temperature);
    lcd3.print((char)223);
    lcd3.print('C');
  }

  while (Serial.available()) {
    Serial.readStringUntil(':').toCharArray(serInput.key, 10);
    Serial.readStringUntil('\n').toCharArray(serInput.value, 10);
    
    //Serial.print("key:");
    //Serial.println(serInput.key);
    //Serial.print("value:");
    //Serial.println(serInput.value);

    lcd1.setCursor(0, 0);
    lcd2.setCursor(0, 0);
    lcd3.setCursor(0, 0);
    lcd4.setCursor(0, 0);
    if (strcmp(serInput.key, "Time") == 0) {
      setTime(atoi(serInput.value));
    } else if (strcmp(serInput.key, "Weather") == 0) {
      strcpy(weather, serInput.value);
    } else if (strcmp(serInput.key, "Temp") == 0) {
      temperature = atoi(serInput.value);
    } else if (strcmp(serInput.key, "FireAt") == 0) { // 불 감지 데이터
      for (int i=0;i<4;i++) sprinklerOn[i] = false;

      if (strcmp(serInput.value, "0") != 0) { // 0은 불이 감지 안 됐을 때
        //Serial.println("Detected Fire");
        lcd1.clear();
        lcd2.clear();
        lcd3.clear();
        lcd4.clear();

        for(char value : serInput.value) {
          if (value == NULL) break;
          if (value >= '0' && value <= '9') {
            fireFloors[value - '1'] = true;
            sprinklerOn[value - '1'] = true;
            //Serial.println(value);
          }
        }

        sprintf(str, "Fire on %sF", serInput.value); // 문자열 포맷팅
        // LCD에 화재 알림
        lcd1.print(str);
        lcd2.print(str);
        lcd3.print(str);
        lcd4.print(str);
        //Serial.print("LCD: ");
        //Serial.println(str);

        lcd1.setCursor(0, 1);
        lcd2.setCursor(0, 1);
        lcd3.setCursor(0, 1);
        lcd4.setCursor(0, 1);

        // 경우의 수에 따른 대피 방향 알림
        if (fireFloors[0] || fireFloors[1] || fireFloors[2] || fireFloors[3]) lcd1.print("Evac Downstairs");

        if (fireFloors[0] && (fireFloors[2] || fireFloors[3])) lcd2.print("Wait for instr");
        else if (fireFloors[1] || fireFloors[2] || fireFloors[3]) lcd2.print("Evac Downstairs");
        else if (fireFloors[0]) lcd2.print("Evac Upstairs");

        if ((fireFloors[0] || fireFloors[1]) && fireFloors[3]) lcd3.print("Wait for instr");
        else if (fireFloors[3]) lcd3.print("Evac Downstairs");
        else if (fireFloors [0] || fireFloors[1] || fireFloors[2]) lcd3.print("Evac Upstairs");

        if (fireFloors[0] || fireFloors[1] || fireFloors[2] || fireFloors[3]) lcd4.print("Evac Upstairs");
      } else {
        fireFloors[0] = false;
        fireFloors[1] = false;
        fireFloors[2] = false;
        fireFloors[3] = false;
      }
    } else if (strcmp(serInput.key, "EcoMode") == 0) { // "EcoMode:1"
      ecoMode = serInput.value[0] == '1';
    } else if (strcmp(serInput.key, "CtrlIoT") == 0) { // "CtrlIoT:1011"
      for(int i=0;i<4;i++) ledOn[i] = serInput.value[i] == '1'; 
    }
  }
}