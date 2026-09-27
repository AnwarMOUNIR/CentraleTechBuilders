// Each listen/speak operation settles before the next turn begins.
// API keys never enter this module. Audio stays in memory.
export function createVoice(notify = () => {}) {
  let config = { stt: false, local_stt: false, tts: false };
  let stream, context, audio, url, cancelOperation, request;
  let stopped = false;
  let mockIndex = 0;
  const query = new URLSearchParams(location.search);
  const mock = query.get('mockSpeech') === 'true';
  const mockSilenceOnce = query.get('mockSilence') === 'once';
  const phrases = [
    'Two large coffees without sugar and one croissant', 'No, cancel',
    'Two large coffees without sugar and one croissant', 'Confirm order',
  ];
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

  function stopPlayback() {
    if (audio) { audio.pause(); audio = null; }
    window.speechSynthesis?.cancel();
    cancelOperation?.();
    cancelOperation = null;
    request?.abort();
    if (url) { URL.revokeObjectURL(url); url = null; }
  }
  function stop() {
    stopped = true;
    stopPlayback();
    stream?.getTracks().forEach(t => t.stop());
    stream = null;
    if (context) { context.close().catch(() => {}); context = null; }
  }
  async function initialize() {
    try {
      const response = await fetch('/voice/config', { signal: AbortSignal.timeout(5000) });
      if (response.ok) config = await response.json();
    } catch { /* Browser speech stays available offline. */ }
  }
  async function start() {
    stopped = false;
    if (mock) return;
    if ((config.local_stt || config.stt) && navigator.mediaDevices?.getUserMedia && window.MediaRecorder) {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      if (stopped) { stream.getTracks().forEach(t => t.stop()); stream = null; return; }
      context = new (window.AudioContext || window.webkitAudioContext)();
      await context.resume();
    } else if (!Recognition) {
      throw new Error('Voice input is unavailable. Use Chrome or Edge on localhost, or type your order.');
    }
  }
  async function browserSpeak(text) {
    if (!window.speechSynthesis) throw new Error('Audio playback is unavailable. The response is visible on screen.');
    await new Promise((resolve, reject) => {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'en-US';
      utterance.rate = 0.92;
      utterance.pitch = 1;
      utterance.volume = 1;
      const englishVoices = window.speechSynthesis.getVoices()
        .filter(voice => voice.lang.toLowerCase().startsWith('en'));
      utterance.voice = englishVoices.find(voice => /zira|aria|jenny|samantha/i.test(voice.name))
        || englishVoices.find(voice => voice.lang.toLowerCase() === 'en-us' && voice.localService)
        || englishVoices[0]
        || null;
      let timer;
      const finish = (error) => { clearTimeout(timer); cancelOperation = null; error ? reject(error) : resolve(); };
      cancelOperation = () => finish();
      utterance.onend = () => finish();
      utterance.onerror = () => finish(new Error('Speech playback failed. Please use the visible response.'));
      timer = setTimeout(() => { window.speechSynthesis.cancel(); finish(new Error('Speech playback timed out.')); }, 90000);
      window.speechSynthesis.speak(utterance);
    });
  }
  async function speak(text) {
    if (stopped || mock) return;
    if (config.tts) {
      try {
        request = new AbortController();
        const response = await fetch('/voice/speak', { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text }), signal: AbortSignal.any([request.signal, AbortSignal.timeout(30000)]) });
        if (!response.ok) throw new Error('Cloud voice unavailable');
        const blob = await response.blob();
        if (stopped) return;
        url = URL.createObjectURL(blob);
        audio = new Audio(url);
        await new Promise((resolve, reject) => {
          let timer;
          const finish = (error) => { clearTimeout(timer); cancelOperation = null; error ? reject(error) : resolve(); };
          cancelOperation = () => finish();
          audio.onended = () => finish();
          audio.onerror = () => finish(new Error('Playback unavailable'));
          timer = setTimeout(() => finish(new Error('Playback timed out')), 90000);
          audio.play().catch(finish);
        });
        if (url) URL.revokeObjectURL(url);
        url = null; audio = null;
        return;
      } catch {
        if (stopped || request?.signal.aborted) return;
        if (audio) audio.pause();
        if (url) URL.revokeObjectURL(url);
        audio = null; url = null;
        config.tts = false;
        notify('Cloud voice unavailable; using the browser voice.');
      }
    }
    await browserSpeak(text);
  }
  async function recordUtterance() {
    return new Promise((resolve, reject) => {
      const mime = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find(m => MediaRecorder.isTypeSupported(m));
      const recorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      const source = context.createMediaStreamSource(stream);
      const analyser = context.createAnalyser();
      analyser.fftSize = 2048; source.connect(analyser);
      const samples = new Float32Array(analyser.fftSize);
      const chunks = [];
      const began = performance.now();
      let lastSpeech = began, speechFrames = 0, heard = false, cancelled = false, timer;
      function cleanup() { clearInterval(timer); source.disconnect(); analyser.disconnect(); cancelOperation = null; }
      recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
      recorder.onerror = () => { cleanup(); reject(new Error('Microphone recording failed.')); };
      recorder.onstop = () => {
        cleanup();
        if (cancelled || stopped) reject(new Error('Voice session stopped.'));
        else if (chunks.length === 0) reject(new Error('No speech detected. I am still listening.'));
        else resolve(new Blob(chunks, { type: recorder.mimeType || 'audio/webm' }));
      };
      cancelOperation = () => { cancelled = true; if (recorder.state !== 'inactive') recorder.stop(); };
      timer = setInterval(() => {
        analyser.getFloatTimeDomainData(samples);
        const rms = Math.sqrt(samples.reduce((sum, n) => sum + n * n, 0) / samples.length);
        const now = performance.now();
        if (rms > 0.005) { speechFrames++; lastSpeech = now; if (speechFrames >= 2) heard = true; }
        if ((heard && now - lastSpeech > 2000) || now - began > (heard ? 25000 : 15000)) {
          clearInterval(timer);
          if (recorder.state !== 'inactive') recorder.stop();
        }
      }, 50);
      recorder.start(100);
    });
  }
  async function browserListen() {
    if (!Recognition) throw new Error('Cloud recognition failed and browser recognition is unavailable. Please type your order.');
    return new Promise((resolve, reject) => {
      const recognition = new Recognition();
      recognition.lang = 'en-US'; recognition.continuous = false; recognition.interimResults = false;
      let transcript = '', settled = false;
      const timer = setTimeout(() => { finish(new Error('No speech detected. I am still listening.')); recognition.abort(); }, 20000);
      function finish(error) {
        if (settled) return;
        settled = true; clearTimeout(timer); cancelOperation = null;
        error ? reject(error) : resolve(transcript);
      }
      cancelOperation = () => { finish(new Error('Voice session stopped.')); recognition.abort(); };
      recognition.onresult = e => { transcript = e.results?.[0]?.[0]?.transcript?.trim() || ''; };
      recognition.onerror = e => {
        if (e.error === 'no-speech') finish(new Error('No speech detected. I am still listening.'));
        else if (e.error === 'not-allowed') finish(new Error('Microphone permission denied. Allow access or type your order.'));
        else if (e.error === 'network') finish(new Error('Speech service is offline. Retrying; you can also type your order.'));
        else finish(new Error(`Speech recognition: ${e.error}. Please try again.`));
      };
      recognition.onend = () => finish(transcript ? null : new Error('No speech detected. I am still listening.'));
      try { recognition.start(); } catch { finish(new Error('Could not start the microphone.')); }
    });
  }
  async function listen() {
    if (stopped) throw new Error('Voice session stopped.');
    if (mock) {
      await pause(150);
      if (mockSilenceOnce && mockIndex === 0) {
        mockIndex++;
        throw new Error('No speech detected. I am still listening.');
      }
      return phrases[(mockIndex++ - Number(mockSilenceOnce)) % phrases.length];
    }
    if (stream && (config.local_stt || config.stt)) {
      const blob = await recordUtterance();
      if (stopped) throw new Error('Voice session stopped.');
      notify(config.stt ? 'Recognizing your speech with Deepgram…' : 'Recognizing your words locally…');
      try {
        request = new AbortController();
        const response = await fetch('/voice/transcribe', { method: 'POST', headers: { 'Content-Type': blob.type }, body: blob,
          signal: AbortSignal.any([request.signal, AbortSignal.timeout(25000)]) });
        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || 'Speech recognition unavailable');
        }
        const result = await response.json();
        if (!result.text?.trim()) throw new Error('No speech detected. I am still listening.');
        return result.text;
      } catch (error) {
        if (stopped || error.message.startsWith('No speech')) throw error;
        notify('Transcription retry: ' + error.message);
        throw error;
      }
    }
    return browserListen();
  }
  function preparePlayback() { stopped = false; }
  return { initialize, start, stop, speak, listen, stopPlayback, preparePlayback };
}
