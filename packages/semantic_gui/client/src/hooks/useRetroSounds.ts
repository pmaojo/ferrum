import { useCallback } from 'react';

// Authentic Tandy TGA sound frequencies
const RETRO_SOUNDS = {
  // Classic computer beeps
  startup: () => playTone(800, 150),
  click: () => playTone(1200, 50),
  select: () => playTone(900, 75),
  error: () => playSequence([400, 350, 300], [100, 100, 150]),
  success: () => playSequence([600, 800, 1000], [100, 100, 150]),
  typing: () => playTone(1100, 25),

  // Graph interaction sounds
  nodeConnect: () => playSequence([800, 1200], [75, 75]),
  nodeSelect: () => playTone(1000, 100),
  nodeCreate: () => playSequence([600, 900, 1200], [50, 50, 100]),

  // System sounds
  load: () => playSequence([400, 500, 600, 700, 800], [80, 80, 80, 80, 120]),
  save: () => playSequence([1000, 800, 600], [100, 100, 150]),
};

function playTone(frequency: number, duration: number) {
  try {
    const audioContext = new (window.AudioContext ||
      (window as any).webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.setValueAtTime(frequency, audioContext.currentTime);
    oscillator.type = 'square'; // Classic Tandy square wave

    gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(
      0.01,
      audioContext.currentTime + duration / 1000
    );

    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + duration / 1000);
  } catch (error) {
  }
}

function playSequence(frequencies: number[], durations: number[]) {
  frequencies.forEach((freq, index) => {
    const delay = durations.slice(0, index).reduce((sum, dur) => sum + dur, 0);
    setTimeout(() => playTone(freq, durations[index]), delay);
  });
}

export function useRetroSounds() {
  const playSound = useCallback((soundName: keyof typeof RETRO_SOUNDS) => {
    RETRO_SOUNDS[soundName]();
  }, []);

  return { playSound };
}
