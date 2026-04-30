#include <power_bar.h>

Power_bar::Power_bar(vector<CRGB*> local_sorted_leds,byte ID, byte* asservedPower)
{
    initiateVariables(ID,local_sorted_leds);

    this->fadeToBlackInt=65;
   
    max_size=listSize-1;
    white_dot_speed=float(listSize)/250;

    intensity=255;

    real_size=0;
    white_dot_pos=0;                                                         //Taille de la limite supérieure blanche qui met plus de temps à redescendre pour un effet visuel sympa
    real_size=0;                                                      //Taille réel de la vague centrale

    //Transition:
    whiteTransitionUpperLimit=0;                                      //Limite haute de coloriage en blanc pour la white Transition
    blackTransitionLowerLimit=0;                                      //Limite basse de coloriage en noir pour la black Transition
    transitionPositionCoef;                                         //Coefficient permettant d'artificiellement augmenter la valeur de real_size
    transitionProportion = 0.75;                                    //La transitio est divisée en 2 phases. Permet de controler le temps de chaque phase
   
    this->asservedPower=asservedPower;

    this->analysingNeeds[0] = true;
    this->analysingNeeds[1] = true;
    this->analysingNeeds[2] = false;
    this->analysingNeeds[3] = false;
    this->analysingNeeds[4] = true;
    for (byte band=0 ; band<16 ; band++)
    {
        bandAnalysingNeeds[band]=false;
    }
   };

void Power_bar::update() 
{
    real_size = 0.5 * (real_size + float((*asservedPower) * max_size)/255);
    if (real_size>max_size)
    {
        real_size=max_size;
    }


    if (transition)
    {
        if (!blackOrWhite)
        {
            if(!transitionUp)
            {                                                                                //Dans cette partie, la barre monte, puis en se retirant elle ne laisse que du blanc
                if (timeSinceTransition<=transitionProportion*transitionTime)
                {
                    transitionPositionCoef=float(timeSinceTransition)/(transitionProportion*transitionTime);               //Elle monte pendant 75% du temps de la transition (soit 3/4), donc le coef passe de 0 à 1 durant cette période
                    real_size=transitionPositionCoef*max_size + (1-transitionPositionCoef)*real_size;
                    whiteTransitionUpperLimit=real_size+1;                                                  //On fait augmenter la valeur supp
                } else 
                {
                    whiteTransitionUpperLimit=max_size;                                     // C'est une descente linéaire de la valeur de la barre. Mais on ne met pas a jour la valeur sup (qui reste égale au max)
                    real_size = max_size * (1-(timeSinceTransition-transitionProportion*transitionTime)/((1-transitionProportion)*transitionTime));
                }
                
            } 
            else 
            {
                if (timeSinceTransition<=transitionProportion*transitionTime)
                {                                              //On fait la mm chose , sauf qu en se retirant, on ne laisse que du noir
                    transitionPositionCoef=float(timeSinceTransition)/(transitionProportion*transitionTime);
                    whiteTransitionUpperLimit=max_size;
                    real_size=transitionPositionCoef*max_size;
                } 
                else 
                {
                    real_size = max_size * (1-(timeSinceTransition-transitionProportion*transitionTime)/((1-transitionProportion)*transitionTime));
                    whiteTransitionUpperLimit=real_size+1;                                                  //La diff se fait ici dans la mise à jour de la val supp à la redescente.
                }

            }
        } 
        else 
        {
            if(!transitionUp)
            {                                                                                //Dans cette partie, la barre monte, puis en se retirant elle ne laisse que du blanc
                if (timeSinceTransition<=transitionProportion*transitionTime)
                {
                    transitionPositionCoef=float(timeSinceTransition)/(transitionProportion*transitionTime);               //Elle monte pendant 75% du temps de la transition (soit 3/4), donc le coef passe de 0 à 1 durant cette période
                    real_size=transitionPositionCoef*max_size + (1-transitionPositionCoef)*real_size;
                } 
                else 
                {
                    blackTransitionLowerLimit=max_size*float(timeSinceTransition-transitionProportion*transitionTime)/((1-transitionProportion)*transitionTime);
                    real_size = max_size;
                } 
            } 
            else 
            {
                if (timeSinceTransition<=transitionProportion*transitionTime)
                {  
                    real_size=max_size;
                    blackTransitionLowerLimit=max_size * (1-float(timeSinceTransition)/(transitionProportion*transitionTime));
                } 
                else 
                {
                    blackTransitionLowerLimit=0;
                    real_size = max_size * (1-float(timeSinceTransition-transitionProportion*transitionTime)/((1-transitionProportion)*transitionTime));
                }
            }
        }
    }

    if(real_size<1)
    {
        real_size=1;
    }

    if(real_size>white_dot_pos)
    {                                                      //white_dot_pos>real_size tj
        white_dot_pos=real_size+1;
    }

    if(real_size<white_dot_pos-1)
    {                                                    //Quand real_size diminue, on fait baisser white_dot_pos 3 fois moins vite
        white_dot_pos-=white_dot_speed;
    }
    testColorChange+=random(2);
};  
//Update()

void Power_bar::draw()
{
    if(transition)
    {
        if(!blackOrWhite)
        {
            whiteTransitionUpperLimit=min(max_size , int(whiteTransitionUpperLimit));
            for (int i=real_size ; i<whiteTransitionUpperLimit ; i++)
            {
                *local_sorted_leds[i] = CHSV(0,0,intensity);
            }
        }
    }
    for (int pos=blackTransitionLowerLimit ; pos<=real_size ; pos++)
    {
        *local_sorted_leds[pos] = CHSV(pos * 160 / max_size + testColorChange, 255 , intensity);
    }
    //The moving limit:
    if(real_size<max_size)
    {
        *local_sorted_leds[white_dot_pos] = CHSV(0 , 0 , intensity);   
    }
    if(transition)
    {
        updateTransitionTimer();
    }
  
}
// draw()

void Power_bar::startTransition(int transitionTime , bool upOrDown , bool blackOrWhite)
{
    this->transition=true;
    this->transitionUp=upOrDown;
    this->transitionTime=transitionTime;
    this->timeSinceTransition=0;
    this->blackOrWhite=blackOrWhite;
    this->blackTransitionLowerLimit=0;

    if (!blackOrWhite)
    {
        if(!upOrDown)
        {
            Serial.println("                                                            power_bar  ==>       ( white transition ) ");
            whiteTransitionUpperLimit=0;
            transitionPositionCoef=0;
        } 
        else
        {
            Serial.println("                                                             ==>  power_bar     ( white transition ) ");
            whiteTransitionUpperLimit=max_size;
            transitionPositionCoef=0;
        }
    } 
    else 
    {
        if(!upOrDown)
        {
            Serial.println("                                                                power_bar  ==>       ( black  transition ) ");
            transitionPositionCoef=0;
            blackTransitionLowerLimit=0;
        } 
        else
        {
            Serial.println("                                                             ==>  power_bar     ( black  transition ) ");
            transitionPositionCoef=0;
            blackTransitionLowerLimit=max_size;
        }
    }
}
//stratTransition()

void Power_bar::resetTransition()
{
    transition=false;
    timeSinceTransition=0;
    transitionPositionCoef=0;
    blackTransitionLowerLimit=0;
    Serial.println("                                                                      |power_bar|    ");
}
//resetTransition()

void Power_bar::activate()
{
    this->activated=true;
}
