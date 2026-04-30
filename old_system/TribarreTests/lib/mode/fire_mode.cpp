#include <fire_mode.h>

Fire_mode::Fire_mode(vector<CRGB*> local_sorted_leds,byte ID, byte* samplePeak)
{
    initiateVariables(ID,local_sorted_leds);

    this->fadeToBlackInt=100;

    brasier=3+listSize/6;
    temperatures.clear();
    for (int b=0 ; b<listSize ; b++)
    {
        temperatures.push_back(0);
    }

    //Data
    this->samplePeak=samplePeak;

    this->analysingNeeds[0] = true;
    this->analysingNeeds[1] = true;
    this->analysingNeeds[2] = true;
    this->analysingNeeds[3] = false;
    this->analysingNeeds[4] = false;
    for (byte band=0 ; band<16 ; band++)
    {
        bandAnalysingNeeds[band]=false;
    }
}
// ================================= Fire_mode()
  
byte total;
byte randomPos;
byte randomAdd;
void Fire_mode::update()
{
    if(!(transition && !blackOrWhite && !transitionUp))     //On applique le refroidissement tout le temps sauf pour la transi blanche/fin de vie
    {                                                       //Car dans cette transi, on veut que la température augment jusqu a 255
        for(int i = 0; i < listSize; i++) 
        {
            refroidissement = random(0, (((30+i) * 10) / listSize) + 2);

            if(refroidissement > temperatures[i])       //Obligé de faire ça car temperatures est en bytes
            {                                           //Ce qui fait que 255+1=0
                temperatures[i] = 0;        
            }
            else 
            {
                temperatures[i] -= refroidissement;
            }
        }
    }
    if(transition && blackOrWhite)
    {//black
        if(!transitionUp)
        {//fin de vie

            //On utilise un coefficient de transition pour la continuité
            // coef : 0  ->            1           ->        1
            // time : 0  ->  (95%*transitionTime)  ->  transitionTime
            if(transiCoef<1)
            {
                transiCoef=float(timeSinceTransition)/(0.95*transitionTime);
                if(transiCoef>1)
                {
                    transiCoef=1;
                }
            }
        }
        else
        {//début de vie

            //On utilise un coefficient de transition pour la continuité
            // coef : 1  ->            0         ->        0
            // time : 0  ->  (transitionTime/2)  ->  transitionTime
            if(transiCoef>0)
            {
                transiCoef=1-float(timeSinceTransition)/(0.5*transitionTime);
                if(transiCoef<0)
                {
                    transiCoef=0;
                }
            }
        }
    }
    
    // la température monte
    for(int k = listSize-1; k >= 2; k--) 
    {
        temperatures[k] = (temperatures[k - 1] + temperatures[k - 2] + temperatures[k]) / 3;
    }

    // On fait apparaître des pics de chaleurs de manière random/sur les peaks dans le brasier
    // Ceci permet de faire chauffer toute la barre, durant la transi blanche/fin de vie
    if(transition && !blackOrWhite && !transitionUp)
    {   
        total=0;
        for (byte s=0 ; s<16 ; s++)
        {
            total+=samplePeak[s];
        }   
        if(total>=12)
        {//Si y a un max de peaks, on fait augmenter la température
            randomPos=random(brasier);
            randomAdd=50+random(75);
            if(temperatures[randomPos]+randomAdd>255)
            {
                temperatures[randomPos] = 255;
            }
            else
            {
                temperatures[randomPos]+=randomAdd;
            }
        }
        else if(random(255) < 200) 
        {//De maniere random, on fait augmenter la température
            randomPos=random(brasier);
            randomAdd=10+random(55);
            if(temperatures[randomPos]+randomAdd>255)
            {
                temperatures[randomPos] = 255;
            }
            else
            {
                temperatures[randomPos]+=randomAdd;
            }
        }
    }
    else
    {// On fait apparaître des pics de chaleurs/froids de manière random/sur les peaks dans le brasier
     //Il y a aussi des pics de froids car 255+1=0!
        total=0;
        for (byte s=0 ; s<16 ; s++)
        {
            total+=samplePeak[s];
        }
        if(total>=6)
        {//Si y a un max de peaks, on fait augmenter la température
            for(byte bi=6 ; bi<=total ; bi++)
            {
                temperatures[random(brasier)]=255;
            }
        }
        else if(random(255) < 100) 
        {//Sinon, de maniere random, on fait varier brutalement la température
            temperatures[random(brasier)] += (20+random(100));
        }
    }
}
// ================================= update()

float temperatureCoefF;
void Fire_mode::draw()
{
    if (transition && blackOrWhite)
    {//Black transitions
        for(int j = 0; j < listSize; j++)
        {//Juste pour faire baisser le calcul, si transiCoef =1 ou 0, on se fatigue pas à calculer l'intensité, on la connait
            if(transiCoef==0)
            {
                temperatureCoefF=float(temperatures[j])/255;
                if(temperatures[j]>20)
                {
                (*local_sorted_leds[j])=CHSV(30*temperatureCoefF,255*(1-temperatureCoefF), (155+100*temperatureCoefF));
                }
            }
            else if(transiCoef==1)
            {
                //do nothing
            }
            else
            {
                temperatureCoefF=float(temperatures[j])/255;
                if(temperatures[j]>20)
                {
                (*local_sorted_leds[j])=CHSV(30*temperatureCoefF,255*(1-temperatureCoefF), (155+100*temperatureCoefF) * (1-transiCoef));
                }
            }
            
        }
    }
    else
    {//Sinon la température fait virer la couleur au orange, la whitness vers 0 et augmenter l'intensité 
        for(int j = 0; j < listSize; j++)
        {
            temperatureCoefF=float(temperatures[j])/255;
            if(temperatures[j]>20)
            {
            (*local_sorted_leds[j])=CHSV(30*temperatureCoefF,255*(1-temperatureCoefF), (155+100*temperatureCoefF));
            }
        }
    }

    if(transition)
    {
        updateTransitionTimer();
    }
}
// ================================= draw()

void Fire_mode::activate()
{
    this->activated=true;
}
// ================================= activate()

void Fire_mode::deactivate()
{
    this->activated=false;
    local_sorted_leds.clear();
    temperatures.clear();
}
// ================================= deactivate()


void Fire_mode::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
{
    this->transition=true;
    this->blackOrWhite=blackOrWhite;
    this->transitionUp=upOrDown;
    this->timeSinceTransition=0;
    this->transitionTime=transitionTime;
    if (!blackOrWhite)
    {//white
        if (!upOrDown)
        {//fin de vie
            Serial.println("                                                            fire_mode  ==>       ( white transition ) ");
        }
        else
        {//debut de vie
        for (byte b=0 ; b<listSize ; b++)
        {
            temperatures[b]=255;
        }
            Serial.println("                                                             ==>  fire_mode     ( white transition ) ");
        }
    }
    else
    {//black
        if (!upOrDown)
        {//fin de vie
            transiCoef=0;
            Serial.println("                                                             fire_mode  ==>       ( black  transition ) ");
        }
        else
        {//debut de vie
            transiCoef=1;
            Serial.println("                                                             ==>  fire_mode     ( black  transition ) ");
        }
    }
}
// ================================= startTransition()

void Fire_mode::resetTransition()
{
    this->transition=false;
    Serial.println("                                                              |fire_mode|    ");
}
// ================================= resetTransition()

