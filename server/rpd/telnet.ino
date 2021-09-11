#include <ESPTelnet.h>

struct TDataHeader
{
  uint32_t sig;
  
};

ESPTelnet telnet;

SemaphoreHandle_t xSendSemaphore;

void TelnetSendTask(void *pvParameter)
{
  for(;;)
  {
    int sz = LZ_Compress((unsigned char *)packed_buffer, compressed_buffer, ((SAMPLE_RATE * 12) / 16) * sizeof(unsigned short));

    sb64buffer = base64::encode(compressed_buffer, sz);

    xSemaphoreTake(xSendSemaphore, portMAX_DELAY);

    char sSize[5];
    sprintf(sSize, "%04x", sb64buffer.length());
    telnet.print(sSize);
    telnet.print(sb64buffer);
  } // for(;;)
}

void TelnetTask(void *pvParameter)
{
  // passing on functions for various telnet events
  telnet.onConnect([](String ip) {
    Serial.print("- Telnet: ");
    Serial.print(ip);
    Serial.println(" connected");
    //telnet.println("\nWelcome " + telnet.getIP());
    //telnet.println("(Use ^] + q  to disconnect.)");
  });
  telnet.onConnectionAttempt([](String ip) {
    Serial.print("- Telnet: ");
    Serial.print(ip);
    Serial.println(" tried to connected");
  });
  telnet.onReconnect([](String ip) {
    Serial.print("- Telnet: ");
    Serial.print(ip);
    Serial.println(" reconnected");
  });
  telnet.onDisconnect([](String ip) {
    Serial.print("- Telnet: ");
    Serial.print(ip);
    Serial.println(" disconnected");
  });
  
  // passing a lambda function
  telnet.onInputReceived([](String str) {
    // checks for a certain command
    if (str == "vibro")
    {
      HMD.Waveform(0, 83);
      HMD.go();
      fprintf(stdout, "telnet: vibro requested\n");
    }
  });

  Serial.print("telnet: ");
  int res = telnet.begin();
  if(res)
  {
    Serial.println("running");
    for (;;)
    {
      telnet.loop();
      vTaskDelay(10);
    } // for (;;)
  }
  else
  {
    Serial.println("error.");
  }
}

bool setupTelnet()
{
  bool res = true;

  // Stack size needs to be larger, so continue in a new task.
  xTaskCreatePinnedToCore(TelnetTask, "Telnet", 10000, NULL,
    (tskIDLE_PRIORITY + 3), NULL, portNUM_PROCESSORS - 1);

  xSendSemaphore = xSemaphoreCreateBinary();
  xTaskCreatePinnedToCore(TelnetSendTask, "TelnetSend", 10000, NULL,
    (tskIDLE_PRIORITY + 3), NULL, portNUM_PROCESSORS - 1);

  return res;
}
