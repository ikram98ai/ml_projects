import React from 'react';
import { Transcript, ChatMessageInput } from '../types';
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
  const chatMessages: ChatMessageInput[] = transcript.chats.map(chat => ({
    role: chat.role === 'assistant' ? 'model' : 'user',
    text: chat.message,
  }));

  const renderContent = () => {
    if (transcript.status === 'processing') {
      return (
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
      );
    }

    if (transcript.status === 'failed') {
      return (
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
      );
    }

    return (
      <div className="flex-1 flex flex-col p-6 gap-6 overflow-hidden">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h2 className="text-xl font-bold text-slate-800">{transcript.title}</h2>
              <p className="text-sm text-slate-500 mt-1">
                {new Date(transcript.created_at).toLocaleString('en-US', {
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit',
                })}
              </p>
            </div>
            {transcript.audio_url && (
              <div className="flex-shrink-0">
                <audio controls className="h-10" preload="metadata">
                  <source src={transcript.audio_url} type="audio/mpeg" />
                  <source src={transcript.audio_url} type="audio/wav" />
                  Your browser does not support the audio element.
                </audio>
              </div>
            )}
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col md:flex-row gap-6 overflow-hidden">
          {/* Primary Column: Chat */}
          <main className="flex-1 flex flex-col gap-4 min-w-0">
            <div className="flex-1 flex flex-col min-h-0 bg-white rounded-2xl shadow-sm border border-slate-200">
              <ChatInterface
                messages={chatMessages}
                onSendMessage={onSendMessage}
                isLoading={isChatLoading}
              />
            </div>
            <div className="bg-blue-50 border border-blue-100 p-3 rounded-xl text-xs text-blue-700">
              <strong>💬 Ask AI:</strong> Use the chat to clarify details or get additional insights from the consultation.
            </div>
          </main>

          {/* Inspector Column: Details */}
          <aside className="w-full md:w-1/3 md:max-w-md lg:max-w-lg flex flex-col gap-4">
            <div className="overflow-y-auto custom-scrollbar space-y-4 bg-white rounded-2xl shadow-sm border border-slate-200 p-4">
              <CollapsibleSection title="Transcript" defaultOpen={true}>
                <div className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                  {transcript.summary || 'No transcript available'}
                </div>
              </CollapsibleSection>

              {transcript.soap_note && (
                <CollapsibleSection title="SOAP Note" defaultOpen={true}>
                  <div className="space-y-4">
                    <div>
                      <h4 className="font-semibold text-slate-800 mb-1">Subjective</h4>
                      <p className="text-sm text-slate-600 leading-relaxed">
                        {transcript.soap_note.subjective}
                      </p>
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-800 mb-1">Objective</h4>
                      <p className="text-sm text-slate-600 leading-relaxed">
                        {transcript.soap_note.objective}
                      </p>
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-800 mb-1">Assessment</h4>
                      <p className="text-sm text-slate-600 leading-relaxed">
                        {transcript.soap_note.assessment}
                      </p>
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-800 mb-1">Plan</h4>
                      <p className="text-sm text-slate-600 leading-relaxed">
                        {transcript.soap_note.plan}
                      </p>
                    </div>
                  </div>
                </CollapsibleSection>
              )}
            </div>
          </aside>
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col bg-slate-50">
      {renderContent()}
    </div>
  );
};
