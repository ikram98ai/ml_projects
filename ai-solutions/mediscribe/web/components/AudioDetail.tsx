import React from 'react';
import { Transcript, ChatMessageInput } from '../types';
import { SoapCard } from './SoapCard';
import { ChatInterface } from './ChatInterface';
import { CollapsibleSection } from './CollapsibleSection';

interface AudioDetailProps {
  transcript: Transcript;
  onSendMessage: (message: string) => Promise<void>;
  isChatLoading: boolean;
}

export const AudioDetail: React.FC<AudioDetailProps> = ({
  transcript,
  onSendMessage,
  isChatLoading,
}) => {
  // Convert backend chat messages to frontend format
  const chatMessages: ChatMessageInput[] = transcript.chats.map(chat => ({
    role: chat.role === 'assistant' ? 'model' : 'user',
    text: chat.message,
  }));

  return (
    <div className="h-full flex flex-col bg-slate-50">
      {transcript.status === 'processing' ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="inline-block animate-spin rounded-full h-16 w-16 border-4 border-slate-200 border-t-blue-600 mb-4"></div>
            <h3 className="text-xl font-semibold text-slate-700 mb-2">Processing Audio</h3>
            <p className="text-slate-500">Transcribing and generating SOAP note...</p>
            <div className="mt-4 bg-blue-50 border border-blue-100 rounded-xl p-3 text-sm text-blue-700 max-w-md mx-auto">
              This usually takes 30-60 seconds depending on audio length.
            </div>
          </div>
        </div>
      ) : transcript.status === 'failed' ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md">
            <div className="bg-red-100 rounded-full p-4 inline-block mb-4">
              <svg className="h-12 w-12 text-red-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h3 className="text-xl font-semibold text-red-700 mb-2">Processing Failed</h3>
            <p className="text-slate-600">There was an error processing this audio file. Please try uploading again.</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col p-6 gap-4 overflow-hidden">
          {/* Title */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
            <h2 className="text-xl font-bold text-slate-800">{transcript.title}</h2>
            <p className="text-sm text-slate-500 mt-1">
              {new Date(transcript.created_at).toLocaleString()}
            </p>
          </div>

          {/* Main Content Grid */}
          <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 overflow-hidden">
            {/* Left Column: Transcript & SOAP */}
            <div className="flex flex-col gap-4 overflow-y-auto custom-scrollbar">
              {/* Transcript Section */}
              <CollapsibleSection title="Transcript" defaultOpen={true}>
                <div className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                  {transcript.summary || 'No transcript available'}
                </div>
              </CollapsibleSection>

              {/* SOAP Note Section */}
              {transcript.soap_note && (
                <CollapsibleSection title="SOAP Note" defaultOpen={true}>
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-semibold text-slate-800 mb-2">Subjective</h4>
                      <p className="text-sm text-slate-600 leading-relaxed">
                        {transcript.soap_note.subjective}
                      </p>
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-800 mb-2">Objective</h4>
                      <p className="text-sm text-slate-600 leading-relaxed">
                        {transcript.soap_note.objective}
                      </p>
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-800 mb-2">Assessment</h4>
                      <p className="text-sm text-slate-600 leading-relaxed">
                        {transcript.soap_note.assessment}
                      </p>
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-800 mb-2">Plan</h4>
                      <p className="text-sm text-slate-600 leading-relaxed">
                        {transcript.soap_note.plan}
                      </p>
                    </div>
                  </div>
                </CollapsibleSection>
              )}
            </div>

            {/* Right Column: Chat */}
            <div className="flex flex-col gap-4 h-full">
              <div className="flex-1 min-h-0">
                <ChatInterface
                  messages={chatMessages}
                  onSendMessage={onSendMessage}
                  isLoading={isChatLoading}
                />
              </div>
              
              {/* Info Box */}
              <div className="bg-blue-50 border border-blue-100 p-3 rounded-xl text-xs text-blue-700">
                <strong>💬 Ask Questions:</strong> Use the chat to clarify details or get additional insights from the consultation.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
