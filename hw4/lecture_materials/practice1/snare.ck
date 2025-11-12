Noise n => BPF f => dac;
0.4 => n.gain;
2000 => f.freq;
2.0 => f.Q; // controls brightness

0.5::second => dur beat;

while (true) {
    0.7 => n.gain;
    50::ms => now;
    0.1 => n.gain;
    
    // wait for next hit (every 2 beats)
    beat * 2 => now;
}