import React, { useState, useEffect } from 'react';
import { AudioRecorder } from './components/AudioRecorder';
import { SoapCard } from './components/SoapCard';
import { ChatInterface } from './components/ChatInterface';
import { Button } from './components/Button';
import { uploadAudio, getTranscript, askQuestion } from './services/api';
import { SoapNote, ChatMessage, Patient } from './types';

// Mock Patient Data
const MOCK_PATIENT: Patient = {
  id: 'P-2024-001',
  name: 'Sarah Tan Li Min',
  age: 68,
  mrn: 'SG-882910'
};

// For POC: Using a demo token. In production, implement proper login.
const DEMO_TOKEN = 'demo-token-for-poc';

const App: React.FC = () => {
  // State Management
  const [view, setView] = useState<'upload' | 'analysis'>('upload');
  const [isProcessing, setIsProcessing] = useState(false);
  const [transcriptId, setTranscriptId] = useState<string>('');
  const [transcript, setTranscript] = useState<string>('');
  const [soapNote, setSoapNote] = useState<SoapNote | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  // Polling for transcript completion
  useEffect(() => {
    if (!transcriptId || !isProcessing) return;

    const pollInterval = setInterval(async () => {
      try {
        const result = await getTranscript(transcriptId, DEMO_TOKEN);
        
        if (result.status === 'completed') {
          setIsProcessing(false);
          if (result.soap_note) {
            setSoapNote(result.soap_note);
          }
          // Get the full transcript from the summary for now
          // In a real app, we'd have a separate endpoint to get the full transcript text
          setTranscript(result.summary || 'Transcript processing completed');
          setView('analysis');
          clearInterval(pollInterval);
        } else if (result.status === 'failed') {
          setIsProcessing(false);
          alert('Failed to process audio. Please try again.');
          clearInterval(pollInterval);
        }
      } catch (error) {
        console.error('Polling error:', error);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [transcriptId, isProcessing]);

  // Handlers
  const handleAudioReady = async (audioBlob: Blob) => {
    setIsProcessing(true);
    try {
      const result = await uploadAudio(audioBlob, DEMO_TOKEN);
      setTranscriptId(result.id);
      // Polling will handle the rest
    } catch (error) {
      console.error("Upload failed:", error);
      alert("Failed to upload audio. Please ensure the backend is running.");
      setIsProcessing(false);
    }
  };

  const handleSendMessage = async (text: string) => {
    const newUserMsg: ChatMessage = { role: 'user', text };
    setMessages(prev => [...prev, newUserMsg]);
    setIsChatLoading(true);

    try {
      const result = await askQuestion(transcriptId, text, DEMO_TOKEN);
      setMessages(prev => [...prev, { role: 'model', text: result.answer }]);
    } catch (error) {
      console.error("Chat failed:", error);
      setMessages(prev => [...prev, { role: 'model', text: "Sorry, I encountered an error." }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleReset = () => {
    if (confirm("Are you sure? All current data will be lost.")) {
      setView('upload');
      setTranscriptId('');
      setTranscript('');
      setSoapNote(null);
      setMessages([]);
    }
  };

  const exportPdf = () => {
    alert("In the full version, this generates a PDF and saves to S3 via FastAPI.");
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-md sticky top-0 z-50 border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-blue-600 p-2 rounded-lg">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path><polyline points="14 2 14 8 20 8"></polyline><path d="M8 13h8"></path><path d="M8 17h8"></path><path d="M8 9h2"></path></svg>
            </div>
            <span className="font-bold text-lg text-slate-800 tracking-tight">MediScribe AI</span>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex flex-col items-end mr-4 hidden md:flex">
              <span className="text-sm font-semibold text-slate-900">{MOCK_PATIENT.name}</span>
              <span className="text-xs text-slate-500">MRN: {MOCK_PATIENT.mrn} | {MOCK_PATIENT.age}yo</span>
            </div>
            <div className="h-8 w-8 rounded-full bg-slate-200 border-2 border-white shadow-sm overflow-hidden">
                <img src={`https://picsum.photos/seed/${MOCK_PATIENT.id}/200`} alt="Avatar" className="h-full w-full object-cover" />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-grow bg-slate-50 p-6">
        <div className="max-w-7xl mx-auto h-full">
          
          {view === 'upload' && (
            <div className="h-full flex flex-col items-center pt-12">
              <AudioRecorder onAudioReady={handleAudioReady} isProcessing={isProcessing} />
              
              <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-4xl text-center">
                {[
                  { title: "Secure Audio", desc: "End-to-end encryption compliant with PDPA/HIPAA standards." },
                  { title: "Gemini 2.5 Flash", desc: "Low latency transcription and medical reasoning." },
                  { title: "Automated SOAP", desc: "Instant clinical documentation ready for EMR review." }
                ].map((item, i) => (
                  <div key={i} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
                    <h3 className="font-semibold text-slate-800 mb-2">{item.title}</h3>
                    <p className="text-sm text-slate-500">{item.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {view === 'analysis' && soapNote && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-8rem)]">
              {/* Left Column: Transcript */}
              <div className="lg:col-span-3 flex flex-col h-full bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
                 <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                   <h3 className="font-semibold text-slate-700">Transcript</h3>
                   <span className="text-xs text-slate-400">Verbatim</span>
                 </div>
                 <div className="p-4 overflow-y-auto text-sm text-slate-600 leading-relaxed whitespace-pre-wrap custom-scrollbar flex-1 font-mono">
                   {transcript}
                 </div>
              </div>

              {/* Middle Column: SOAP Note */}
              <div className="lg:col-span-5 h-full">
                <SoapCard note={soapNote} />
              </div>

              {/* Right Column: Chat & Actions */}
              <div className="lg:col-span-4 flex flex-col gap-6 h-full">
                <div className="flex-1 min-h-0">
                  <ChatInterface 
                    messages={messages} 
                    onSendMessage={handleSendMessage} 
                    isLoading={isChatLoading} 
                  />
                </div>
                
                <div className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 space-y-3">
                   <Button variant="primary" onClick={exportPdf} className="w-full justify-center">
                     Export to EMR / PDF
                   </Button>
                   <Button variant="ghost" onClick={handleReset} className="w-full justify-center text-red-500 hover:bg-red-50 hover:text-red-600">
                     End Session
                   </Button>
                </div>
                
                {/* POC Notice */}
                 <div className="bg-blue-50 border border-blue-100 p-3 rounded-xl text-xs text-blue-700">
                    <strong>Production Mode:</strong> This frontend now communicates with the FastAPI backend. 
                    Audio processing happens server-side with results stored in PynamoDB (SGP Region).
                 </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
};

export default App;
