#ifndef MAIN_BLUETOOTH_H
#define MAIN_BLUETOOTH_H

// Write to ESP32 using nRF Connect app

#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <Arduino.h>

using namespace std;


class MyCallbacks: public BLECharacteristicCallbacks {
    void onWrite(BLECharacteristic *pCharacteristic);
};

#endif