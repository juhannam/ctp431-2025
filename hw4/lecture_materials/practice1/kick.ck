SinOsc kick => dac;
0.8 => kick.gain;

0.5::second => dur beat;

while (true) {
    // frequency sweep for punch
    120 => float startFreq;
    40 => float endFreq;
    
    for (0 => int i; i < 50; i++) {
        (startFreq - (startFreq - endFreq) * (i / 50.0)) => kick.freq;
        1::ms => now;
    }
    // short pause between hits
    beat => now;
}