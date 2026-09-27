
// web/speech.js

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

/**
 * Checks if speech recognition and speech synthesis are supported by the browser.
 * @returns {{ listen: boolean, speak: boolean }}
 */
export function speechAvailable() {
  const listenAvailable = typeof SpeechRecognition !== 'undefined';
  const speakAvailable = typeof window !== 'undefined' && 'speechSynthesis' in window;
  return {
    listen: listenAvailable,
    speak: speakAvailable,
  };
}

/**
 * Immediately cancels any ongoing speech playback.
 */
export function stopSpeaking() {
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {

let activeListenPromise = null;

function recognitionConstructor() {
  if (typeof window === "undefined") return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export function speechAvailable() {
  return {
    listen: Boolean(recognitionConstructor()),
    speak: typeof window !== "undefined" && "speechSynthesis" in window,
  };
}

export function stopSpeaking() {
  if (typeof window !== "undefined" && "speechSynthesis" in window) {

    window.speechSynthesis.cancel();
  }
}


/**
 * Speaks text aloud in English.
 * Cancels any earlier speech first to prevent overlapping.
 * @param {string} text
 */
export function speak(text) {
  if (!text || typeof window === 'undefined' || !('speechSynthesis' in window)) {
    return;
  }

  // Always cancel older speech first
  stopSpeaking();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'en-US'; // Switched to English
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  window.speechSynthesis.speak(utterance);
}

/**
 * Listens for a single speech utterance via push-to-talk and returns the transcript.
 * @returns {Promise<string>}
 */
export function listen() {
  return new Promise((resolve, reject) => {
    if (!SpeechRecognition) {
      return reject(new Error("Speech recognition is not supported on this browser."));
    }

    // Stop ongoing speech so microphone doesn't pick up computer audio
    stopSpeaking();

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';         // Switched to English
    recognition.continuous = false;     // One utterance at a time
    recognition.interimResults = false; // Final results only
    recognition.maxAlternatives = 1;

    let transcriptResult = '';
    let hasHandledError = false;

    recognition.onresult = (event) => {
      if (event.results && event.results.length > 0) {
        transcriptResult = event.results[0][0].transcript.trim();
      }
    };

    recognition.onerror = (event) => {
      hasHandledError = true;
      let errorMsg = `Speech recognition error: ${event.error}`;
      if (event.error === 'not-allowed') {
        errorMsg = "Microphone access denied. Please allow microphone permissions.";
      } else if (event.error === 'no-speech') {
        errorMsg = "No speech detected. Please try again.";
      } else if (event.error === 'network') {
        errorMsg = "Network error connecting to speech recognition service.";
      }
      reject(new Error(errorMsg));
    };

    recognition.onend = () => {
      if (hasHandledError) return;
      if (transcriptResult) {
        resolve(transcriptResult);
      } else {
        reject(new Error("No speech detected."));
      }

export function speak(text) {
  if (!text || !speechAvailable().speak || typeof SpeechSynthesisUtterance === "undefined") return;

  stopSpeaking();
  const utterance = new SpeechSynthesisUtterance(String(text));
  utterance.lang = "en-US";
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

function recognitionErrorMessage(code) {
  const messages = {
    "not-allowed": "Microphone access was denied. Allow microphone permission or type your order.",
    "service-not-allowed": "Speech recognition is blocked. Check browser permissions or type your order.",
    "no-speech": "No speech was detected. Please try again or type your order.",
    "audio-capture": "No working microphone was found. Connect one or type your order.",
    network: "Speech recognition could not reach its service. Check your connection or type your order.",
    aborted: "Speech recognition was stopped.",
  };
  return messages[code] || `Speech recognition failed (${code || "unknown error"}). Please type your order.`;
}

export async function listen() {
  if (activeListenPromise) return activeListenPromise;

  const Recognition = recognitionConstructor();
  if (!Recognition) {
    throw new Error("Speech recognition is not supported in this browser. Please type your order.");
  }

  stopSpeaking();
  activeListenPromise = new Promise((resolve, reject) => {
    const recognition = new Recognition();
    let settled = false;
    let transcript = "";

    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    const finish = (callback, value) => {
      if (settled) return;
      settled = true;
      callback(value);
    };

    recognition.onresult = (event) => {
      transcript = event.results?.[0]?.[0]?.transcript?.trim() || "";
    };
    recognition.onerror = (event) => {
      finish(reject, new Error(recognitionErrorMessage(event.error)));
    };
    recognition.onend = () => {
      if (transcript) finish(resolve, transcript);
      else finish(reject, new Error("No speech was detected. Please try again or type your order."));

    };

    try {
      recognition.start();

    } catch (err) {
      reject(new Error(`Unable to start speech recognition: ${err.message}`));
    }
  });
}
=======
    } catch (error) {
      finish(reject, new Error(`Unable to start speech recognition: ${error.message}`));
    }
  });

  try {
    return await activeListenPromise;
  } finally {
    activeListenPromise = null;
  }
}

