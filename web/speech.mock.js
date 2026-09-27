// web/speech.mock.js

// Typical test phrases matching the English demo ordering scenario
const mockTranscripts = [
  "I want a large coffee without sugar",
  "Change order",
  "I want two coffees",
  "Confirm",
  "Cancel"
];

let mockIndex = 0;

/**
 * Indicates that the mock supports both listen and speak.
 */
export function speechAvailable() {
  return {
    listen: true,
    speak: true,
  };
}

/**
 * Stops simulated speech.
 */
export function stopSpeaking() {
  console.log("[MOCK SPEECH] stopSpeaking called");
}

/**
 * Simulates text-to-speech output in the console.
 * Cancels any previous speech.
 */
export function speak(text) {
  stopSpeaking();
  console.log(`[MOCK SPEECH] speak: "${text}"`);
}

/**
 * Simulates listening by returning the next transcript after a 1-second delay.
 */
export async function listen() {
  stopSpeaking();
  // Simulate 1 second speaking delay
  await new Promise((resolve) => setTimeout(resolve, 1000));

  const phrase = mockTranscripts[mockIndex % mockTranscripts.length];
  mockIndex++;
  console.log(`[MOCK SPEECH] listen returned: "${phrase}"`);
  return phrase;
}