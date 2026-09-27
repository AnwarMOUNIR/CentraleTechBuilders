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
    };

    try {
      recognition.start();
    } catch (err) {
      reject(new Error(`Unable to start speech recognition: ${err.message}`));
    }
  });
}