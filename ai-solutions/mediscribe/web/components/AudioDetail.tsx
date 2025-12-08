import React, { useState, useEffect, useRef } from 'react';
import { Menu } from '@headlessui/react';
import { Transcript, ChatMessageInput } from '../types';
import { ChatInterface } from './ChatInterface';
import { CollapsibleSection } from './CollapsibleSection';

interface AudioDetailProps {
  transcript: Transcript;
  onSendMessage: (message: string) => Promise<void>;
  onUpdateTitle?: (newTitle: string) => Promise<void>;
  onDelete?: () => Promise<void>;
  isChatLoading: boolean;
}

export const AudioDetail: React.FC<AudioDetailProps> = ({
  transcript,
  onSendMessage,
  onUpdateTitle,
  onDelete,
  isChatLoading,
}) => {
  const chatMessages: ChatMessageInput[] = transcript.chats.map(chat => ({
    role: chat.role === 'assistant' ? 'model' : 'user',
    text: chat.message,
  }));

  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editableTitle, setEditableTitle] = useState(transcript.title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setEditableTitle(transcript.title);
  }, [transcript.title]);

  useEffect(() => {
    if (isEditingTitle && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isEditingTitle]);

  const handleTitleSave = async () => {
    if (editableTitle && editableTitle !== transcript.title) {
      await onUpdateTitle?.(editableTitle);
    }
    setIsEditingTitle(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      handleTitleSave();
    } else if (e.key === 'Escape') {
      setEditableTitle(transcript.title);
      setIsEditingTitle(false);
    }
  };

  const handleDelete = () => {
    if (window.confirm('Are you sure you want to delete this transcript and all its data? This action cannot be undone.')) {
      onDelete?.();
    }
  };

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
            <div className="flex-1 group">
              {!isEditingTitle ? (
                <div className="flex items-center gap-2">
                   <h2 className="text-xl font-bold text-slate-800">{transcript.title}</h2>
                   <button onClick={() => setIsEditingTitle(true)} className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded-md hover:bg-slate-100">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.536L16.732 3.732z" /></svg>
                   </button>
                </div>
              ) : (
                <input
                  ref={inputRef}
                  type="text"
                  value={editableTitle}
                  onChange={(e) => setEditableTitle(e.target.value)}
                  onBlur={handleTitleSave}
                  onKeyDown={handleKeyDown}
                  className="text-xl font-bold text-slate-800 bg-slate-100 border border-slate-300 rounded-md px-2 py-0.5 -m-1"
                />
              )}
            </div>
            <div className="flex items-center gap-2">
                {transcript.audio_url && (
                  <div className="flex-shrink-0">
                    <audio controls className="h-10" preload="metadata">
                      <source src={transcript.audio_url} type="audio/mpeg" />
                      <source src={transcript.audio_url} type="audio/wav" />
                      Your browser does not support the audio element.
                    </audio>
                  </div>
                )}
                <ActionsMenu onDelete={handleDelete} />
            </div>
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

const ActionsMenu: React.FC<{ onDelete: () => void }> = ({ onDelete }) => {
  return (
    <Menu as="div" className="relative inline-block text-left">
      <div>
        <Menu.Button className="p-2 rounded-full hover:bg-slate-100 text-slate-500 hover:text-slate-700">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z" />
          </svg>
        </Menu.Button>
      </div>
      <Menu.Items className="absolute right-0 w-48 mt-2 origin-top-right bg-white divide-y divide-gray-100 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-10">
        <div className="px-1 py-1">
          <Menu.Item>
            {({ active }) => (
              <button
                onClick={onDelete}
                className={`${
                  active ? 'bg-red-500 text-white' : 'text-gray-900'
                } group flex rounded-md items-center w-full px-2 py-2 text-sm`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className={`h-5 w-5 mr-2 ${active ? 'text-white' : 'text-red-500'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Delete
              </button>
            )}
          </Menu.Item>
        </div>
      </Menu.Items>
    </Menu>
  );
};
