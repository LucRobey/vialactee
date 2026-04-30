#include <mode_shining_stars.h>

Mode_shining_stars::Mode_shining_stars(vector<CRGB*> local_sorted_leds,byte ID, byte* samplePeak ,  byte* asservedPower)
{
    initiateVariables(ID,local_sorted_leds);

    this->fadeToBlackInt=20;
    
    segment_division_size=35; 
    this->segment_division_number = listSize/segment_division_size;
    this->rests=listSize%segment_division_size;

    //Construction de la permutation
    bool hasAlreadyBeenPlaced;
    int randPos;
    while(permutationForWhiteTransition.size()<listSize)
    {
        hasAlreadyBeenPlaced=false;
        randPos = random8()%listSize;
        for(int s=0 ; s<permutationForWhiteTransition.size() ; s++)
        {
            if (permutationForWhiteTransition[s]==randPos)
            {
                hasAlreadyBeenPlaced=true;
                break;
            }
        }
        if(!hasAlreadyBeenPlaced)
        {
            permutationForWhiteTransition.push_back(randPos);
        }
    }

    //Data
    this->samplePeak=samplePeak;
    this->asservedPower=asservedPower;

    this->analysingNeeds[0] = true;         //Ecoute
    this->analysingNeeds[1] = true;         //FFT
    this->analysingNeeds[2] = true;        //Peaks
    this->analysingNeeds[3] = false;         //asservBands
    this->analysingNeeds[4] = true;         //Power
    for (byte band=0 ; band<16 ; band++)
    {
        this->bandAnalysingNeeds[band]=false;
    }
    
};

void Mode_shining_stars::update()
{
    //Serial.print("Temps de calcul pour Shining star de taille ");
    //Serial.print(listSize);
    //Serial.print(" : ");
    //timeL=micros();
    total=0;
    for (byte s=0 ; s<16 ; s++)
    {
        total += samplePeak[s];                  //total de bandes actruellement en peak
    }
    
    if (transition)
    {
        if (blackOrWhite)
        { // Black transition
            if (!transitionUp)
            {                                                                                            // fin de vie
                fadeToBlackInt = 10 + float(10 * timeSinceTransition) / transitionTime;            // On augmente le fadeToBlack
                black_power_coef = float(transitionTime - timeSinceTransition) / transitionTime; // On diminue la luminosité
            }
            else
            {                                                                                 // Debut de vie
                fadeToBlackInt = 20 - float(10 * timeSinceTransition) / transitionTime; // On diminue le fadeToBlack
                black_power_coef = float(timeSinceTransition) / transitionTime;         // On augmente la luminosité
            }
        }
    }
}
// Update()

// Puissance de la lumière
void Mode_shining_stars::draw()
{
    // fadeToBlackBy(leds, 269, 10);
    powerSS= (float(total)/15) * 0.5*(255+(*asservedPower));

    
    if(transition && blackOrWhite)
    {
        powerSS*=black_power_coef;
    }
    //powerSS = black_power_coef * min(140, int(140.0 * float(total) / 2.5)); // Apres observation, en moyenne on a 2 peaks d'activés et 3 parfois || Le coef sert à la black Transition
                                                                              // On divise donc par 2.5 pour ramener cette valeur entre 0 et 255 environ
    // if (!transitionSS){
    
    //} else {

    if( ! (transition && !blackOrWhite))
    {
        for (byte band = 0; band < 16; band++)
        {
            if (samplePeak[band] > 0.5)
            {
                posSS = random8() % segment_division_size; // On fait apparaître une lumière, a la couleur de la bande, à la puissance
                                                //  adaptée.
                for (int j=0 ; j<segment_division_number ; j++)
                {//On copie ce qui se passe sur les segment_division_size premières LEDs histoire de limiter le nb de calculs
                    *local_sorted_leds[posSS + segment_division_size*j] = CHSV(11 * band, 255 , powerSS);
                }
                if (posSS<rests)
                {// On colorie les LEDs qui restent si segment_division_size ne divise le nb de leds du segment
                    *local_sorted_leds[segment_division_size*segment_division_number+posSS] = CHSV(11 * band, 255, powerSS);
                }
            }
        }
    }
    else
    {
        for (byte band = 0; band < 16; band++)
        {
            if (samplePeak[band] > 0.5)
            {
                posSS = random8() % segment_division_size; // On fait apparaître une lumière, a la couleur de la bande, à la puissance
                                                //  adaptée.
                for (int j=0 ; j<segment_division_number ; j++)
                {//On copie ce qui se passe sur les segment_division_size premières LEDs histoire de limiter le nb de calculs
                    if( (*local_sorted_leds[posSS+ segment_division_size*j]).red!=255)
                    {
                        *local_sorted_leds[posSS + segment_division_size*j] = CHSV(11 * band, 255 , powerSS);
                    }
                }
                if (posSS<rests)
                {// On colorie les LEDs qui restent si segment_division_size ne divise le nb de leds du segment
                    if( (*local_sorted_leds[segment_division_size*segment_division_number+posSS]).red!=255)
                    {
                        *local_sorted_leds[segment_division_size*segment_division_number+posSS] = CHSV(11 * band, 255 , powerSS);
                    }
                }
            }
        }
        if(!transitionUp)
        {
            whiteTransitionCounter = float(listSize*timeSinceTransition)/(0.9*transitionTime);
            if(whiteTransitionCounter>listSize)
            {
                whiteTransitionCounter=listSize;
            }
            for (int j=0 ; j<whiteTransitionCounter ; j++)
            {
                *local_sorted_leds[permutationForWhiteTransition[j]]=CHSV(0,0,255);
            }

        }
        else
        {
            whiteTransitionCounter = float(listSize*timeSinceTransition)/(0.9*transitionTime);
            if(whiteTransitionCounter>listSize)
            {
                whiteTransitionCounter=listSize;
            }
            for (int j=whiteTransitionCounter ; j<listSize ; j++)
            {
                *local_sorted_leds[permutationForWhiteTransition[j]]=CHSV(0,0,255);
            }
        }
    }  
    if (transition)
    {
        updateTransitionTimer();
    }
    //Serial.println(micros()-timeL);
}
// draw()

void Mode_shining_stars::startTransition(int transitionTime, bool upOrDown, bool blackOrWhite)
{
    this->transition = true;
    this->transitionUp = upOrDown;
    this->transitionTime = transitionTime;
    this->timeSinceTransition = 0;
    this->blackOrWhite = false;
    if (!this->blackOrWhite)
    {//white
        if (!upOrDown)
        {//fin de vie
            Serial.println("                                                              mode_shining_star  ==>       ( white transition ) ");
        }
        else
        {//debut de vie
            Serial.println("                                                              ==>  mode_shining_star     ( white transition ) ");
        }
    }
    else
    {//black
        if (!upOrDown)
        {//fin de vie
            Serial.println("                                                             mode_shining_star  ==>       ( black  transition ) ");
            fadeToBlackInt = 10;
            black_power_coef = 1;
        }
        else
        {//debut de vie
            Serial.println("                                                              ==>  mode_shining_star     ( black  transition ) ");
            fadeToBlackInt = 20;
            black_power_coef = 0;
        }
    }
}
// startTransition


void Mode_shining_stars::resetTransition()
{ // Reset toutes les variables si on appuie sur le bouton au milieu d'une transition
    black_power_coef = 1;             // Pour la black Transition, contrôle la puissance
    fadeToBlackInt = 20;              // Pour la white transition, on joue sur le fadeToBlack
    transition = false;
    timeSinceTransition = 0;
    Serial.println("                                                                |shining_star|    ");
}
// resetTransition()

void Mode_shining_stars::activate()
{
    this->activated=true;
}
