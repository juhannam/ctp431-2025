// melodyline.ck — simple random melody generator
SinOsc osc => ADSR env => NRev rev => dac;

(5::ms, 100::ms, 0.4, 100::ms) => env.set;
0.15 => osc.gain;
0.1 => rev.mix;

60 => int root;
[0,2,4,5,7,9,11,12] @=> int scale[];
0.5::second => dur beat;

while (true) {
    scale[Math.random2(0, scale.cap()-1)] + root => int note;
    Std.mtof(note) => osc.freq;
    1 => env.keyOn;
    beat * Math.random2f(0.5, 1.0) => now;
    1 => env.keyOff;
}
