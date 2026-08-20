import React from 'react';
import { SoapNote } from '../types';

interface SoapCardProps {
  note: SoapNote;
}

const Section: React.FC<{ title: string; content: string; color: string }> = ({ title, content, color }) => (
  <div className="mb-6 last:mb-0">
    <h4 className={`text-xs font-bold uppercase tracking-wider mb-2 ${color}`}>
      {title}
    </h4>
    <div className="text-slate-700 text-sm leading-relaxed whitespace-pre-wrap bg-slate-50 p-3 rounded-lg border border-slate-100">
      {content}
    </div>
  </div>
);

export const SoapCard: React.FC<SoapCardProps> = ({ note }) => {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden h-full flex flex-col">
      <div className="bg-slate-50 px-6 py-4 border-b border-slate-100 flex justify-between items-center">
        <h3 className="font-semibold text-slate-800">Clinical Summary (SOAP)</h3>
        <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">AI Generated</span>
      </div>
      <div className="p-6 overflow-y-auto custom-scrollbar flex-1">
        <Section title="Subjective" content={note.subjective} color="text-blue-600" />
        <Section title="Objective" content={note.objective} color="text-purple-600" />
        <Section title="Assessment" content={note.assessment} color="text-amber-600" />
        <Section title="Plan" content={note.plan} color="text-emerald-600" />
      </div>
    </div>
  );
};
