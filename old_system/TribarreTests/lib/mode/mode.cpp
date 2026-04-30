#include <mode.h>
#include <FastLED.h>

Mode::Mode(vector<CRGB*> local_sorted_leds)
{
    this->local_sorted_leds=local_sorted_leds;
    this->activated=0;
    this->listSize=local_sorted_leds.size();
    resetTransition();
}

void Mode::update()
{
}

void Mode::draw()
{
    if(transition)
    {
        updateTransitionTimer();
    }
}
// ======================================== draw()

int Mode::getFadeToBlackCoef()
{
    return fadeToBlackInt;
}
// ======================================== getFadeToBlackCoef()

void Mode::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
{
    this->transition=true;
    this->transitionUp=upOrDown;
    this->blackOrWhite=blackOrWhite;
    this->timeSinceTransition=0;
    this->transitionTime=transitionTime;
}

bool Mode::isTransitionFinished()
{
    return !transition;
}
// ======================================== isTransitionFinished()

void Mode::resetTransition()
{
    transition=false;
    timeSinceTransition=0;
}
// ======================================== resetTransition()

void Mode::updateTransitionTimer()
{
    timeSinceTransition+=1;
    if (timeSinceTransition>=transitionTime)
    {
        resetTransition();
    }
}
// ======================================== updateTransitionTimer()

bool Mode::isActivated()
{
    return activated;
}
// ======================================== isActivated()

void Mode::activate()
{
    activated=true;
}
// ======================================== activate()

void Mode::deactivate()
{
    this->activated=false;
}
// ======================================== deactivate()

bool* Mode::getAnalysingNeeds()
{
    return analysingNeeds;
}
// ======================================== getAnalysingNeeds()

bool* Mode::getBandAnalysingNeeds()
{
    return bandAnalysingNeeds;
}
// ======================================== getBandAnalysingNeeds()

void Mode::printID()
{
    Serial.print(ID);
}
// ======================================== getBandAnalysingNeeds()

void Mode::initiateVariables(byte ID ,vector<CRGB*> local_sorted_leds)
{
    this->activated=false;
    this->transition=false;
    this->ID=ID;
    resetTransition();

    this->local_sorted_leds=local_sorted_leds;
    this->listSize=local_sorted_leds.size();
}
// ======================================== initiateVariables()
