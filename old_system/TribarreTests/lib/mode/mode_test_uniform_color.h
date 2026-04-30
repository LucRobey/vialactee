#ifndef MODE_TEST_UNIFORM_COLOR_H
#define MODE_TEST_UNIFORM_COLOR_H

#include <Arduino.h>
#include <FastLED.h>
using namespace std;
#include <vector>
#include <mode.h>
#pragma once

class Mode_test_uniform_color : public Mode
{
public:
  Mode_test_uniform_color() = default;
  Mode_test_uniform_color(byte ID, int color);
  void update();
  void draw();

private:
  int color;
  int tmeBeforeColoring;
};

#endif
