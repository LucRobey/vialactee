#include <magnetic_ball.h>

Magnetic_ball::Magnetic_ball(vector<CRGB*> local_sorted_leds,byte ID, int* bandSmoothedValues, byte* asservedPower , byte* asservedBandPower)
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

    bassColor = 35;
    aiguColor = 145;

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

    this->ID=ID;

    for (byte a=0 ; a<16 ; a++)
    {
        localAsservissement[a]=pow((0.8+0.2*(float(a)/7)),2);
    }
    
}
// ================================= Extending_waves_mode()
  

void Magnetic_ball::update()
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

    bassSize +=  0.6 *((maxSize*bassValue) - bassSize);     //On smoothisifie un peu quand meme
    aiguSize +=  0.6 *((maxSize*aiguValue) - aiguSize);

    musicCenter/=(15*musicWeight);
    if(musicCenter<coefToMiddle) musicCenter *=(musicCenter+coefToMiddle)/(2*coefToMiddle);        //coef qui écarte les valeurs de part et d autre
    else musicCenter *=1 + 0.5* (musicCenter-coefToMiddle)/(1-coefToMiddle);

    if(midBallPos>listSize/2) acceleration = (float(*asservedPower)/255) * (listSize * musicCenter - midBallPos) - 0.05* pow((listSize/2 - midBallPos),2); //a = |puissance| *  (écartALaMoyenne + écartAuMilieu)
    else acceleration = (float(*asservedPower)/255) * (listSize * musicCenter - midBallPos) + 0.05* pow((listSize/2 - midBallPos),2);
    speed = speed + 0.3*acceleration;
    
    if(speed>7.5) speed=7.4;        //On veut pas que ça bouge trop vite, sinon la boule se TP
    else if(speed<-7.5) speed=-7.5;

    midBallPos += 0.4*speed;
    if(midBallPos<3) midBallPos=3;
    if(midBallPos>listSize-4) midBallPos=listSize-4;

    midBallColor=160*float(midBallPos-10)/(listSize-20);    //Coulkeur directement liée à la position
    speed -= 0.1*speed; //frottements

    //Asservissement du coef
    if(midBallPos>listSize/2)
    {
        if(lastSign)
        {
            if ( (millis()-timeForCoef)>6000)
            {   //Si la boule est trop en haut depuis trop longtemps, on fait réaugmenter le coef pour envoyer plus de valeurs vers 0 et faire tendre musicCenter vers 0
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
            {//Si c'est l inverse, on le fait tendre vers 0
                coefToMiddle-=0.01*(coefToMiddle);
            }
        }
        else
        {
            lastSign=false;
            timeForCoef=millis();
        }
    }

    if(transition)
    {
        if(!blackOrWhite)
        {//white
            if(!transitionUp)
            {   //White fin de vie
                if(firstPhase)
                {   //D'abord le fond devient blanc
                    if(timeSinceTransition>=firstPhaseLimit)
                    {
                        whiteIntensity=255;
                        firstPhase=false;
                        secondPhase=true;
                    }
                    else
                    {
                        whiteIntensity=255*float(timeSinceTransition)/firstPhaseLimit;
                    }
                }
                if(secondPhase)
                {//Puis les barres d'aigus et graves disparaissent
                    if(timeSinceTransition>=secondPhaseLimit)
                    {
                        barsMaxSize=0;
                        secondPhase=false;
                        thirdPhase=true;
                    }
                    else
                    {
                        barsMaxSize= maxSize * float(secondPhaseLimit - timeSinceTransition)/(secondPhaseLimit-firstPhaseLimit);
                    }
                }
                if(thirdPhase)
                {   //Enfin la boule centrale devient blanche
                    if(timeSinceTransition<0.95*transitionTime)
                    {
                        midBallWhitness = 255 * float(0.95* transitionTime - timeSinceTransition)/(0.95*transitionTime-secondPhaseLimit);
                    }
                    else
                    {
                        midBallWhitness=0;
                    }
                }
            }
            else
            { //White Début de vie
                if(firstPhase)
                { //On fait réapparaitre les bandes
                    if(timeSinceTransition>=firstPhaseLimit)
                    {
                        barsMaxSize=maxSize;
                        firstPhase=false;
                        secondPhase=true;
                    }
                    else
                    {
                        barsMaxSize=maxSize*float(timeSinceTransition)/firstPhaseLimit;
                    }
                }
                if(secondPhase)
                {//Puis la boule
                    if(timeSinceTransition>=secondPhaseLimit)
                    {
                        midBallWhitness=255;
                        secondPhase=false;
                        thirdPhase=true;
                    }
                    else
                    {
                        midBallWhitness= 255 * float(timeSinceTransition-firstPhaseLimit)/(secondPhaseLimit-firstPhaseLimit);
                    }
                }
                if(thirdPhase)
                {  //Et lefond redevient noir
                    if(timeSinceTransition<0.95*transitionTime)
                    {
                        whiteIntensity = 255 * float(0.95* transitionTime - timeSinceTransition)/(0.95*transitionTime-secondPhaseLimit);
                    }
                    else
                    {
                        whiteIntensity=0;
                    }
                }
            }
        }
        else
        {//Black
            if(!transitionUp)
            {//Fin de vie
                if(firstPhase)
                { //On fait disparaitre les barres aigues et graves
                    if(timeSinceTransition>=firstPhaseLimit)
                    {
                        barsMaxSize=0;
                        firstPhase=false;
                        secondPhase=true;
                    }
                    else
                    {
                        barsMaxSize=maxSize*float(firstPhaseLimit - timeSinceTransition)/firstPhaseLimit;
                    }
                }
                if(secondPhase)
                {//On fait disparaitre la midBall
                    if(timeSinceTransition>=0.98*transitionTime)
                    {
                        midBallPowerCoef=0;
                    }
                    else
                    {
                        midBallPowerCoef=  1-float(timeSinceTransition-firstPhaseLimit)/(0.98*transitionTime-firstPhaseLimit);
                    }
                }
            }
            else
            {   //Début de vie
                if(firstPhase)
                { //On fait réapparaitre les barres aigues et graves
                    if(timeSinceTransition>=firstPhaseLimit)
                    {
                        midBallPowerCoef=1;
                        firstPhase=false;
                        secondPhase=true;
                    }
                    else
                    {
                        midBallPowerCoef=  float(timeSinceTransition)/firstPhaseLimit;
                    }
                    
                }
                if(secondPhase)
                {//On fait réapparaitre la midBall
                    if(timeSinceTransition>=0.98*transitionTime)
                    {
                        barsMaxSize=maxSize;
                    }
                    else
                    {
                        barsMaxSize=maxSize*float(timeSinceTransition-firstPhaseLimit)/(0.98*transitionTime-firstPhaseLimit);
                    }
                }
            }
        }
    }
    

}
// ================================= update()

void Magnetic_ball::draw()
{
    if(!transition)
    {
        //Bandes:
        bassPower = 0.5 * (255*bassValue - bassPower);
        for (byte led=0 ; led<=bassSize ; led++)
        {
            (*local_sorted_leds[led])=CHSV(bassColor,255,bassPower*float(bassSize-led)/bassSize);
        }
        aiguPower = 0.5 * (255*aiguValue - aiguPower);
        for (byte led=0 ; led<=aiguSize ; led++)
        {
            
            (*local_sorted_leds[listSize-1-led])=CHSV(aiguColor,255,aiguPower*float(aiguSize-led)/aiguSize);

        }
        //boule:
        midPower = 0.5*(0.5*(int(*asservedPower)+255)+midPower);
        (*local_sorted_leds[midBallPos-2])=CHSV(midBallColor,255,midPower);
        (*local_sorted_leds[midBallPos-1])=CHSV(midBallColor,255,midPower);
        (*local_sorted_leds[midBallPos])=CHSV(midBallColor,150,midPower);
        (*local_sorted_leds[midBallPos+1])=CHSV(midBallColor,255,midPower);
        (*local_sorted_leds[midBallPos+2])=CHSV(midBallColor,255,midPower);
    }
    else
    {
        if(!blackOrWhite)
        {   //D'abord, on dessine normalement
            if(!transitionUp)
            {
                if(firstPhase)
                {
                    for(int whiteLeds=bassSize+1 ; whiteLeds<listSize-aiguSize ; whiteLeds++ )
                    {
                        (*local_sorted_leds[whiteLeds])=CHSV(0,0,whiteIntensity);
                    }
                    bassPower = 0.5 * (255*bassValue - bassPower);
                    if(bassPower<whiteIntensity) bassPower=whiteIntensity;
                    for (byte led=0 ; led<=bassSize ; led++)
                    {
                        (*local_sorted_leds[led])=CHSV(bassColor,255,whiteIntensity + (bassPower-whiteIntensity)*float(bassSize-led)/bassSize);
                    }
                    aiguPower = 0.5 * (255*aiguValue - aiguPower);
                    if(aiguPower<whiteIntensity) aiguPower=whiteIntensity;
                    for (byte led=0 ; led<=aiguSize ; led++)
                    {
                        
                        (*local_sorted_leds[listSize-1-led])=CHSV(aiguColor,255,whiteIntensity+(aiguPower-whiteIntensity)*float(aiguSize-led)/aiguSize);

                    }
                    midPower = 0.5*(0.5*(int(*asservedPower)+255)+midPower);
                    if(midPower<whiteIntensity) midPower=whiteIntensity;
                    (*local_sorted_leds[midBallPos-2])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos-1])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos])=CHSV(midBallColor,150,midPower);
                    (*local_sorted_leds[midBallPos+1])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos+2])=CHSV(midBallColor,255,midPower);
                }
                if(secondPhase)
                {
                    
                    if(barsMaxSize>0)
                    {
                        bassPower = 0.5 * (255*bassValue - bassPower);
                        if(bassSize>barsMaxSize) bassSize=barsMaxSize;
                        for (byte led=0 ; led<=bassSize ; led++)
                        {
                            (*local_sorted_leds[led])=CHSV(bassColor,255,255);
                        }
                        aiguPower = 0.5 * (255*aiguValue - aiguPower);
                        if(aiguSize>barsMaxSize) aiguSize=barsMaxSize;
                        for (byte led=0 ; led<=aiguSize ; led++)
                        {
                            
                            (*local_sorted_leds[listSize-1-led])=CHSV(aiguColor,255,255);

                        }
                        for(int whiteLeds=bassSize+1 ; whiteLeds<listSize-1-aiguSize ; whiteLeds++ )
                        {
                            (*local_sorted_leds[whiteLeds])=CHSV(0,0,255);
                        }
                    }
                    else
                    {
                        for(int whiteLeds=0 ; whiteLeds<listSize ; whiteLeds++ )
                        {
                            (*local_sorted_leds[whiteLeds])=CHSV(0,0,255);
                        }
                    }
                    (*local_sorted_leds[midBallPos-2])=CHSV(midBallColor,255,255);
                    (*local_sorted_leds[midBallPos-1])=CHSV(midBallColor,255,255);
                    (*local_sorted_leds[midBallPos])=CHSV(midBallColor,150,255);
                    (*local_sorted_leds[midBallPos+1])=CHSV(midBallColor,255,255);
                    (*local_sorted_leds[midBallPos+2])=CHSV(midBallColor,255,255);
                }
                if(thirdPhase)
                {
                    for(int whiteLeds=0 ; whiteLeds<listSize ; whiteLeds++ )
                    {
                        (*local_sorted_leds[whiteLeds])=CHSV(0,0,255);
                    }
                    (*local_sorted_leds[midBallPos-2])=CHSV(midBallColor,midBallWhitness,255);
                    (*local_sorted_leds[midBallPos-1])=CHSV(midBallColor,midBallWhitness,255);
                    (*local_sorted_leds[midBallPos])=CHSV(midBallColor,midBallWhitness,255);
                    (*local_sorted_leds[midBallPos+1])=CHSV(midBallColor,midBallWhitness,255);
                    (*local_sorted_leds[midBallPos+2])=CHSV(midBallColor,midBallWhitness,255);
                }
            }
            else
            {//White début de vie
                if(firstPhase)
                {
                    bassPower = 0.5 * (255*bassValue - bassPower);
                    if(bassSize>barsMaxSize) bassSize=barsMaxSize;
                    for (byte led=0 ; led<=bassSize ; led++)
                    {
                        (*local_sorted_leds[led])=CHSV(bassColor,255,255);
                    }
                    aiguPower = 0.5 * (255*aiguValue - aiguPower);
                    if(aiguSize>barsMaxSize) aiguSize=barsMaxSize;
                    for (byte led=0 ; led<=aiguSize ; led++)
                    {
                        
                        (*local_sorted_leds[listSize-1-led])=CHSV(aiguColor,255,255);

                    }
                    for(int whiteLeds=bassSize+1 ; whiteLeds<listSize-1-aiguSize ; whiteLeds++ )
                    {
                        (*local_sorted_leds[whiteLeds])=CHSV(0,0,255);
                    }
                }
                if(secondPhase)
                {
                    for (byte led=0 ; led<=bassSize ; led++)
                    {
                        (*local_sorted_leds[led])=CHSV(bassColor,255,255);
                    }
                    for (byte led=0 ; led<=aiguSize ; led++)
                    {  
                        (*local_sorted_leds[listSize-1-led])=CHSV(aiguColor,255,255);
                    }
                    for(int whiteLeds=bassSize+1 ; whiteLeds<listSize-1-aiguSize ; whiteLeds++ )
                    {
                        (*local_sorted_leds[whiteLeds])=CHSV(0,0,255);
                    }
                    (*local_sorted_leds[midBallPos-2])=CHSV(midBallColor,midBallWhitness,255);
                    (*local_sorted_leds[midBallPos-1])=CHSV(midBallColor,midBallWhitness,255);
                    (*local_sorted_leds[midBallPos])=CHSV(midBallColor,midBallWhitness,255);
                    (*local_sorted_leds[midBallPos+1])=CHSV(midBallColor,midBallWhitness,255);
                    (*local_sorted_leds[midBallPos+2])=CHSV(midBallColor,midBallWhitness,255);
                }
                if (thirdPhase)
                {
                    for(int whiteLeds=bassSize+1 ; whiteLeds<listSize-aiguSize ; whiteLeds++ )
                    {
                        (*local_sorted_leds[whiteLeds])=CHSV(0,0,whiteIntensity);
                    }
                    bassPower = 0.5 * (255*bassValue - bassPower);
                    if(bassPower<whiteIntensity) bassPower=whiteIntensity;
                    for (byte led=0 ; led<=bassSize ; led++)
                    {
                        (*local_sorted_leds[led])=CHSV(bassColor,255,whiteIntensity + (bassPower-whiteIntensity)*float(bassSize-led)/bassSize);
                    }
                    aiguPower = 0.5 * (255*aiguValue - aiguPower);
                    if(aiguPower<whiteIntensity) aiguPower=whiteIntensity;
                    for (byte led=0 ; led<=aiguSize ; led++)
                    { 
                        (*local_sorted_leds[listSize-1-led])=CHSV(aiguColor,255,whiteIntensity+(aiguPower-whiteIntensity)*float(aiguSize-led)/aiguSize);
                    }
                    midPower = 0.5*(0.5*(int(*asservedPower)+255)+midPower);
                    if(midPower<whiteIntensity) midPower=whiteIntensity;
                    (*local_sorted_leds[midBallPos-2])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos-1])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos])=CHSV(midBallColor,150,midPower);
                    (*local_sorted_leds[midBallPos+1])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos+2])=CHSV(midBallColor,255,midPower);
                }
            }
        }
        else
        {//Black
            if(!transitionUp)
            {//Fin de vie
                if(firstPhase)
                {
                    bassPower = 0.5 * (255*bassValue - bassPower);
                    if(bassSize>barsMaxSize) bassSize=barsMaxSize;
                    for (byte led=0 ; led<=bassSize ; led++)
                    {
                        (*local_sorted_leds[led])=CHSV(bassColor,255,bassPower*float(bassSize-led)/bassSize);
                    }
                    aiguPower = 0.5 * (255*aiguValue - aiguPower);
                    if(aiguSize>barsMaxSize) aiguSize=barsMaxSize;
                    for (byte led=0 ; led<=aiguSize ; led++)
                    { 
                        (*local_sorted_leds[listSize-1-led])=CHSV(aiguColor,255,aiguPower*float(aiguSize-led)/aiguSize);
                    }
                    midPower = 0.5*(0.5*(int(*asservedPower)+255)+midPower);
                    (*local_sorted_leds[midBallPos-2])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos-1])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos])=CHSV(midBallColor,150,midPower);
                    (*local_sorted_leds[midBallPos+1])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos+2])=CHSV(midBallColor,255,midPower);

                }
                if(secondPhase)
                {
                    midPower = 0.5*(0.5*(int(*asservedPower)+255)+midPower);
                    (*local_sorted_leds[midBallPos-2])=CHSV(midBallColor,255,midBallPowerCoef*midPower);
                    (*local_sorted_leds[midBallPos-1])=CHSV(midBallColor,255,midBallPowerCoef*midPower);
                    (*local_sorted_leds[midBallPos])=CHSV(midBallColor,150,midBallPowerCoef*midPower);
                    (*local_sorted_leds[midBallPos+1])=CHSV(midBallColor,255,midBallPowerCoef*midPower);
                    (*local_sorted_leds[midBallPos+2])=CHSV(midBallColor,255,midBallPowerCoef*midPower);
                }
            }
            else
            {//Début de vie
                if(firstPhase)
                {
                    midPower = 0.5*(0.5*(int(*asservedPower)+255)+midPower);
                    (*local_sorted_leds[midBallPos-2])=CHSV(midBallColor,255,midBallPowerCoef*midPower);
                    (*local_sorted_leds[midBallPos-1])=CHSV(midBallColor,255,midBallPowerCoef*midPower);
                    (*local_sorted_leds[midBallPos])=CHSV(midBallColor,150,midBallPowerCoef*midPower);
                    (*local_sorted_leds[midBallPos+1])=CHSV(midBallColor,255,midBallPowerCoef*midPower);
                    (*local_sorted_leds[midBallPos+2])=CHSV(midBallColor,255,midBallPowerCoef*midPower);
                }
                if(secondPhase)
                {
                    bassPower = 0.5 * (255*bassValue - bassPower);
                    if(bassSize>barsMaxSize) bassSize=barsMaxSize;
                    for (byte led=0 ; led<=bassSize ; led++)
                    {
                        (*local_sorted_leds[led])=CHSV(bassColor,255,bassPower*float(bassSize-led)/bassSize);
                    }
                    aiguPower = 0.5 * (255*aiguValue - aiguPower);
                    if(aiguSize>barsMaxSize) aiguSize=barsMaxSize;
                    for (byte led=0 ; led<=aiguSize ; led++)
                    { 
                        (*local_sorted_leds[listSize-1-led])=CHSV(aiguColor,255,aiguPower*float(aiguSize-led)/aiguSize);
                    }
                    midPower = 0.5*(0.5*(int(*asservedPower)+255)+midPower);
                    (*local_sorted_leds[midBallPos-2])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos-1])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos])=CHSV(midBallColor,150,midPower);
                    (*local_sorted_leds[midBallPos+1])=CHSV(midBallColor,255,midPower);
                    (*local_sorted_leds[midBallPos+2])=CHSV(midBallColor,255,midPower);
                }
            }
        }
   }

   
    if(transition)
    {
        updateTransitionTimer();
    }
}
// ================================= draw()

void Magnetic_ball::updateTransitionTimer()
{
    timeSinceTransition+=1;
    if (timeSinceTransition>=transitionTime)
    {
        resetTransition();
    }
}
// ================================= updateTransitionTimer()

void Magnetic_ball::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
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
            firstPhase=true;
            secondPhase=false;
            thirdPhase=false;
            firstPhaseLimit=0.95*float(transitionTime)/3;
            secondPhaseLimit=2*firstPhaseLimit;
            whiteIntensity=0;
            barsMaxSize=listSize;
            midBallWhitness=255;
            Serial.println("                                                            Coloured_middle_wave  ==>       ( white transition ) ");
        }
        else
        {//debut de vie
            firstPhase=true;
            secondPhase=false;
            thirdPhase=false;
            firstPhaseLimit=0.95*float(transitionTime)/3;
            secondPhaseLimit=2*firstPhaseLimit;
            whiteIntensity=255;
            barsMaxSize=0;
            midBallWhitness=0;
            Serial.println("                                                            ==>  Coloured_middle_wave     ( white transition ) ");
        }
    }
    else
    {//black
        if (!this->transitionUp)
        {//fin de vie
            firstPhase=true;
            secondPhase=false;
            barsMaxSize=maxSize;
            firstPhaseLimit=0.48*transitionTime;
            midBallPowerCoef=1;
            Serial.println("                                                            Coloured_middle_wave  ==>       ( black  transition ) ");
        }
        else
        {//debut de vie
            firstPhase=true;
            secondPhase=false;
            barsMaxSize=0;
            firstPhaseLimit=0.48*transitionTime;
            midBallPowerCoef=0;
            Serial.println("                                                             ==>  Coloured_middle_wave     ( black  transition ) ");
        }
    }
}
// ================================= startTransition()

void Magnetic_ball::resetTransition()
{
    this->transition=false;
    Serial.println("                                                             |Coloured_middle_wave|    ");
}
// ================================= resetTransition()