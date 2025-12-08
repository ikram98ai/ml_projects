import React from 'react';
import { TranscriptListItem } from '../types';

interface SidebarProps {
  transcripts: TranscriptListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onNewAudio: () => void;
  isLoading: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  transcripts,
  selectedId,
  onSelect,
  onNewAudio,
  isLoading,
}) => {
  const getStatusBadge = (status: string) => {
    const styles = {
      processing: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      completed: 'bg-green-100 text-green-700 border-green-200',
      failed: 'bg-red-100 text-red-700 border-red-200',
    };
    
    return (
      <span className={`text-xs px-2 py-1 rounded-full border ${styles[status as keyof typeof styles] || 'bg-slate-100 text-slate-700'}`}>
        {status}
      </span>
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="h-full bg-white border-r border-slate-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-slate-200">
        <button
          onClick={onNewAudio}
          className="w-full bg-gradient-to-r from-blue-600 to-blue-800 text-white font-semibold py-3 px-4 rounded-xl hover:from-blue-700 hover:to-blue-900 transition-all shadow-md flex items-center justify-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="16"></line>
            <line x1="8" y1="12" x2="16" y2="12"></line>
          </svg>
          New Recording
        </button>
      </div>

      {/* List Header */}
      <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
        <h2 className="text-sm font-semibold text-slate-700">Your Recordings</h2>
        <p className="text-xs text-slate-500 mt-1">{transcripts.length} total</p>
      </div>

      {/* Transcripts List */}
      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-200 border-t-blue-600"></div>
            <p className="text-sm text-slate-500 mt-3">Loading recordings...</p>
          </div>
        ) : transcripts.length === 0 ? (
          <div className="p-8 text-center">
            <svg className="mx-auto h-12 w-12 text-slate-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
            </svg>
            <p className="text-sm font-medium text-slate-700 mt-3">No recordings yet</p>
            <p className="text-xs text-slate-500 mt-1">Click "New Recording" to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {transcripts.map((transcript) => (
              <button
                key={transcript.id}
                onClick={() => onSelect(transcript.id)}
                className={`w-full text-left p-4 hover:bg-slate-50 transition-colors ${
                  selectedId === transcript.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="text-xs text-slate-500">{formatDate(transcript.created_at)}</span>
                  {getStatusBadge(transcript.status)}
                </div>
                <h4 className="text-sm font-semibold text-slate-800 mb-1 line-clamp-2">
                  {transcript.title}
                </h4>
                {transcript.summary && (
                  <p className="text-xs text-slate-500 line-clamp-2 leading-relaxed">
                    {transcript.summary.substring(0, 60)}...
                  </p>
                )}
                {!transcript.summary && (
                  <p className="text-xs text-slate-400 italic">Processing...</p>
                )}
              </button>
            ))}

          </div>
        )}
      </div>
    </div>
  );
};
