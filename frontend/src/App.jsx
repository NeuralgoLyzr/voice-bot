
import { useEffect, useRef, useState } from 'react';

function App() {
  const sendWsRef = useRef(null);
  const receiveWsRef = useRef(null);
  const micWsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const audioRef = useRef(null);
  const mediaSourceRef = useRef(null);
  const sourceBufferRef = useRef(null);
  const queueRef = useRef([]);

  const WS_URL = 'ws://192.168.0.104:8000/ws'

  const processQueue = () => {
    if (
      sourceBufferRef.current &&
      !sourceBufferRef.current.updating &&
      queueRef.current.length > 0
    ) {
      const chunk = queueRef.current.shift();
      try {
        sourceBufferRef.current.appendBuffer(chunk);
      } catch (err) {
        console.error('❌ Error appending buffer:', err);
      }
    }
  };

  useEffect(() => {
    const interval = setInterval(processQueue, 50);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const mediaSource = new MediaSource();
    mediaSourceRef.current = mediaSource;
    audioRef.current.src = URL.createObjectURL(mediaSource);

    const handleSourceOpen = () => {
      const mime = 'audio/webm; codecs=opus';
      const sourceBuffer = mediaSource.addSourceBuffer(mime);
      sourceBuffer.mode = 'sequence';
      sourceBufferRef.current = sourceBuffer;
    };

    mediaSource.addEventListener('sourceopen', handleSourceOpen);
    return () => {
      mediaSource.removeEventListener('sourceopen', handleSourceOpen);
    };
  }, []);

  const handleAudioMessage = async (event) => {
    const audioData = event.data;
    if (audioData instanceof Blob) {
      const arrayBuffer = await audioData.arrayBuffer();
      queueRef.current.push(new Uint8Array(arrayBuffer));
    } else if (audioData instanceof ArrayBuffer) {
      queueRef.current.push(new Uint8Array(audioData));
    }
  };

  const startConnection = () => {
    if (
      sendWsRef.current?.readyState === WebSocket.OPEN &&
      receiveWsRef.current?.readyState === WebSocket.OPEN
    ) {
      console.log('🟢 WebSocket connections already active.');
      return;
    }

    if (sendWsRef.current) sendWsRef.current.close();
    if (receiveWsRef.current) receiveWsRef.current.close();

    console.log('🔗 Connecting to send WebSocket...');
    // const sendWs = new WebSocket('ws://54.234.202.142:8000/ws/send_text');
    const sendWs = new WebSocket(`${WS_URL}/send_text`);

    console.log('🔗 Connecting to receive WebSocket...');
    // const receiveWs = new WebSocket('ws://54.234.202.142:8000/ws/receive_audio');
    const receiveWs = new WebSocket(`${WS_URL}/receive_audio`);

    sendWs.binaryType = 'arraybuffer';
    receiveWs.binaryType = 'blob';

    sendWsRef.current = sendWs;
    receiveWsRef.current = receiveWs;

    sendWs.onopen = () => {
      console.log('✅ Send WebSocket connected');
      if (message) {
        console.log('💬 Sending message:', message);
        sendWs.send(message);
        setMessage('');
      }
    };

    receiveWs.onopen = () => {
      console.log('✅ Receive WebSocket connected');
    };

    receiveWs.onmessage = handleAudioMessage;

    sendWs.onerror = (error) => console.error('❌ Send WS error:', error);
    receiveWs.onerror = (error) => console.error('❌ Receive WS error:', error);

    sendWs.onclose = () => console.log('⛔ Send WebSocket closed');
    receiveWs.onclose = () => console.log('⛔ Receive WebSocket closed');
  };

  const handleSendMessage = () => {
    console.log('📡 Checking WebSocket readiness...');
    console.log('sendWs readyState:', sendWsRef.current?.readyState);
    console.log('receiveWs readyState:', receiveWsRef.current?.readyState);

    if (
      !sendWsRef.current ||
      sendWsRef.current.readyState !== WebSocket.OPEN ||
      !receiveWsRef.current ||
      receiveWsRef.current.readyState !== WebSocket.OPEN
    ) {
      console.warn('🟡 One or more WebSockets not open. (Re)starting...');
      startConnection();
      return;
    }

    console.log('✅ Both WebSockets are open. Sending message...');
    sendWsRef.current.send(message);
    setMessage('');
  };

  const sendAudioToElevenLabs = (audioBlob) => {
    console.log('🎧 Preparing to send audio to ElevenLabs');
    
    if (sendWsRef.current?.readyState !== WebSocket.OPEN) {
      console.warn('⚠️ WebSocket not open, attempting to reconnect');
      startConnection();
      return;
    }

    sendWsRef.current.send(audioBlob);
    console.log('✅ Audio sent to ElevenLabs');
  };

  const startMicStream = async () => {
    if (isRecording) return;

    // const ws = new WebSocket('ws://54.234.202.142:8000/ws/send_audio');
    const ws = new WebSocket(`${WS_URL}/send_audio`);

    console.log('🔗 Connecting to mic WebSocket...');
    ws.binaryType = 'arraybuffer';
    micWsRef.current = ws;

    ws.onopen = async () => {
      console.log('🎙️ Mic WebSocket connected');

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
        audioBitsPerSecond: 64000,
      });

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        if (ws.readyState === WebSocket.OPEN) {
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          ws.send(blob);
          console.log('📨 Sent audio blob');

          // Send audio to ElevenLabs for speech synthesis
          sendAudioToElevenLabs(blob);

          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = 'recording.webm';
          a.click();
        } else {
          console.warn('⚠️ Mic WebSocket not open, skipping audio send.');
        }

        audioChunksRef.current = [];
        stream.getTracks().forEach((track) => track.stop());
        ws.close();
        setIsRecording(false);
      };

      mediaRecorder.start(250); // send every 250ms
      setIsRecording(true);
    };

    ws.onerror = (err) => {
      console.error('❌ Mic WebSocket error:', err);
    };
  };

  const stopMicStream = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  };

  return (
    <div style={{ textAlign: 'center', padding: '2rem' }}>
      <h1>🎤 Lyzr AI Voice Agent 🎤</h1>

      <textarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        rows="4"
        cols="50"
        placeholder="Type your message..."
      />

      <div style={{ marginTop: '1rem' }}>
        <button
          onClick={handleSendMessage}
          style={{
            padding: '1rem 2rem',
            fontSize: '1.2rem',
            borderRadius: '10px',
            backgroundColor: '#06d6a0',
            color: '#fff',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          Send Message & Start WebSocket Connection
        </button>
      </div>

      <div style={{ marginTop: '2rem' }}>
  <button
    onMouseDown={startMicStream}
    onMouseUp={stopMicStream}
    onTouchStart={startMicStream}
    onTouchEnd={stopMicStream}
    style={{
      width: '100px',
      height: '100px',
      borderRadius: '50%',
      backgroundColor: isRecording ? '#ef476f' : '#06d6a0',
      color: '#fff',
      border: 'none',
      cursor: 'pointer',
      fontSize: '1.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: '0 4px 10px rgba(0,0,0,0.2)',
      transition: 'background-color 0.3s ease',
    }}
  >
    🎙️
  </button>
</div>

<div style={{ marginTop: '2rem' }}>
  <audio ref={audioRef} controls autoPlay style={{ display: 'none' }} />
</div>
    </div>
  );
}

export default App;
