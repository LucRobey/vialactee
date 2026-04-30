#include <mode_test_uniform_color.h>

Mode_test_uniform_color::Mode_test_uniform_color(byte ID, int color)
{
    this->activated=false;
    this->fadeToBlackInt=0;
    this->ID=ID;
    resetTransition();

    this->color=color;
    tmeBeforeColoring=0;
    

    this->analysingNeeds[0] = false;
    this->analysingNeeds[1] = false;
    this->analysingNeeds[2] = false;
    this->analysingNeeds[3] = false;
    this->analysingNeeds[4] = false;
    for (byte band=0 ; band<16 ; band++)
    {
        bandAnalysingNeeds[band]=false;
    }
}

int intensity;
int whitness;
void Mode_test_uniform_color::update()
{
    if (!transition)
    {
        intensity=255;
        whitness=255;
    }
    else
    {
        if (!blackOrWhite)
        {//white
            if(!transitionUp)
            {//fin de vie
                intensity=255;
                whitness = 255 * float(float(transitionTime-timeSinceTransition)/transitionTime);
            }
            else
            {//Début de vie
                intensity=255;
                whitness = 255 * float(1-float(transitionTime-timeSinceTransition)/transitionTime);
            }
        }
        else
        {//black
            if(!transitionUp)
            {//fin de vie
                whitness=255;
                intensity = 255 * float(float(transitionTime-timeSinceTransition)/transitionTime);
            }
            else
            {//Début de vie
                whitness=255;
                intensity = 255 * float(1-float(transitionTime-timeSinceTransition)/transitionTime);
            }
        }
    }
    if(tmeBeforeColoring<=0)
    {
        for (int j=0 ; j<local_sorted_leds.size() ; j++)
            {
                *local_sorted_leds[j]=CHSV(color,whitness,intensity);
            }
        tmeBeforeColoring=31;
    }
    tmeBeforeColoring-=1;
}
  void Mode_test_uniform_color::draw()
  {
    if(transition)
    {
        for (int j=0 ; j<local_sorted_leds.size() ; j++)
            {
                *local_sorted_leds[j]=CHSV(color,whitness,intensity);
            }
    }
    if (transition)
    {
        updateTransitionTimer();
    }
  }
