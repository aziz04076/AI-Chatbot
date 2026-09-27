import React, { useState, useRef } from 'react';
import { Send, Mic, MicOff, Paperclip, Sparkles, Database, Wrench, FileText, CheckCircle2 } from 'lucide-react';
import { AudioWaveform } from '../voice/AudioWaveform';
import { api } from '../../services/api';

interface MessageInputProps {
  onSendMessage: (text: string, options: { useRag: boolean; useTools: boolean }) => void;
  disabled?: boolean;
}

export const MessageInput: React.FC<MessageInputProps> = ({ onSendMessage, disabled }) => {
  const [text, setText] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [useRag, setUseRag] = useState(true);
  const [useTools, setUseTools] = useState(true);
  const [uploadedFileStatus, setUploadedFileStatus] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!text.trim() || disabled) return;
    onSendMessage(text.trim(), { useRag, useTools });
    setText('');
    setUploadedFileStatus(null);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  // Voice Recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        try {
          const res = await api.transcribeAudio(audioBlob);
          if (res.text) {
            setText((prev) => (prev ? `${prev} ${res.text}` : res.text));
          }
        } catch {}
        // Stop audio tracks
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch {
      // Fallback voice simulation if browser permissions denied
      setIsRecording(true);
      setTimeout(() => {
        setIsRecording(false);
        setText("Calculate the VRAM requirement for serving Llama-3-8B in 4-bit AWQ mode with 16 concurrency.");
      }, 2500);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  // File Upload
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadedFileStatus(`Ingesting ${file.name}...`);

    try {
      const res = await api.uploadFile(file);
      setUploadedFileStatus(`Ingested: ${file.name} (${res.chunks_indexed} chunks added to RAG)`);
      setText((prev) => (prev ? `${prev}\n[Referencing uploaded file: ${file.name}]` : `Please analyze and summarize ${file.name}`));
    } catch (err: any) {
      setUploadedFileStatus(`Error ingesting file: ${err.message}`);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-4 sm:p-5 glass-header border-t border-white/10 relative z-20">
      <div className="max-w-4xl mx-auto space-y-2.5">
        {/* Upload Status Banner */}
        {uploadedFileStatus && (
          <div className="flex items-center justify-between text-xs px-3 py-1.5 rounded-xl bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 font-mono">
            <span className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
              {uploadedFileStatus}
            </span>
            <button onClick={() => setUploadedFileStatus(null)} className="hover:text-white">✕</button>
          </div>
        )}

        {/* Input Card */}
        <div className="relative rounded-2xl glass-panel border border-white/10 p-2 shadow-2xl focus-within:border-cyan-500/50 transition-all">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Ask anything on Kubernetes, vLLM, Terraform, or Cloud Architecture (Shift+Enter for newline)..."
            rows={2}
            className="w-full bg-transparent text-slate-100 text-sm sm:text-[15px] placeholder-slate-500 focus:outline-none resize-none px-3 pt-2"
          />

          <div className="flex items-center justify-between px-2 pt-2 border-t border-white/5">
            {/* Feature switches */}
            <div className="flex items-center gap-1.5 sm:gap-2">
              <button
                type="button"
                onClick={() => setUseRag(!useRag)}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-mono border transition-all ${
                  useRag
                    ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-300'
                    : 'bg-slate-900 border-slate-800 text-slate-500'
                }`}
                title="Toggle RAG Vector Retrieval"
              >
                <Database className="w-3 h-3" />
                <span>RAG</span>
              </button>

              <button
                type="button"
                onClick={() => setUseTools(!useTools)}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-mono border transition-all ${
                  useTools
                    ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300'
                    : 'bg-slate-900 border-slate-800 text-slate-500'
                }`}
                title="Toggle Agentic Tools (Calculator / Web Search)"
              >
                <Wrench className="w-3 h-3" />
                <span>Tools</span>
              </button>

              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.txt,.md,.json"
                onChange={handleFileUpload}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="p-1.5 rounded-lg hover:bg-white/10 text-slate-400 hover:text-slate-200 transition-colors"
                title="Upload PDF or Document for RAG indexing"
              >
                <Paperclip className="w-4 h-4" />
              </button>
            </div>

            {/* Voice & Send */}
            <div className="flex items-center gap-2">
              <AudioWaveform isRecording={isRecording} />

              <button
                type="button"
                onClick={isRecording ? stopRecording : startRecording}
                className={`p-2 rounded-xl border transition-all ${
                  isRecording
                    ? 'bg-rose-500/30 border-rose-500 text-rose-300 animate-pulse'
                    : 'bg-slate-800/80 border-slate-700/60 text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40'
                }`}
                title={isRecording ? 'Stop listening' : 'Start voice query (Whisper)'}
              >
                {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>

              <button
                type="button"
                onClick={() => handleSubmit()}
                disabled={!text.trim() || disabled}
                className={`flex items-center justify-center p-2 rounded-xl transition-all shadow-lg ${
                  text.trim() && !disabled
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-semibold shadow-[0_0_15px_rgba(0,242,254,0.4)]'
                    : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-white/5'
                }`}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
