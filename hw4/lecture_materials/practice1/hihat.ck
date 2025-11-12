Noise n => HPF f => dac;
0.3 => n.gain;
8000 => f.freq;

0.25::second => dur step;

while (true) {
    0.4 => n.gain;
    40::ms => now;
    0.05 => n.gain;
    
    step => now;
}