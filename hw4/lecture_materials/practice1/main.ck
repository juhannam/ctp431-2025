// main.ck — combines melody + synthesized drums
me.dir() => string base;

base + "kick.ck" => string kickFile;
base + "snare.ck" => string snareFile;
base + "hihat.ck" => string hatFile;
base + "melodyline.ck" => string melodyFile;

Machine.add(kickFile) => int kickID;
Machine.add(snareFile) => int snareID;
Machine.add(hatFile)   => int hatID;
Machine.add(melodyFile) => int melodyID;

// let the loop play for a while
8::second => now;

// clean up
Machine.remove(kickID);
Machine.remove(snareID);
Machine.remove(hatID);
Machine.remove(melodyID);
