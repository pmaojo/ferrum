import { useCallback, useRef } from 'react';

interface FMSoundsHook {
  playBoot: () => void;
  playGlitch: () => void;
  playHover: () => void;
  playNodeCreate: () => void;
  playConnection: () => void;
  playValidation: () => void;
  playMatrixGlitch: () => void;
  playDeepBass: () => void;
  playHackerSequence: () => void;
  playQuantumResonance: () => void;
  playTerminalBoot: () => void;
  playDataStream: () => void;
}

export const useFMSounds = (defaultVolume: number = 0.8): FMSoundsHook => {
  const audioContextRef = useRef<AudioContext | null>(null);

  const getAudioContext = useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext ||
        (window as any).webkitAudioContext)();
    }
    return audioContextRef.current;
  }, []);

  // Enhanced FM synthesis with multiple operators and advanced routing
  const playAdvancedFM = useCallback(
    (config: {
      carriers: { freq: number; type?: OscillatorType }[];
      modulators: { freq: number; depth: number; type?: OscillatorType }[];
      duration: number;
      envelope?: {
        attack?: number;
        decay?: number;
        sustain?: number;
        release?: number;
      };
      filter?: { freq: number; type?: BiquadFilterType; sweep?: boolean };
      volume?: number;
      stereo?: boolean;
      reverb?: boolean;
    }) => {
      const audioContext = getAudioContext();
      const {
        carriers,
        modulators,
        duration,
        envelope = { attack: 0.01, decay: 0.1, sustain: 0.7, release: 0.2 },
        filter,
        volume = defaultVolume,
        stereo = false,
        reverb = false,
      } = config;

      const now = audioContext.currentTime;

      // Create oscillators and gains
      const carrierNodes = carriers.map((c) => {
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        osc.type = c.type || 'sine';
        osc.frequency.value = c.freq;
        osc.connect(gain);
        return { osc, gain };
      });

      const modulatorNodes = modulators.map((m, i) => {
        const osc = audioContext.createOscillator();
        const gain = audioContext.createGain();
        osc.type = m.type || 'sine';
        osc.frequency.value = m.freq;
        gain.gain.value = m.depth;
        osc.connect(gain);

        // Connect to carrier frequencies for FM
        if (carrierNodes[i % carrierNodes.length]) {
          gain.connect(carrierNodes[i % carrierNodes.length].osc.frequency);
        }

        return { osc, gain };
      });

      // Master gain and effects chain
      const masterGain = audioContext.createGain();
      let outputNode: AudioNode = masterGain;

      // Filter
      if (filter) {
        const filterNode = audioContext.createBiquadFilter();
        filterNode.type = filter.type || 'lowpass';
        filterNode.frequency.value = filter.freq;

        if (filter.sweep) {
          filterNode.frequency.exponentialRampToValueAtTime(
            filter.freq * 0.3,
            now + duration * 0.8
          );
        }

        masterGain.connect(filterNode);
        outputNode = filterNode;
      }

      // Reverb (convolution reverb simulation)
      if (reverb) {
        const delay1 = audioContext.createDelay();
        const delay2 = audioContext.createDelay();
        const delay3 = audioContext.createDelay();
        const reverbGain = audioContext.createGain();

        delay1.delayTime.value = 0.03;
        delay2.delayTime.value = 0.07;
        delay3.delayTime.value = 0.11;
        reverbGain.gain.value = 0.3;

        outputNode.connect(delay1);
        outputNode.connect(delay2);
        outputNode.connect(delay3);

        delay1.connect(reverbGain);
        delay2.connect(reverbGain);
        delay3.connect(reverbGain);

        reverbGain.connect(audioContext.destination);
      }

      // Stereo panning
      if (stereo) {
        const panner = audioContext.createStereoPanner();
        panner.pan.value = Math.random() * 2 - 1; // Random pan
        outputNode.connect(panner);
        panner.connect(audioContext.destination);
      } else {
        outputNode.connect(audioContext.destination);
      }

      // Connect carriers to master
      carrierNodes.forEach((node) => node.gain.connect(masterGain));

      // ADSR envelope
      masterGain.gain.setValueAtTime(0, now);
      masterGain.gain.linearRampToValueAtTime(volume, now + envelope.attack!);
      masterGain.gain.linearRampToValueAtTime(
        volume * envelope.sustain!,
        now + envelope.attack! + envelope.decay!
      );
      masterGain.gain.setValueAtTime(
        volume * envelope.sustain!,
        now + duration - envelope.release!
      );
      masterGain.gain.linearRampToValueAtTime(0, now + duration);

      // Start all oscillators
      [...carrierNodes, ...modulatorNodes].forEach((node) => {
        node.osc.start(now);
        node.osc.stop(now + duration);
      });
    },
    [getAudioContext, defaultVolume]
  );

  // Original enhanced sounds
  const playFMSound = useCallback(
    (config: {
      carrierFreq: number;
      modulatorFreq: number;
      modulationIndex: number;
      duration: number;
      attack?: number;
      decay?: number;
      sustain?: number;
      release?: number;
      volume?: number;
    }) => {
      const audioContext = getAudioContext();
      const {
        carrierFreq,
        modulatorFreq,
        modulationIndex,
        duration,
        attack = 0.01,
        decay = 0.1,
        sustain = 0.7,
        release = 0.2,
        volume = defaultVolume,
      } = config;

      const carrier = audioContext.createOscillator();
      const modulator = audioContext.createOscillator();
      const modulatorGain = audioContext.createGain();
      const outputGain = audioContext.createGain();

      modulator.frequency.value = modulatorFreq;
      modulatorGain.gain.value = modulationIndex;
      carrier.frequency.value = carrierFreq;

      modulator.connect(modulatorGain);
      modulatorGain.connect(carrier.frequency);
      carrier.connect(outputGain);
      outputGain.connect(audioContext.destination);

      const now = audioContext.currentTime;
      outputGain.gain.setValueAtTime(0, now);
      outputGain.gain.linearRampToValueAtTime(volume, now + attack);
      outputGain.gain.linearRampToValueAtTime(
        volume * sustain,
        now + attack + decay
      );
      outputGain.gain.setValueAtTime(
        volume * sustain,
        now + duration - release
      );
      outputGain.gain.linearRampToValueAtTime(0, now + duration);

      carrier.start(now);
      modulator.start(now);
      carrier.stop(now + duration);
      modulator.stop(now + duration);
    },
    [getAudioContext, defaultVolume]
  );

  // Original sounds (preserved)
  const playBoot = useCallback(() => {
    const baseFreq = 220 + Math.random() * 100;
    playFMSound({
      carrierFreq: baseFreq,
      modulatorFreq: baseFreq * (0.5 + Math.random() * 0.5),
      modulationIndex: 50 + Math.random() * 100,
      duration: 1.5 + Math.random() * 0.5,
      attack: 0.1,
      decay: 0.3,
      sustain: 0.6,
      release: 0.8,
      volume: defaultVolume * 0.7,
    });
  }, [playFMSound, defaultVolume]);

  const playGlitch = useCallback(() => {
    const freq = 800 + Math.random() * 1200;
    playFMSound({
      carrierFreq: freq,
      modulatorFreq: freq * (2 + Math.random() * 8),
      modulationIndex: 200 + Math.random() * 300,
      duration: 0.1 + Math.random() * 0.1,
      attack: 0.001,
      decay: 0.02,
      sustain: 0.3,
      release: 0.05,
      volume: defaultVolume * 0.5,
    });
  }, [playFMSound, defaultVolume]);

  const playHover = useCallback(() => {
    const freq = 440 + Math.random() * 220;
    playFMSound({
      carrierFreq: freq,
      modulatorFreq: freq * (1.1 + Math.random() * 0.3),
      modulationIndex: 10 + Math.random() * 20,
      duration: 0.15,
      attack: 0.01,
      decay: 0.05,
      sustain: 0.8,
      release: 0.09,
      volume: defaultVolume * 0.3,
    });
  }, [playFMSound, defaultVolume]);

  const playNodeCreate = useCallback(() => {
    const freq = 523.25; // C5
    playFMSound({
      carrierFreq: freq,
      modulatorFreq: freq * 2,
      modulationIndex: 30 + Math.random() * 20,
      duration: 0.4,
      attack: 0.02,
      decay: 0.1,
      sustain: 0.7,
      release: 0.25,
      volume: defaultVolume * 0.6,
    });
  }, [playFMSound, defaultVolume]);

  const playConnection = useCallback(() => {
    const freq = 659.25; // E5
    playFMSound({
      carrierFreq: freq,
      modulatorFreq: freq * 1.2, // Less modulation
      modulationIndex: 10 + Math.random() * 8, // Reduced modulation depth
      duration: 0.15, // Shorter duration
      attack: 0.005, // Quicker attack
      decay: 0.04, // Faster decay
      sustain: 0.4, // Lower sustain
      release: 0.1, // Quicker release
      volume: defaultVolume * 0.25, // Much quieter
    });
  }, [playFMSound, defaultVolume]);

  const playValidation = useCallback(() => {
    const success = Math.random() > 0.5;
    const baseFreq = success ? 783.99 : 369.99; // G5 for success, F#4 for warning
    playFMSound({
      carrierFreq: baseFreq,
      modulatorFreq: baseFreq * (success ? 1.25 : 0.75),
      modulationIndex: success ? 20 : 40,
      duration: 0.5,
      attack: 0.02,
      decay: 0.1,
      sustain: 0.8,
      release: 0.35,
      volume: defaultVolume * 0.4,
    });
  }, [playFMSound, defaultVolume]);

  // NEW ENHANCED SOUNDS
  const playMatrixGlitch = useCallback(() => {
    playAdvancedFM({
      carriers: [
        { freq: 880, type: 'square' },
        { freq: 1320, type: 'sawtooth' },
        { freq: 440, type: 'triangle' },
      ],
      modulators: [
        { freq: 200, depth: 300, type: 'square' },
        { freq: 150, depth: 400, type: 'sawtooth' },
        { freq: 100, depth: 250, type: 'triangle' },
      ],
      duration: 0.2,
      envelope: { attack: 0.001, decay: 0.05, sustain: 0.3, release: 0.1 },
      filter: { freq: 2000, type: 'highpass', sweep: true },
      stereo: true,
      volume: defaultVolume * 0.6,
    });
  }, [playAdvancedFM, defaultVolume]);

  const playDeepBass = useCallback(() => {
    playAdvancedFM({
      carriers: [
        { freq: 55, type: 'sine' },
        { freq: 110, type: 'triangle' },
      ],
      modulators: [
        { freq: 27.5, depth: 50, type: 'sine' },
        { freq: 41.25, depth: 75, type: 'triangle' },
      ],
      duration: 1.0,
      envelope: { attack: 0.1, decay: 0.3, sustain: 0.8, release: 0.6 },
      filter: { freq: 200, type: 'lowpass' },
      reverb: true,
      volume: defaultVolume * 0.8,
    });
  }, [playAdvancedFM, defaultVolume]);

  const playHackerSequence = useCallback(() => {
    // Sequence of ascending tones with complex modulation
    [0, 0.1, 0.2, 0.3].forEach((delay, i) => {
      setTimeout(() => {
        playAdvancedFM({
          carriers: [{ freq: 440 * Math.pow(1.5, i), type: 'square' }],
          modulators: [
            {
              freq: 220 * Math.pow(1.2, i),
              depth: 100 + i * 50,
              type: 'sawtooth',
            },
          ],
          duration: 0.2,
          envelope: { attack: 0.01, decay: 0.05, sustain: 0.7, release: 0.15 },
          filter: { freq: 1000 + i * 500, type: 'bandpass' },
          stereo: true,
          volume: defaultVolume * 0.4,
        });
      }, delay * 1000);
    });
  }, [playAdvancedFM, defaultVolume]);

  const playQuantumResonance = useCallback(() => {
    playAdvancedFM({
      carriers: [
        { freq: 261.63, type: 'sine' }, // C4
        { freq: 329.63, type: 'sine' }, // E4
        { freq: 392.0, type: 'sine' }, // G4
      ],
      modulators: [
        { freq: 130.81, depth: 20, type: 'sine' },
        { freq: 164.81, depth: 25, type: 'sine' },
        { freq: 196.0, depth: 30, type: 'sine' },
      ],
      duration: 2.0,
      envelope: { attack: 0.2, decay: 0.5, sustain: 0.6, release: 1.3 },
      filter: { freq: 800, type: 'lowpass', sweep: true },
      reverb: true,
      stereo: true,
      volume: defaultVolume * 0.5,
    });
  }, [playAdvancedFM, defaultVolume]);

  const playTerminalBoot = useCallback(() => {
    playAdvancedFM({
      carriers: [
        { freq: 80, type: 'square' },
        { freq: 160, type: 'sawtooth' },
        { freq: 320, type: 'triangle' },
      ],
      modulators: [
        { freq: 40, depth: 100, type: 'sine' },
        { freq: 80, depth: 150, type: 'square' },
      ],
      duration: 1.5,
      envelope: { attack: 0.1, decay: 0.4, sustain: 0.7, release: 1.0 },
      filter: { freq: 1200, type: 'lowpass', sweep: true },
      reverb: true,
      volume: defaultVolume * 0.7,
    });
  }, [playAdvancedFM, defaultVolume]);

  const playDataStream = useCallback(() => {
    // Rapid-fire data transmission sound
    for (let i = 0; i < 8; i++) {
      setTimeout(() => {
        playAdvancedFM({
          carriers: [{ freq: 1000 + Math.random() * 2000, type: 'square' }],
          modulators: [
            { freq: 500 + Math.random() * 1000, depth: 200, type: 'sawtooth' },
          ],
          duration: 0.05,
          envelope: { attack: 0.001, decay: 0.01, sustain: 0.5, release: 0.04 },
          filter: { freq: 3000, type: 'highpass' },
          stereo: true,
          volume: defaultVolume * 0.3,
        });
      }, i * 50);
    }
  }, [playAdvancedFM, defaultVolume]);

  return {
    playBoot,
    playGlitch,
    playHover,
    playNodeCreate,
    playConnection,
    playValidation,
    playMatrixGlitch,
    playDeepBass,
    playHackerSequence,
    playQuantumResonance,
    playTerminalBoot,
    playDataStream,
  };
};
