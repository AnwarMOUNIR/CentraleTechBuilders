const mockTranscripts = [
  "I want a large coffee without sugar",
  "Change order",
  "Make that two coffees",
  "Repeat",
  "Confirm",
  "Cancel",
];

let mockIndex = 0;
let activeListenPromise = null;

export function speechAvailable() {
  return { listen: true, speak: true };
}

export function stopSpeaking() {
  // The mock never starts real audio playback.
}

export function speak(text) {
  stopSpeaking();
  if (text) globalThis.console?.info?.(`[mock speech] ${text}`);
}

export async function listen() {
  if (activeListenPromise) return activeListenPromise;
  activeListenPromise = Promise.resolve().then(() => {
    const transcript = mockTranscripts[mockIndex % mockTranscripts.length];
    mockIndex += 1;
    return transcript;
  });
  try {
    return await activeListenPromise;
  } finally {
    activeListenPromise = null;
  }
}
