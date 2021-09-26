#include <driver/adc.h>
#include <driver/timer.h>
#include <esp_adc_cal.h>
#include <Sparkfun_DRV2605L.h>
#include <Wire.h>
#include <WiFiManager.h>          //https://github.com/tzapu/WiFiManager WiFi Configuration Magic
//#include <DNSServer.h>
#include <WebServer.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <base64.h>
#include "telnet.h"
#include "pack12bit.h"
#include "double_buffer.h"

//#include <lwip/opt.h>
//#include <lwip/ip4_addr.h>
#define IPADDR_NONE         ((u32_t)0xffffffffUL)

/*#ifndef IPADDR_NONE
#error IPADDR_NONE
#endif*/

#include <sys/socket.h>
#include <netinet/in.h>

//#include <lwip/ip4_addr.h>
//#include <lwip/inet.h>

#define channel ADC1_CHANNEL_7
#define pin ADC1_CHANNEL_7_GPIO_NUM
#define ar_pin A7

#define DEFAULT_VREF 1100

#define SDA_VIBE 33
#define SCL_VIBE 32

#define WIFI_SSID "RPD"
#define WIFI_PASS "_8rpdpass"

//const byte DNS_PORT = 53;

#define SAMPLE_RATE 2000 // (SAMPLE_RATE * 12) / 16 должно являться целым числом.

const int LED_BUILTIN = 2;

static esp_adc_cal_characteristics_t *adc_chars;
static const adc_atten_t atten = ADC_ATTEN_DB_11;
static const adc_unit_t unit = ADC_UNIT_1;
static int counter = 0;

WiFiManager wifiManager;
//DNSServer dnsServer;
WebServer webServer(80);

WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP);
unsigned long epoch_time;

DoubleBuffer dbuf(SAMPLE_RATE);
unsigned short packed_buffer[(SAMPLE_RATE * 12) / 16];
unsigned short *packed_buffer_ptr = packed_buffer;
uint8_t compressed_buffer[SAMPLE_RATE * sizeof(unsigned short)]; // ставим размер больше, на случай, если данные не сожмутся...
Pack12bit packer;
String sb64buffer;

String responseHTML = "<!DOCTYPE html><html>"
                      "<head><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
                      "<style>html { font-family: Helvetica; display: inline-block; margin: 0px auto; text-align: center;}"
                      "</style></head>"
                      "<body><h1>ESP32 Web Server</h1>"
                      "<p>Hello World</p>"
                      "</body></html>";

const char server_name[] = "rpd";

//unsigned long next_time;
//int timeout = 30000;

class MyVibe: public SFE_HMD_DRV2605L
{
  public:
    bool begin(int sda, int scl)
    {
      Wire.begin(sda, scl);
      //Get a read from the status register
      //Want this to Read 0xE0, any other value than 0 and you have tripped the over-current protection=wrong motor
      uint8_t status = readDRV2605L(STATUS_REG);
      Serial.print("Status Register 0x"); 
      Serial.println(status, HEX);
     
      return true;
    }
};

MyVibe HMD;

void check_efuse()
{
    //Check TP is burned into eFuse
    if (esp_adc_cal_check_efuse(ESP_ADC_CAL_VAL_EFUSE_TP) == ESP_OK) {
        Serial.println("eFuse Two Point: Supported");
    } else {
        Serial.println("eFuse Two Point: NOT supported");
    }

    //Check Vref is burned into eFuse
    if (esp_adc_cal_check_efuse(ESP_ADC_CAL_VAL_EFUSE_VREF) == ESP_OK) {
        Serial.println("eFuse Vref: Supported");
    } else {
        Serial.println("eFuse Vref: NOT supported");
    }
}

void print_char_val_type(esp_adc_cal_value_t val_type)
{
    if (val_type == ESP_ADC_CAL_VAL_EFUSE_TP) {
        Serial.println("Characterized using Two Point Value\n");
    } else if (val_type == ESP_ADC_CAL_VAL_EFUSE_VREF) {
        Serial.println("Characterized using eFuse Vref");
    } else {
        Serial.println("Characterized using Default Vref");
    }
}

String NumToAtten(int atten)
{
  switch (atten)
  {
    case 0:
      return "ADC_ATTEN_DB_0. No chages for the input voltage";
    case 1:
      return "ADC_ATTEN_DB_2_5. The input voltage will be reduce to about 1/1.34.";
    case 2:
      return "ADC_ATTEN_DB_6. The input voltage will be reduced to about 1/2";
    case 3:
      return "ADC_ATTEN_DB_11. The input voltage will be reduced to about 1/3.6";  
  }
  return "Unknown attenuation.";
}

String NumToWidth(int width)
{
  switch (width)
  {
    case 0:
      return "ADC_WIDTH_BIT_9. ADC capture width is 9Bit";
    case 1:
      return "ADC_WIDTH_BIT_10. ADC capture width is 10Bit";
    case 2:
      return "ADC_WIDTH_BIT_11. ADC capture width is 11Bit";
    case 3:
      return "ADC_WIDTH_BIT_12. ADC capture width is 12Bit";  
  }
  return "Unknown width.";
}

static void IRAM_ATTR timer0_ISR(void *ptr)
{

  //Reset irq and set for next time
  TIMERG0.int_clr_timers.t0 = 1;
  TIMERG0.hw_timer[0].config.alarm_en = 1;

  int val = adc1_get_raw(channel);
  dbuf.add(val);
}

static void timerInit()
{
  timer_config_t config = {
    .alarm_en = TIMER_ALARM_EN, // Включить прерывание Alarm
    .counter_en = TIMER_PAUSE, // Состояние - пауза
    .intr_type = TIMER_INTR_LEVEL, // Прерывание по уровню
    .counter_dir = TIMER_COUNT_UP, // Считать вверх
    .auto_reload = 1, // Автоматически перезапускать счет
    .divider = 8, // Предделитель
  };

  // Применить конфиг
  ESP_ERROR_CHECK(timer_init(TIMER_GROUP_0, TIMER_0, &config));
  // Установить начальное значение счетчика
  ESP_ERROR_CHECK(timer_set_counter_value(TIMER_GROUP_0, TIMER_0, 0x00000000ULL));
  // Установить значение счетчика для срабатывания прерывания Alarm
  ESP_ERROR_CHECK(timer_set_alarm_value(TIMER_GROUP_0, TIMER_0, TIMER_BASE_CLK / config.divider / SAMPLE_RATE));
  // Разрешить прерывания
  ESP_ERROR_CHECK(timer_enable_intr(TIMER_GROUP_0, TIMER_0));
  // Зарегистрировать обработчик прерывания
  timer_isr_register(TIMER_GROUP_0, TIMER_0, timer0_ISR, NULL, ESP_INTR_FLAG_IRAM, NULL);
  // Запустить таймер
  //timer_start(TIMER_GROUP_0, TIMER_0);
}

void setup()
{
  delay(3000);
  Serial.begin(115200);

  // инициализация вибромотора:
  HMD.begin(SDA_VIBE, SCL_VIBE);
  HMD.Mode(0); // Internal trigger input mode -- Must use the GO() function to trigger playback.
  HMD.MotorSelect(0x36); // ERM motor, 4x Braking, Medium loop gain, 1.365x back EMF gain
  HMD.Library(2); //1-5 & 7 for ERM motors, 6 for LRA motors 

  //HMD.Waveform(0, 83);
  //HMD.go();

  // инициализация WiFi:
  wifiManager.setHostname("rpd");
  wifiManager.autoConnect(WIFI_SSID, WIFI_PASS);

  /*dnsServer.setTTL(300);
  dnsServer.setErrorReplyCode(DNSReplyCode::NoError);
  //dnsServer.setErrorReplyCode(DNSReplyCode::ServerFailure);
  dnsServer.start(DNS_PORT, "rpd", WiFi.localIP());
  */

  timeClient.begin();
  timeClient.setTimeOffset(0); // UTC
  
  webServer.onNotFound([]() {
    webServer.send(200, "text/html", responseHTML);
  });
  webServer.begin();

  timerInit();
  pinMode(LED_BUILTIN, OUTPUT);
  setupTelnet();

  // инициализация АЦП:
  adc1_config_width(ADC_WIDTH_BIT_12);
  adc1_config_channel_atten(channel,ADC_ATTEN_DB_11);

  check_efuse();

  //Characterize ADC at particular atten
  adc_chars = (esp_adc_cal_characteristics_t *)calloc(1, sizeof(esp_adc_cal_characteristics_t));
  esp_adc_cal_value_t val_type = esp_adc_cal_characterize(unit, atten, ADC_WIDTH_BIT_12, DEFAULT_VREF, adc_chars);

  Serial.println("ADC number:\t" + String(adc_chars->adc_num));
  Serial.println("ADC attenuation:\t" + NumToAtten(adc_chars->atten));
  Serial.println("ADC bit width:\t" + NumToWidth(adc_chars->bit_width));
  Serial.println("ADC coeff_a:\t" + String(adc_chars->coeff_a));
  Serial.println("ADC coeff_b:\t" + String(adc_chars->coeff_b));
  Serial.println("ADC VRef:\t" + String(adc_chars->vref));

  //Check type of calibration value used to characterize ADC
  print_char_val_type(val_type);

  dbuf.onFillingComplete([](unsigned short *pbuf) {
    BaseType_t xHigherPriorityTaskWoken = pdFALSE;
    xSemaphoreGiveFromISR(xSendSemaphore, &xHigherPriorityTaskWoken);
  });

  packer.onProduce([](unsigned short v) {
    *packed_buffer_ptr++ = v;
  });
}

void loop()
{
  webServer.handleClient();
}
