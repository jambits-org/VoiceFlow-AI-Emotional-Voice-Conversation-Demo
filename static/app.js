let sessionId = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let isProcessing = false;
let recordingTimer = null;
const MAX_RECORDING_SECONDS = 30;

// --- OTP ---
async function verifyOTP() {
  const otp = document.getElementById('otp-input').value.trim();
  const errEl = document.getElementById('otp-error');
  const btn = document.getElementById('otp-btn');
  if (!otp) return;

  btn.textContent = 'Verifying...';
  btn.disabled = true;

  try {
    const fd = new FormData();
    fd.append('otp', otp);
    const res = await fetch('/api/verify-otp', { method: 'POST', body: fd });
    if (!res.ok) {
      const d = await res.json();
      throw new Error(d.detail || 'Invalid code');
    }
    const data = await res.json();
    sessionId = data.session_id;
    document.getElementById('attempts-count').textContent = data.attempts_left;
    document.getElementById('otp-screen').classList.add('hidden');
    document.getElementById('chat-screen').classList.remove('hidden');
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('hidden');
    btn.textContent = 'Continue';
    btn.disabled = false;
  }
}

document.getElementById('otp-input').addEventListener('keydown', e => {
  if (e.key === 'Enter') verifyOTP();
});

// --- Recording (tap to start / tap to stop) ---
function toggleRecording() {
  if (isProcessing) return;
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
}

async function startRecording() {
  if (isRecording || isProcessing) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
    audioChunks = [];
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.start();
    isRecording = true;

    // UI: recording state
    setMicState('recording');

    // Auto-stop after MAX_RECORDING_SECONDS
    recordingTimer = setTimeout(() => {
      if (isRecording) stopRecording();
    }, MAX_RECORDING_SECONDS * 1000);

  } catch (e) {
    showToast('Microphone access is needed to use voice chat', 'error');
  }
}

function stopRecording() {
  if (!isRecording || !mediaRecorder) return;
  isRecording = false;
  clearTimeout(recordingTimer);

  setMicState('processing');

  mediaRecorder.onstop = async () => {
    const blob = new Blob(audioChunks, { type: 'audio/webm' });
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
    if (blob.size < 1000) {
      showToast('Recording was too short, try again', 'warning');
      setMicState('idle');
      return;
    }
    await sendAudio(blob);
  };
  mediaRecorder.stop();
}

// --- Send audio to backend ---
async function sendAudio(blob) {
  isProcessing = true;
  setMicState('processing');

  const fd = new FormData();
  fd.append('session_id', sessionId);
  fd.append('audio', blob, 'audio.webm');

  try {
    const res = await fetch('/api/chat', { method: 'POST', body: fd });
    if (!res.ok) {
      const d = await res.json();
      throw new Error(d.detail || 'Something went wrong');
    }
    const data = await res.json();

    document.getElementById('attempts-count').textContent = data.attempts_left;
    addMessage(data.user_text, 'user');
    addMessage(data.reply_text, 'ai');

    // Play audio
    setMicState('speaking');
    const audioSrc = 'data:audio/mp3;base64,' + data.audio;
    const audio = new Audio(audioSrc);
    audio.onended = () => setMicState('idle');
    audio.onerror = () => setMicState('idle');
    audio.play();

    if (data.attempts_left <= 0) {
      showToast('You\'ve used all your attempts. Thanks for trying it out!', 'warning');
      setMicState('disabled');
      return;
    }
  } catch (e) {
    showToast(e.message, 'error');
    setMicState('idle');
  } finally {
    isProcessing = false;
  }
}

// --- Mic button states ---
function setMicState(state) {
  const btn = document.getElementById('mic-btn');
  const hint = document.getElementById('mic-hint');
  const waves = document.getElementById('wave-container');
  const spinner = document.getElementById('spinner');
  const micIcon = document.getElementById('mic-icon');
  const stopIcon = document.getElementById('stop-icon');

  // Reset all
  waves.classList.add('hidden');
  spinner.classList.add('hidden');
  micIcon.classList.remove('hidden');
  stopIcon.classList.add('hidden');
  btn.disabled = false;
  btn.classList.remove('opacity-50', 'scale-110', 'ring-2', 'ring-red-400/50', 'bg-red-500/20');

  switch (state) {
    case 'idle':
      hint.textContent = 'Tap to speak';
      break;

    case 'recording':
      waves.classList.remove('hidden');
      micIcon.classList.add('hidden');
      stopIcon.classList.remove('hidden');
      btn.classList.add('scale-110', 'ring-2', 'ring-red-400/50');
      hint.textContent = 'Recording... tap to stop';
      break;

    case 'processing':
      spinner.classList.remove('hidden');
      micIcon.classList.add('hidden');
      btn.disabled = true;
      btn.classList.add('opacity-50');
      hint.textContent = 'Thinking...';
      break;

    case 'speaking':
      btn.disabled = true;
      btn.classList.add('opacity-50');
      hint.textContent = 'Speaking...';
      break;

    case 'disabled':
      btn.disabled = true;
      btn.classList.add('opacity-50');
      hint.textContent = 'No attempts left';
      break;
  }
}

// --- Chat messages ---
function addMessage(text, type) {
  const container = document.getElementById('messages');
  const wrapper = document.createElement('div');
  wrapper.className = 'fade-in flex ' + (type === 'user' ? 'justify-end' : 'justify-start');

  const bubble = document.createElement('div');
  bubble.className = 'rounded-2xl px-4 py-3 max-w-[85%] text-sm ';

  if (type === 'user') {
    bubble.className += 'bg-violet-600/20 border border-violet-500/20 rounded-tr-md text-white/90';
  } else {
    bubble.className += 'glass rounded-tl-md text-white/70';
  }

  bubble.textContent = text;
  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;
}

// --- Toast notifications ---
function showToast(message, type = 'error') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');

  const colors = {
    error: 'bg-red-500/15 border-red-500/30 text-red-300',
    warning: 'bg-amber-500/15 border-amber-500/30 text-amber-300',
    info: 'bg-blue-500/15 border-blue-500/30 text-blue-300',
  };

  const icons = {
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
  };

  toast.className = `fade-in flex items-center gap-3 px-4 py-3 rounded-xl border backdrop-blur-xl text-sm ${colors[type] || colors.error}`;
  toast.innerHTML = `
    <span class="text-base">${icons[type] || icons.error}</span>
    <span class="flex-1">${message}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
