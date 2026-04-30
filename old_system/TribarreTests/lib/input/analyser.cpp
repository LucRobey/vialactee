#include <analyser.h>

const int BUFFER_SIZE = 100;
char buf[BUFFER_SIZE];

Analyser::Analyser()
{
  sampling_period_us = round(1000000 * (1.0 / SAMPLING_FREQ));
  for (byte s=0 ; s<16 ; s++)
  {
    bandValues[s]=0;
    peakTime[s]=0;
    samplePeak[s]=0;

    bandMeans[s]=100;
    bandLocalMaxs[s]=100;
    bandGlobalMaxs[s]=100;
    bandSmoothedValues[s]=100;
    asservedBandPowers[s]=100;

    bandAnalyserNeeds[s]=false;
  }
  asservedPower=100;
  smoothedPower=100;
  globalMaxPower=100;
  localMaxPower=100;
  meanPower10sec=100;
  meanPower1min=100;

  amortissement[0]=1;
  amortissement[1]=1.3;
  amortissement[2]=0.95;
  amortissement[3]=0.9;
  amortissement[4]=0.8;
  amortissement[5]=0.9;
  amortissement[6]=1;
  amortissement[7]=1;
  amortissement[8]=1;
  amortissement[9]=1.3;
  amortissement[10]=0.95;
  amortissement[11]=0.9;
  amortissement[12]=0.8;
  amortissement[13]=0.9;
  amortissement[14]=1;
  amortissement[15]=1;

  analyserNeeds[0]=true;
  analyserNeeds[1]=true;
  analyserNeeds[2]=true;
  analyserNeeds[3]=false;

  sensitivity = 800;

}

void Analyser::analyse()
{
  if(analyserNeeds[0])
  {
    //Serial.println("On écoute");
    listen();
    if(analyserNeeds[1])
    {
      //Serial.print("On fait la FFT:");
      FFT_analyse();
      updateBandMeansAndSmoothedValues();
      if(analyserNeeds[2])
      {
        //Serial.println("On détecte les peaks");
        detectBeats();
      }
      if(analyserNeeds[3])
      {
        //Serial.println("On asserve les bandes");
        asservBandPowers();
      }
      if(analyserNeeds[4])
      {
        asservPower();
      }
    }
  }
}
//analyse()

void Analyser::listen()
{
  //Serial.print("temps d'écoute: ");
  //timeL=micros();
  for (int i = 0; i < SAMPLES; i++) 
  {
      newTime = micros();
      vReal[i] = analogRead(AUDIO_IN_PIN); // A conversion takes about 9.7uS on an ESP32
      vImag[i] = 0;
      while ((micros() - newTime) < sampling_period_us) { /* chill */ }
  }
  //Serial.println(micros()-timeL);
}
//listen()

void Analyser::FFT_analyse(){ 
  //Serial.print("Temps de FFT : ");
  //timeL=micros();
  // Reset bandValues[]
  for (int i = 0; i<16; i++){
    bandValues[i] = 0;
  }

  
    // Compute FFT
  FFT.DCRemoval();
  FFT.Windowing(FFT_WIN_TYP_HAMMING, FFT_FORWARD);
  FFT.Compute(FFT_FORWARD);
  FFT.ComplexToMagnitude();

  // Analyse FFT results
  for (int i = 2; i < (SAMPLES/2); i++){       // Don't use sample 0 and only first SAMPLES/2 are usable. Each array element represents a frequency bin and its value the amplitude.
    if (vReal[i] > NOISE) {                    // Add a crude noise filter

      //8 bands, 12kHz top band
      /*
      if      (i<=5  ) bandValues[0]  += (int)vReal[i];
      else if (i<=10  ) bandValues[1]  += (int)vReal[i];
      else if (i<=15 ) bandValues[2]  += (int)vReal[i];
      else if (i<=27 ) bandValues[3]  += (int)vReal[i];
      else if (i<=40 ) bandValues[4]  += (int)vReal[i];
      else if (i<=53) bandValues[5]  += (int)vReal[i];
      else if (i<=84) bandValues[6]  += (int)vReal[i];
      else if (i<=126) bandValues[7]  += (int)vReal[i];
      */

    //16 bands, 12kHz top band
      if      (i<=3  ) bandValues[0]  += (int)vReal[i]; //50
      else if (i<=4  ) bandValues[1]  += (int)vReal[i]; //100
      else if (i<=6  ) bandValues[2]  += (int)vReal[i]; //140
      else if (i<=8  ) bandValues[3]  += (int)vReal[i]; //200
      else if (i<=11 ) bandValues[4]  += (int)vReal[i]; //255
      else if (i<=14 ) bandValues[5]  += (int)vReal[i]; //310
      else if (i<=18 ) bandValues[6]  += (int)vReal[i]; //450
      else if (i<=23 ) bandValues[7]  += (int)vReal[i]; //600
      else if (i<=29 ) bandValues[8]  += (int)vReal[i]; //800
      else if (i<=36 ) bandValues[9]  += (int)vReal[i]; //1000
      else if (i<=45 ) bandValues[10] += (int)vReal[i]; //1400
      else if (i<=56 ) bandValues[11] += (int)vReal[i]; //1800
      else if (i<=69) bandValues[12] += (int)vReal[i]; //2700
      else if (i<=85) bandValues[13] += (int)vReal[i]; //3200
      else if (i<=104) bandValues[14] += (int)vReal[i]; //4000
      else if (i<=127) bandValues[15] += (int)vReal[i]; //7000-8000
    }
  }
  
  //Serial.println("7 eme bande : ");
  //Serial.println(bandValues[7]);
  /*
  for (int i=0; i<15 ; i++)
  {
    Serial.print(bandValues[i]);
    Serial.print(",");
  }
  Serial.println(bandValues[15]);
  delay(1);
  if(Serial.available())
  {
    int rlen = Serial.readBytesUntil('\n', buf, BUFFER_SIZE);

    // prints the received data
    Serial.print("RECU");
    for(int i = 0; i < rlen; i++)
      Serial.print(buf[i]);
      Serial.print(",");
  }
  
  for (int i=0 ; i<254 ; i++)
  {
    Serial.print(vReal[i]);
    Serial.print(",");
  }
  Serial.println(vReal[254]);
  delay(1);
  if(Serial.available())
  {
    int rlen = Serial.readBytesUntil('\n', buf, BUFFER_SIZE);

    // prints the received data
    Serial.print("RECU");
    for(int i = 0; i < rlen; i++)
      Serial.print(buf[i]);
      Serial.print(",");
  }
  Serial.println();
  */
  

}
//FFT_analyse()

void Analyser::amortiseBandValues()
{
  for (byte band=0 ; band<16 ; band++)
  {
    bandValues[band] *= amortissement[band];
  }
}
// ================================ amortiseBandValues()

void Analyser::updateBandMeansAndSmoothedValues()
{
  if(bandMeans[2]!=0)
  {
    for (byte band=0 ; band<16 ; band++)
    {
      bandSmoothedValues[band] = (2 * bandSmoothedValues[band] + bandValues[band]) / 3;
      bandMeans[band] += 0.01 * (bandSmoothedValues[band] - bandMeans[band]);
    }
  }
  else
  {
    for (byte band=0 ; band<16 ; band++)
    {
      bandValues[band]+=1;
      bandSmoothedValues[band] = bandValues[band];
      bandMeans[band] = bandSmoothedValues[band];
    }
  }
}
// ================================ updateBandMeansAndSmoothedValues()

void Analyser::asservBandPowers()
{
  for (byte band=0 ; band<16 ; band++)
  {
    //Serial.print("band = ");
    //Serial.println(band);
    if(bandAnalyserNeeds[band])
    {
      //Serial.println("  Il faut analyser cette band");

      //Serial.print("    bandSmoothedValues = ");
      //Serial.print(bandSmoothedValues[band]);
      //Serial.print("    bandLocalMaxs = ");
      //Serial.print(bandLocalMaxs[band]);
      //Serial.print("    bandGlobalMaxs = ");
      //Serial.println(bandGlobalMaxs[band]);
      if (bandSmoothedValues[band] > bandLocalMaxs[band])
      {
        bandLocalMaxs[band] = bandSmoothedValues[band]; 
      } 
      else
      {
        bandLocalMaxs[band]*=0.9995;
      }                                                 //Make it slowly decrease

      if (bandSmoothedValues[band] > bandGlobalMaxs[band])
      {
        bandGlobalMaxs[band] = 1.01 * bandSmoothedValues[band];
      }
      else
      {
        bandGlobalMaxs[band] *= 1 + 0.005 * ( (bandLocalMaxs[band]/bandGlobalMaxs[band]) - 0.9);
      }
      //Serial.print("    bandSmoothedValues = ");
      //Serial.print(bandSmoothedValues[band]);
      //Serial.print("    bandLocalMaxs = ");
      //Serial.print(bandLocalMaxs[band]);
      //Serial.print("    bandGlobalMaxs = ");
      //Serial.println(bandGlobalMaxs[band]);
      asservedBandPowers[band] += 0.4 *  (255 * bandSmoothedValues[band]/bandGlobalMaxs[band] - asservedBandPowers[band]);
    }
  }
  //Serial.println("C FINI");
}
// ================================ asservBandPowers()

void Analyser::detectBeats()
{
  //Serial.print(" Analyser samplePeak = { ");
  total=0;
  for (byte band=0 ; band<16 ; band++)
  {
      if (bandValues[band] > bandMeans[band] + sensitivity  && millis() > peakTime[band] + 150)
      {                 //Si la valeur dépasse la moyenne de plus d'une valeur sensible,
                        //et si il n'y a pas eu de peaks dans les derniers 100 mils, il y a peak
        samplePeak[band]=1;
        total+= 1;
        peakTime[band]=millis();
      }
      else 
      { 
        samplePeak[band]=0;
      }
      //Serial.print(samplePeak[band]);
      //Serial.print(" , ");
  }  
  sensitivity*= 1+(total-1)*0.00010;
  //if (total>2){ sensitivity*=1.00015;}                                                                         //On met à jour la sensibilité
  //if (total<1){ sensitivity*=0.99999;}
  //Serial.println("} ");
}
// ================================ detectBeats()

void Analyser::asservPower()
{
  instantPower = 0;
  for (byte band=0 ; band<16 ; band++)
  {
    instantPower+= bandValues[band];
  }
  meanPower10sec += 0.01 * (instantPower - meanPower10sec);
  meanPower1min += 0.0017 * (instantPower - meanPower1min);

  smoothedPower = 0.5 * (smoothedPower + instantPower);

  if (smoothedPower > localMaxPower)
  {
    localMaxPower = smoothedPower; 
  } 
  else
  {
    localMaxPower*=0.9998;
  }                                                 //Make it slowly decrease

  if (smoothedPower > globalMaxPower)
  {
    globalMaxPower = 1.01 * smoothedPower;
  }
  else
  {
    globalMaxPower *= 1 + 0.005 * ( (localMaxPower/globalMaxPower) - 0.9);
  }

  asservedPower += 0.4 *  (255 * smoothedPower/globalMaxPower - asservedPower);
  /*
  Serial.print("smoothedPower = ");
  Serial.println(smoothedPower);
  Serial.print("localMaxPower = ");
  Serial.println(localMaxPower);
  Serial.print("globalMaxPower = ");
  Serial.println(globalMaxPower);
  Serial.print("asservedPower = ");
  Serial.println(asservedPower);
  */


}
// ================================ asservPower()

double* Analyser::getFFTValues()
{
  return vReal;
}

int* Analyser::get_bandValues()
{
    return bandValues;
}
//get_bandValues()

int* Analyser::getSmoothedBandValues()
{
    return bandSmoothedValues;
}
//getSmoothedBandValues()

byte* Analyser::get_samplePeak()
{
  return samplePeak;
}
//get_bandValues()

bool* Analyser::getAnalyserNeeds()
{
    return analyserNeeds;
}
//getAnalyserNeeds()

bool* Analyser::getBandAnalyserNeeds()
{
    return bandAnalyserNeeds;
}
//getAnalyserNeeds()

int* Analyser::get_bandSmoothedValues()
{
  return bandSmoothedValues;
}
int* Analyser::get_bandLocalMaxs()
{
  return bandLocalMaxs;
}
int* Analyser::get_bandGlobalMaxs()
{
  return bandGlobalMaxs;
}
byte* Analyser::getAsservedBandPowers()
{
  return asservedBandPowers;
}
byte* Analyser::getAsservedPower()
{
  return &asservedPower;
}

