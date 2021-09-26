/* ------------------------------------------------- */

#include "ESPTelnetDbg.h"

/* ------------------------------------------------- */

ESPTelnetDbg::ESPTelnetDbg() { 
  isConnected = false; 
}

/* ------------------------------------------------- */

  bool ESPTelnetDbg::begin() {
  ip = "";
  if (WiFi.status() == WL_CONNECTED) {
    server.begin();
    server.setNoDelay(true);
    return true;
  } else {
    return false;
  }
}

/* ------------------------------------------------- */

void ESPTelnetDbg::stop() { 
  server.stop(); 
}

/* ------------------------------------------------- */

bool ESPTelnetDbg::isClientConnected(WiFiClient client) {
#if defined(ARDUINO_ARCH_ESP8266)
  return client.status() == ESTABLISHED;
#else if defined(ARDUINO_ARCH_ESP32)
  return client.connected();
#endif
}

/* ------------------------------------------------- */

void ESPTelnetDbg::loop() {
  //check if there are any new clients
  if (server.hasClient()) {
    isConnected = true;
    // already a connection?
    if (client && client.connected() && isClientConnected(client)) {
      WiFiClient newClient = server.available();
      attemptIp  = newClient.remoteIP().toString();
      // reconnected?
      if (attemptIp == ip) {
        if (on_reconnect != NULL) on_reconnect(ip);
        client.stop();
        client = newClient;
      // disconnect the second connection
      } else {
        if (on_connection_attempt != NULL) on_connection_attempt(ip);
        return;
      }
    // first connection
    } else {
      client = server.available();
      ip = client.remoteIP().toString();
      if (on_connect != NULL) on_connect(ip);
      client.setNoDelay(true);
      client.flush();
    }
  }

  // check whether to disconnect
  //if (client && isConnected && !isClientConnected(client)) {
  if (isConnected && !(client || isClientConnected(client))) {
      if (on_disconnect != NULL) on_disconnect(ip);
      isConnected = false;
      ip = "";
    }
  // gather input
  if (client && isConnected && client.available()) {    
    char c = client.read();
    if (c != '\n') {
      if (c >= 32) {
        input += c; 
      }
    // EOL -> send input
    } else {
      if (on_input != NULL) on_input(input);
      input = "";
      }
  }
    yield();
  } 
  
/* ------------------------------------------------- */
    
void ESPTelnetDbg::print(char c) {
  if (client && isClientConnected(client)) {
    client.print(c); 
  }
}

/* ------------------------------------------------- */

void ESPTelnetDbg::print(String str) {
  if (client && isClientConnected(client)) {
    client.print(str); 
  }
}

/* ------------------------------------------------- */

void ESPTelnetDbg::println(String str) { 
  client.print(str + "\n"); 
}

/* ------------------------------------------------- */

void ESPTelnetDbg::println(char c) { 
  client.print(c + "\n"); 
}

/* ------------------------------------------------- */

void ESPTelnetDbg::println() { 
  client.print("\n"); 
}

/* ------------------------------------------------- */

String ESPTelnetDbg::getIP() const { 
  return ip; 
}

/* ------------------------------------------------- */

String ESPTelnetDbg::getLastAttemptIP() const { 
  return attemptIp; 
}

/* ------------------------------------------------- */

void ESPTelnetDbg::onConnect(CallbackFunction f) { 
  on_connect = f; 
}

/* ------------------------------------------------- */

void ESPTelnetDbg::onConnectionAttempt(CallbackFunction f)  { 
  on_connection_attempt = f; 
}

/* ------------------------------------------------- */

void ESPTelnetDbg::onReconnect(CallbackFunction f) { 
  on_reconnect = f; 
}

/* ------------------------------------------------- */

void ESPTelnetDbg::onDisconnect(CallbackFunction f) { 
  on_disconnect = f; 
}

/* ------------------------------------------------- */

void ESPTelnetDbg::onInputReceived(CallbackFunction f) { 
  on_input = f; 
}

/* ------------------------------------------------- */
