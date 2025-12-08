import React, { useState, useRef, useEffect } from 'react';
import { Button } from './Button';

interface AudioRecorderProps {
  onAudioReady: (blob: Blob) => void;
  isProcessing: boolean;
}

export const AudioRecorder: React.FC<AudioRecorderProps> = ({ onAudioReady, isProcessing }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        onAudioReady(blob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setDuration(0);
      timerRef.current = window.setInterval(() => {
        setDuration(prev => prev + 1);
      }, 1000);
    } catch (err) {
      console.error("Error accessing microphone:", err);
      alert("Microphone access is required to record audio.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onAudioReady(file);
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-white rounded-3xl shadow-sm border border-slate-100 p-8 flex flex-col items-center justify-center space-y-6 max-w-lg mx-auto mt-10">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-semibold text-slate-900">Start Consultation</h2>
        <p className="text-slate-500">Record a new session or upload an existing audio file.</p>
      </div>

      <div className="relative">
        {isRecording && (
          <div className="absolute inset-0 rounded-full animate-ping bg-red-100 opacity-75"></div>
        )}
        <div className={`relative w-24 h-24 rounded-full flex items-center justify-center transition-colors duration-300 ${isRecording ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600'}`}>
          {isRecording ? (
             <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg>
          ) : (
             <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
          )}
        </div>
      </div>

      {isRecording && (
        <div className="text-2xl font-mono font-medium text-slate-800">
          {formatTime(duration)}
        </div>
      )}

      <div className="flex flex-col gap-3 w-full max-w-xs">
        {isRecording ? (
          <Button variant="danger" onClick={stopRecording} className="w-full justify-center">
            Stop Recording
          </Button>
        ) : (
          <Button variant="primary" onClick={startRecording} disabled={isProcessing} className="w-full justify-center">
            Start Recording
          </Button>
        )}

        <div className="relative flex py-2 items-center">
          <div className="flex-grow border-t border-slate-200"></div>
          <span className="flex-shrink-0 mx-4 text-slate-400 text-sm">OR</span>
          <div className="flex-grow border-t border-slate-200"></div>
        </div>

        <input
          type="file"
          accept="audio/*"
          className="hidden"
          ref={fileInputRef}
          onChange={handleFileUpload}
        />
        <Button 
          variant="secondary" 
          onClick={() => fileInputRef.current?.click()} 
          disabled={isProcessing || isRecording}
          className="w-full justify-center"
        >
          Upload Audio File
        </Button>
      </div>
      
      {isProcessing && (
         <p className="text-sm text-blue-600 animate-pulse font-medium">Uploading & Analyzing with Gemini AI...</p>
      )}
    </div>
  );
};
