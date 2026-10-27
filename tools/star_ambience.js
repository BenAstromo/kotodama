// Star ambiences for Amaterasu mode, from the Sun's p-mode spectrum sped up
// ~36,000×: nu_max 3.09 mHz → 110 Hz, large separation 134.9 µHz → 4.80 Hz,
// l=1 modes halfway between, l=2 modes 0.32 Hz below l=0 (small separation).
// Loops: every frequency and LFO completes whole cycles in the loop length,
// and the noise is filtered circularly, so the end meets the start exactly.
const fs = require("fs");
const SR = 44100;
const out = process.argv[2];

let seed = 12345;
const rnd = () => ((seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296);

function q(f, L) { return Math.round(f * L) / L; }           // whole cycles in L

function modes() {
  const NU = 110, DNU = 4.80, D02 = 0.32, list = [];
  for (let n = -4; n <= 3; n++) {
    const f0 = NU + n * DNU;
    const g = Math.exp(-0.5 * (n / 2.4) ** 2);               // Gaussian around nu_max
    list.push({ f: f0, a: g });                              // l = 0
    list.push({ f: f0 + DNU / 2, a: g * 0.85 });             // l = 1
    list.push({ f: f0 - D02, a: g * 0.55 });                 // l = 2 (beats with l = 0)
  }
  return list.filter(m => m.f >= 88 && m.f <= 125);
}

// Slow random envelope (stochastic excitation): whole cycles in L.
function envMaker(L, speed) {
  const parts = [1, 2, 3].map(() => ({ c: Math.max(1, Math.round((1 + rnd() * 5) * speed)), p: rnd() * 6.283 }));
  return t => {
    let s = 0;
    for (const { c, p } of parts) s += Math.sin(6.283185307 * c * t / L + p);
    return (0.5 + 0.5 * s / 3) ** 2;
  };
}

function noiseBand(n, lo, hi) {
  // white noise → two 1-pole HP + LP passes, run twice around the buffer
  // (circular), so the loop has no seam
  const x = new Float32Array(n);
  for (let i = 0; i < n; i++) x[i] = rnd() * 2 - 1;
  const lp = (b, fc) => { const a = Math.exp(-2 * Math.PI * fc / SR); let y = 0;
    for (let k = 0; k < 2; k++) for (let i = 0; i < n; i++) { y = (1 - a) * b[i] + a * y; if (k) b[i] = y; } };
  const hp = (b, fc) => { const c = Float32Array.from(b); lp(c, fc); for (let i = 0; i < n; i++) b[i] -= c[i]; };
  for (let k = 0; k < 2; k++) { lp(x, hi); hp(x, lo); }
  let m = 0; for (const v of x) m = Math.max(m, Math.abs(v));
  for (let i = 0; i < n; i++) x[i] /= m;
  return x;
}

function writeWav(name, L, R, peakDb) {
  const n = L.length;
  let m = 0;
  for (let i = 0; i < n; i++) m = Math.max(m, Math.abs(L[i]), Math.abs(R[i]));
  const g = Math.pow(10, peakDb / 20) / m;
  const buf = Buffer.alloc(44 + n * 4);
  buf.write("RIFF", 0); buf.writeUInt32LE(36 + n * 4, 4); buf.write("WAVEfmt ", 8);
  buf.writeUInt32LE(16, 16); buf.writeUInt16LE(1, 20); buf.writeUInt16LE(2, 22);
  buf.writeUInt32LE(SR, 24); buf.writeUInt32LE(SR * 4, 28); buf.writeUInt16LE(4, 32);
  buf.writeUInt16LE(16, 34); buf.write("data", 36); buf.writeUInt32LE(n * 4, 40);
  let rms = 0;
  for (let i = 0; i < n; i++) {
    const l = L[i] * g, r = R[i] * g; rms += l * l + r * r;
    buf.writeInt16LE(Math.round(l * 32767), 44 + i * 4);
    buf.writeInt16LE(Math.round(r * 32767), 46 + i * 4);
  }
  fs.writeFileSync(`${out}/${name}.wav`, buf);
  console.log(name, `peak ${peakDb} dBFS, rms ${(10 * Math.log10(rms / (2 * n))).toFixed(1)} dBFS`);
}

// Bank of modes with stochastic envelopes, harmonics for small speakers,
// a faint high "shimmer" copy, stereo spread. brightness 0..1.
function modeBank(Lsec, n, opts) {
  const L = new Float32Array(n), R = new Float32Array(n);
  for (const m of modes()) {
    const pan = 0.5 + (rnd() - 0.5) * 0.8;
    const env = envMaker(Lsec, opts.speed);
    const layers = [[1, 1], [2, 0.35 * opts.bright], [3, 0.12 * opts.bright], [8, 0.05 * opts.shimmer]];
    for (const [h, a] of layers) {
      if (!a) continue;
      const f = q(m.f * h, Lsec), ph = rnd() * 6.283, w = 6.283185307 * f / SR;
      const amp = m.a * a / Math.sqrt(h);
      const tw = h === 8 ? envMaker(Lsec, opts.speed * 3) : null;   // shimmer twinkles
      for (let i = 0; i < n; i++) {
        const t = i / SR;
        const v = Math.sin(w * i + ph) * amp * env(t) * (tw ? tw(t) : 1);
        L[i] += v * (1 - pan); R[i] += v * pan;
      }
    }
  }
  return [L, R];
}

function addGas(L, R, Lsec, lo, hi, amt) {
  const n = L.length, nl = noiseBand(n, lo, hi), nr = noiseBand(n, lo, hi), env = envMaker(Lsec, 1);
  for (let i = 0; i < n; i++) { const e = amt * (0.4 + env(i / SR)); L[i] += nl[i] * e; R[i] += nr[i] * e; }
}

// ── 1. Protostar heartbeat (owner 2026-10-16): one colossal beat per loop,
//      layered over the Ringing Sun. 15 bpm (PERIOD 4 s), pitched far down
//      (lub 55 → 33 Hz, dub 48 → 30 Hz) with slow attacks and a long rumbling
//      tail, overtones so small speakers still hear it. Rendered circularly
//      (the tail wraps into the start) so the 4 s loop has no seam; the beat
//      is at 0 s, so starting the loop = a beat.
{
  const PERIOD = 4.0, n = Math.round(PERIOD * SR);
  const L = new Float32Array(n), R = new Float32Array(n);
  const rumL = noiseBand(n, 20, 90), rumR = noiseBand(n, 20, 90), thud = noiseBand(n, 30, 180);
  const thump = (t0, f1, f2, a) => {
    for (let k = 0; k < n; k++) {
      const t = k / SR, i = (Math.round(t0 * SR) + k) % n;
      const ph = 6.283185307 * (f2 * t + (f1 - f2) * 0.15 * (1 - Math.exp(-t / 0.15)));
      const body = a * Math.min(1, t / 0.025) * Math.exp(-t / 0.45);
      const v = body * (Math.sin(ph) + 0.4 * Math.sin(2 * ph) + 0.15 * Math.sin(3 * ph))
              + a * 0.35 * Math.min(1, t / 0.02) * Math.exp(-t / 0.3) * thud[k];
      const tail = a * 0.3 * Math.min(1, t / 0.08) * Math.exp(-t / 1.2);
      L[i] += v + tail * rumL[k]; R[i] += v + tail * rumR[k];
    }
  };
  thump(0, 55, 33, 1.0);          // lub
  thump(0.75, 48, 30, 0.7);       // dub
  writeWav("1_protostar_heartbeat_loop", L, R, -16);
}

// ── 2. Ignition (one-shot, synced to the 7.5 s ascension intro): the
//      heartbeat quickens into a flutter while pitch climbs 90 → 123 Hz,
//      and at 0.55 s (her light blooms / the flash peaks) the whole mode
//      bank is struck like a bell and rings out into the Ringing Sun ──
{
  const Ls = 8, n = Ls * SR, HIT = 0.55;
  const L = new Float32Array(n), R = new Float32Array(n);
  // accelerating flutter before ignition
  let ph = 0, gph = 0;
  for (let i = 0; i < HIT * SR; i++) {
    const t = i / SR, k = t / HIT;
    const f = 90 + 33 * k * k, rate = 3 + 37 * k * k;     // pulses/s: 3 → 40
    ph += 6.283185307 * f / SR;
    gph += rate / SR;
    const gate = Math.pow(0.5 + 0.5 * Math.cos(6.283185307 * gph), 3);
    const v = (0.15 + 0.85 * k) * gate * (Math.sin(ph) + 0.4 * Math.sin(2 * ph));
    L[i] += v * 0.8; R[i] += v * 0.8;
  }
  // the strike: every mode + inharmonic bell partials, swelling then ringing
  for (const m of modes()) {
    const pan = 0.5 + (rnd() - 0.5) * 0.9;
    for (const [h, a, d] of [[1, 1, 3.5], [2, 0.5, 2.2], [2.76, 0.35, 1.6], [5.4, 0.18, 1.0], [8.93, 0.08, 0.7]]) {
      const f = m.f * h, p = rnd() * 6.283;
      for (let i = Math.floor(HIT * SR); i < n; i++) {
        const t = i / SR - HIT;
        const e = m.a * a * Math.min(1, t / 0.04) * Math.exp(-t / d);
        const v = e * Math.sin(6.283185307 * f * t + p);
        L[i] += v * (1 - pan); R[i] += v * pan;
      }
    }
  }
  // a breath of gas swelling into the hit
  const nz = noiseBand(n, 80, 2500);
  for (let i = 0; i < n; i++) {
    const t = i / SR, e = 0.5 * Math.exp(-0.5 * ((t - HIT) / 0.18) ** 2);
    L[i] += nz[i] * e; R[i] += nz[(i + 999) % n] * e;
  }
  // fade the tail so the Ringing Sun loop can take over
  for (let i = 0; i < n; i++) { const t = i / SR; if (t > 6) { const g = Math.cos((t - 6) / 2 * Math.PI / 2); L[i] *= g; R[i] *= g; } }
  writeWav("2_ignition_oneshot", L, R, -14);
}

// ── 3. Ringing Sun: the steady Amaterasu-mode ambience ──
{
  const Ls = 60, n = Ls * SR;
  const [L, R] = modeBank(Ls, n, { speed: 1, bright: 1, shimmer: 1 });
  addGas(L, R, Ls, 60, 900, 0.12);
  writeWav("3_ringing_sun_loop", L, R, -18);
}
