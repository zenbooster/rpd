#pragma once

#include "ESPTelnetDbg.h"

extern ESPTelnetDbg telnet;
extern SemaphoreHandle_t xSendSemaphore;

bool setupTelnet();
