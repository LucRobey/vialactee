#include <band_wars.h>

//Pour les commentaires, aller voir magnetic_ball!!!!

Band_wars::Band_wars(vector<CRGB*> local_sorted_leds,byte ID, int* bandSmoothedValues, byte* asservedPower , byte* asservedBandPower)
{
    initiateVariables(ID,local_sorted_leds);

    this->fadeToBlackInt=55;

    bassSize = listSize/4-1;
    aiguSize = listSize/4-1;

    bassPower = 200;                     
    aiguPower = 200;

    bassColor = 50;
    aiguColor = 120;

    midBallPos = listSize/2+1;
    midBallColor = 90;

    maxSize = listSize/2 - 1; 
    speed = 0;
    acceleration = 0;

    coefToMiddle=0.4;
    lastSign=true;
    timeForCoef=millis();

    //data:
    this->bandSmoothedValues=bandSmoothedValues;
    this->asservedPower=asservedPower;
    this->asservedBandPower=asservedBandPower;

    this->analysingNeeds[0] = true;         //Ecoute
    this->analysingNeeds[1] = true;         //FFT
    this->analysingNeeds[2] = false;        //Peaks
    this->analysingNeeds[3] = true;         //asservBands
    this->analysingNeeds[4] = true;         //Power
    for (byte band=0 ; band<16 ; band++)
    {
        this->bandAnalysingNeeds[band]=true;
    }

    for (byte a=0 ; a<16 ; a++)
    {
        localAsservissement[a]=pow((0.6+0.4*(float(a)/7)),2);
    }
    
}
// ================================= Extending_waves_mode()
  

//Pour les commentaires, aller voir magnetic_ball!!!!
void Band_wars::update()
{
    musicCenter=0;
    musicWeight=0;
    bassValue=0;
    aiguValue=0;

    for (int s=0 ; s<4 ; s++)                          
    {
        fff=bandSmoothedValues[s];
        fff=localAsservissement[s]*fff/100;
        fff=pow(fff,2);

        bassValue+=asservedBandPower[s];
        this->musicCenter+=s*fff;       //Ca permet de mettre en valeur les peaks
        this->musicWeight+=fff;                //On prend le total pour calculer les proportions apres
    }
    for(byte s=3 ; s<7; s++)
    {
        fff=bandSmoothedValues[s];
        fff=localAsservissement[s]*fff/100;
        fff=pow(fff,2);

        this->musicWeight+=fff;  
        this->musicCenter+=s*fff;      
    }
    for (byte s=7 ; s<16 ; s++)                          
    {
        fff=bandSmoothedValues[s];
        fff=localAsservissement[s]*fff/100;
        fff=pow(fff,2);

        aiguValue+=asservedBandPower[s];
        this->musicCenter+=s*fff;
        this->musicWeight+=fff;
    }


    bassValue/=4*255;
    aiguValue/=9*255;

    bassSize +=  0.6 *((maxSize*bassValue) - bassSize);
    aiguSize +=  0.6 *((maxSize*aiguValue) - aiguSize);

    bassColor = 40;
    aiguColor = 135;

    musicCenter/=(15*musicWeight);
    if(musicCenter<coefToMiddle) musicCenter *=(musicCenter+coefToMiddle)/(2*coefToMiddle);
    else musicCenter *=1 + 0.5* (musicCenter-coefToMiddle)/(1-coefToMiddle);

    if(midBallPos>listSize/2) acceleration = (float(*asservedPower)/255) * (listSize * musicCenter - midBallPos) - 0.05* pow((listSize/2 - midBallPos),2);
    else acceleration = (float(*asservedPower)/255) * (listSize * musicCenter - midBallPos) + 0.05* pow((listSize/2 - midBallPos),2);
    speed = speed + 0.3*acceleration;
    
    if(speed>7.5) speed=7.4;
    else if(speed<-7.5) speed=-7.5;
    midBallPos += 0.4*speed;
    if(midBallPos<3) midBallPos=3;
    if(midBallPos>listSize-4) midBallPos=listSize-4;

    midBallColor=160*float(midBallPos-10)/(listSize-20);
    speed -= 0.1*speed;
    if(midBallPos>listSize/2)
    {
        if(lastSign)
        {
            if ( (millis()-timeForCoef)>6000)
            {
                coefToMiddle+=0.01 *(1-coefToMiddle);
            }
        }
        else
        {
            lastSign=true;
            timeForCoef=millis();
        }
    }
    else
    {
        if(!lastSign)
        {
            if ( (millis()-timeForCoef)>6000)
            {
                coefToMiddle-=0.01*(coefToMiddle);
            }
        }
        else
        {
            lastSign=false;
            timeForCoef=millis();
        }
    }
    if (transition)
    {
        if(!blackOrWhite)
        {
            if(!transitionUp)
            {
                whiteness=255*float(transitionTime-timeSinceTransition)/transitionTime;
            }
            else
            {
                whiteness=255*float(timeSinceTransition)/transitionTime;
            }
            blackTransiPowerCoef=1;
        }
        else
        {
            if(!transitionUp)
            {
                blackTransiPowerCoef=float(transitionTime-timeSinceTransition)/transitionTime;
            }
            else
            {
                blackTransiPowerCoef=float(timeSinceTransition)/transitionTime;
            }
            whiteness=255;
        }
    }
}
// ================================= update()

void Band_wars::draw()
{
    if(!transition)
    {
        midPower = 0.5*(0.5*(int(*asservedPower)+255)+midPower);
        for(int led=0 ; led<midBallPos ; led++)
        {
            (*local_sorted_leds[led])=CHSV(10,255,255);
        }
        (*local_sorted_leds[midBallPos])=CHSV(0,0,255);
        for(int led=midBallPos+1 ; led<listSize ; led++)
        {
            (*local_sorted_leds[led])=CHSV(150,255,255);
        }
    }
    else
    {
        midPower = 0.5*(0.5*(int(*asservedPower)+255)+midPower);
        for(int led=0 ; led<midBallPos ; led++)
        {
            (*local_sorted_leds[led])=CHSV(10,whiteness,255*blackTransiPowerCoef);
        }
        (*local_sorted_leds[midBallPos])=CHSV(0,0,255);
        for(int led=midBallPos+1 ; led<listSize ; led++)
        {
            (*local_sorted_leds[led])=CHSV(150,whiteness,255*blackTransiPowerCoef);
        }
    }
   
    if(transition)
    {
        updateTransitionTimer();
    }
}
// ================================= draw()

void Band_wars::updateTransitionTimer()
{
    timeSinceTransition+=1;
    if (timeSinceTransition>=transitionTime)
    {
        resetTransition();
    }
}
// ================================= updateTransitionTimer()

void Band_wars::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
{
    this->transition=true;
    this->blackOrWhite=blackOrWhite;
    this->transitionUp=upOrDown;
    this->timeSinceTransition=0;
    this->transitionTime=transitionTime;
    if (!this->blackOrWhite)
    {//white
        if (!this->transitionUp)
        {//fin de vie
            Serial.println("                                                            Coloured_middle_wave  ==>       ( white transition ) ");
        }
        else
        {//debut de vie
            Serial.println("                                                            ==>  Coloured_middle_wave     ( white transition ) ");
        }
    }
    else
    {//black
        if (!this->transitionUp)
        {//fin de vie
            Serial.println("                                                            Coloured_middle_wave  ==>       ( black  transition ) ");
        }
        else
        {//debut de vie
            Serial.println("                                                             ==>  Coloured_middle_wave     ( black  transition ) ");
        }
    }
}
// ================================= startTransition()

void Band_wars::resetTransition()
{
    this->transition=false;
    Serial.println("                                                             |Coloured_middle_wave|    ");
}
// ================================= resetTransition()