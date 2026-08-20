import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Sidebar } from './Sidebar';
import { AudioDetail } from './AudioDetail';
import { AudioRecorder } from './AudioRecorder';
import { TranscriptListItem, Transcript } from '../types';
import { 
  listTranscripts, 
  getTranscript, 
  uploadAudio, 
  askQuestion, 
  getTranscriptStatus,
  updateTranscriptTitle,
  deleteTranscript,
} from '../services/api';

type View = 'list' | 'detail' | 'record';

export const Dashboard: React.FC = () => {
  const { user, token, logout } = useAuth();
  const [view, setView] = useState<View>('list');
  const [transcripts, setTranscripts] = useState<TranscriptListItem[]>([]);
  const [selectedTranscript, setSelectedTranscript] = useState<Transcript | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  // Load transcripts on mount
  useEffect(() => {
    loadTranscripts();
  }, []);

  // Effect 1: Poll for status updates on any "processing" transcripts
  useEffect(() => {
    const processingTranscripts = transcripts.filter(t => t.status === 'processing');
    if (processingTranscripts.length === 0) {
      return;
    }

    const interval = setInterval(() => {
      const statusPromises = processingTranscripts.map(t => getTranscriptStatus(t.id, token!));
      Promise.allSettled(statusPromises).then(results => {
        setTranscripts(currentTranscripts => {
          let hasChanged = false;
          const newTranscripts = currentTranscripts.map(transcript => {
            const resultIndex = processingTranscripts.findIndex(p => p.id === transcript.id);
            if (resultIndex === -1) {
              return transcript;
            }

            const result = results[resultIndex];
            let newStatus = transcript.status;

            if (result.status === 'fulfilled' && result.value.status !== 'processing') {
              newStatus = result.value.status;
            } else if (result.status === 'rejected') {
              newStatus = 'failed';
            }

            if (newStatus !== transcript.status) {
              hasChanged = true;
              return { ...transcript, status: newStatus };
            }
            return transcript;
          });

          return hasChanged ? newTranscripts : currentTranscripts;
        });
      });
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(interval);
  }, [transcripts, token]);

  // Effect 2: Fetch full data when a selected transcript completes processing
  useEffect(() => {
    if (!selectedId || !selectedTranscript) return;

    const listItem = transcripts.find(t => t.id === selectedId);
    
    // If the detail view is showing "processing" but the list now says "completed", fetch full data.
    if (selectedTranscript.status === 'processing' && listItem?.status === 'completed') {
      getTranscript(selectedId, token!).then(fullData => {
        setSelectedTranscript(fullData);
        // Also update the list with the summary from the full data
        setTranscripts(currentList =>
          currentList.map(item =>
            item.id === selectedId ? { ...item, summary: fullData.summary } : item
          )
        );
      });
    }
  }, [transcripts, selectedId, selectedTranscript, token]);

  const loadTranscripts = async () => {
    try {
      const data = await listTranscripts(token!);
      // Sort by created_at descending (newest first)
      data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setTranscripts(data);
    } catch (error) {
      console.error('Failed to load transcripts:', error);
    } finally {
      setIsLoadingList(false);
    }
  };

  const handleSelectTranscript = async (id: string) => {
    setSelectedId(id);
    setIsLoadingDetail(true);
    setView('detail');
    
    try {
      const data = await getTranscript(id, token!);
      setSelectedTranscript(data);
    } catch (error) {
      console.error('Failed to load transcript:', error);
      alert('Failed to load recording details');
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleNewAudio = () => {
    setView('record');
    setSelectedId(null);
    setSelectedTranscript(null);
  };

  const handleAudioReady = async (audioBlob: Blob, title: string) => {
    setIsProcessing(true);
    try {
      const result = await uploadAudio(audioBlob, title, token!);
      
      const now = new Date().toISOString();

      // Add the new processing transcript to the main list
      const newTranscriptItem: TranscriptListItem = {
        id: result.id,
        title: title,
        status: 'processing',
        created_at: now,
        summary: 'Your transcript is being processed...', 
      };
      setTranscripts(prev => [newTranscriptItem, ...prev]);
      
      // Create a temporary full transcript object for the detail view
      const tempTranscript: Transcript = {
        id: result.id,
        title: title,
        status: 'processing',
        created_at: now,
        summary: '',
        soap_note: null,
        audio_url: '', // This will be fetched later by the poller
        chats: [],
      };
      
      // Select the new item and switch to the detail view
      setSelectedTranscript(tempTranscript);
      setSelectedId(result.id);
      setView('detail');

    } catch (error) {
      console.error('Upload failed:', error);
      alert('Failed to upload audio. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!selectedId) return;
    
    setIsChatLoading(true);
    try {
      await askQuestion(selectedId, message, token!);
      
      // Reload the transcript to get updated chat history
      const updated = await getTranscript(selectedId, token!);
      setSelectedTranscript(updated);
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('Failed to send message. Please try again.');
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleUpdateTitle = async (id: string, newTitle: string) => {
    if (!id) return;

    try {
      await updateTranscriptTitle(id, newTitle, token!);
      // Optimistically update UI
      if (selectedId === id) {
        setSelectedTranscript(prev => prev ? { ...prev, title: newTitle } : null);
      }
      setTranscripts(prev => prev.map(t => t.id === id ? { ...t, title: newTitle } : t));
    } catch (error) {
      console.error('Failed to update title:', error);
      alert('Failed to update title. Please try again.');
    }
  };

  const handleDeleteTranscript = async (id: string) => {
    if (!id) return;

    try {
      await deleteTranscript(id, token!);
      // Optimistically update UI
      setTranscripts(prev => prev.filter(t => t.id !== id));
      if (selectedId === id) {
        setSelectedId(null);
        setSelectedTranscript(null);
        setView('list');
      }
    } catch (error) {
      console.error('Failed to delete transcript:', error);
      alert('Failed to delete transcript. Please try again.');
    }
  };

  return (
    <div className="h-screen flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 shadow-sm z-10">
        <div className="h-16 px-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-r from-blue-600 to-blue-800 p-2 rounded-lg">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <path d="M8 13h8"></path>
                <path d="M8 17h8"></path>
                <path d="M8 9h2"></path>
              </svg>
            </div>
            <span className="font-bold text-lg text-slate-800">MediScribe AI</span>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3 px-4 py-2 bg-slate-50 rounded-xl">
              <div className="h-8 w-8 rounded-full bg-gradient-to-r from-blue-600 to-blue-800 flex items-center justify-center text-white font-semibold text-sm">
                {user?.username.charAt(0).toUpperCase()}
              </div>
              <span className="text-sm font-medium text-slate-700">{user?.username}</span>
            </div>
            <button
              onClick={logout}
              className="px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-xl transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-80 flex-shrink-0">
          <Sidebar
            transcripts={transcripts}
            selectedId={selectedId}
            onSelect={handleSelectTranscript}
            onNewAudio={handleNewAudio}
            onUpdateTitle={handleUpdateTitle}
            onDelete={handleDeleteTranscript}
            isLoading={isLoadingList}
          />
        </div>

        {/* Main Area */}
        <div className="flex-1 overflow-hidden">
          {view === 'list' || (!selectedTranscript && view === 'detail') ? (
            <div className="h-full flex items-center justify-center bg-slate-50">
              <div className="text-center max-w-md px-4">
                <div className="bg-gradient-to-r from-blue-100 to-blue-300 rounded-full p-6 inline-block mb-4">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                </div>
                <h2 className="text-2xl font-bold text-slate-800 mb-2">Welcome to MediScribe AI</h2>
                <p className="text-slate-600 mb-6">
                  Select a recording from the sidebar or create a new one to get started with AI-powered medical documentation.
                </p>
                <button
                  onClick={handleNewAudio}
                  className="bg-gradient-to-r from-blue-600 to-blue-800 text-white font-semibold py-3 px-6 rounded-xl hover:from-blue-700 hover:to-blue-800 transition-all shadow-lg inline-flex items-center gap-2"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="8" x2="12" y2="16"></line>
                    <line x1="8" y1="12" x2="16" y2="12"></line>
                  </svg>
                  Start New Recording
                </button>
              </div>
            </div>
          ) : view === 'record' ? (
            <div className="h-full flex items-center justify-center bg-slate-50 p-6">
              <AudioRecorder onAudioReady={handleAudioReady} isProcessing={isProcessing} />
            </div>
          ) : isLoadingDetail ? (
            <div className="h-full flex items-center justify-center bg-slate-50">
              <div className="text-center">
                <div className="inline-block animate-spin rounded-full h-16 w-16 border-4 border-slate-200 border-t-blue-600 mb-4"></div>
                <p className="text-slate-600">Loading recording...</p>
              </div>
            </div>
          ) : selectedTranscript ? (
            <AudioDetail
              transcript={selectedTranscript}
              onSendMessage={handleSendMessage}
              onUpdateTitle={(newTitle) => handleUpdateTitle(selectedId!, newTitle)}
              onDelete={() => handleDeleteTranscript(selectedId!)}
              isChatLoading={isChatLoading}
            />
          ) : null}
        </div>
      </div>
    </div>
  );
};
