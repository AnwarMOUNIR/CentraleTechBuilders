// Person 3 placeholder: keep the text path usable until speech is implemented.
export async function listen() {
  throw new Error("Speech input is not available yet. Please type your order.");
}

export function speak() {}
export function stopSpeaking() {}
export function speechAvailable() {
  return { listen: false, speak: false };
}
