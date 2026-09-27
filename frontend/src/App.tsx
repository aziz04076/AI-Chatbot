import React, { useState, useEffect, useRef } from 'react';
import { Menu, Command, Activity, Palette, Sparkles } from 'lucide-react';
import { NeuralBackground } from './components/3d/NeuralBackground';
import { ReactiveOrb } from './components/3d/ReactiveOrb';
import { ChatSidebar } from './components/sidebar/ChatSidebar';
import { MessageList } from './components/chat/MessageList';
import { MessageInput } from './components/chat/MessageInput';
import { AnalyticsDashboard } from './components/dashboard/AnalyticsDashboard';
import { CommandPalette } from './components/common/CommandPalette';
import { ThemeCustomizer } from './components/common/ThemeCustomizer';
import { GlowingCursor } from './components/common/GlowingCursor';
import { ChatMessage, AIState } from './types';
import { WS_BASE, getAuthToken, api } from './services/api';

export const App: React.FC = () => {
  const [sessionId, setSessionId] = useState<string>(() => 'session-' + Math.random().toString(36).substring(2, 9));
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [aiState, setAiState] = useState<AIState>('idle');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [themeCustomizerOpen, setThemeCustomizerOpen] = useState(false);
  const [transportMode, setTransportMode] = useState<'ws' | 'sse'>('ws');

  const socketRef = useRef<WebSocket | null>(null);
  const currentMsgRef = useRef<ChatMessage | null>(null);

  // Unified stream event processor for both WebSocket and SSE transports
  const handleIncomingStreamEvent = (data: any) => {
    if (!data || !data.type) return;

    if (data.type === 'status') {
      if (data.state === 'thinking') setAiState('thinking');
      else if (data.state === 'speaking') setAiState('speaking');
    } else if (data.type === 'plan_created') {
      setAiState('thinking');
      const newPlan = data.data?.plan;
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant') {
          return [
            ...prev.slice(0, -1),
            { ...last, plan: newPlan },
          ];
        } else {
          return [
            ...prev,
            {
              id: 'ai-temp-' + Date.now(),
              role: 'assistant',
              content: '',
              plan: newPlan,
            },
          ];
        }
      });
    } else if (data.type === 'agent_start') {
      setAiState('thinking');
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant' && last.plan) {
          const updatedTasks = last.plan.tasks.map((t) =>
            t.id === data.task_id ? { ...t, status: 'running' as const } : t
          );
          return [
            ...prev.slice(0, -1),
            { ...last, plan: { ...last.plan, tasks: updatedTasks } },
          ];
        }
        return prev;
      });
    } else if (data.type === 'agent_thought') {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant' && last.plan) {
          const updatedTasks = last.plan.tasks.map((t) =>
            t.id === data.task_id ? { ...t, thought: data.thought } : t
          );
          return [
            ...prev.slice(0, -1),
            { ...last, plan: { ...last.plan, tasks: updatedTasks } },
          ];
        }
        return prev;
      });
    } else if (data.type === 'agent_finish') {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant' && last.plan) {
          const updatedTasks = last.plan.tasks.map((t) =>
            t.id === data.task_id ? { ...t, status: 'completed' as const, output: data.output } : t
          );
          return [
            ...prev.slice(0, -1),
            { ...last, plan: { ...last.plan, tasks: updatedTasks } },
          ];
        }
        return prev;
      });
    } else if (data.type === 'tool_call') {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant') {
          const events = last.tool_events || [];
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              tool_events: [...events, { tool: data.tool, input: data.input, reason: data.reason }],
            },
          ];
        } else {
          return [
            ...prev,
            {
              id: 'ai-temp-' + Date.now(),
              role: 'assistant',
              content: '',
              tool_events: [{ tool: data.tool, input: data.input, reason: data.reason }],
            },
          ];
        }
      });
    } else if (data.type === 'tool_result') {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.tool_events) {
          const updatedEvents = last.tool_events.map((t) =>
            t.tool === data.tool ? { ...t, output: data.output } : t
          );
          return [...prev.slice(0, -1), { ...last, tool_events: updatedEvents }];
        }
        return prev;
      });
    } else if (data.type === 'token') {
      setAiState('speaking');
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last && last.role === 'assistant') {
          return [
            ...prev.slice(0, -1),
            { ...last, content: last.content + data.content },
          ];
        } else {
          return [
            ...prev,
            {
              id: 'ai-temp-' + Date.now(),
              role: 'assistant',
              content: data.content,
            },
          ];
        }
      });
    } else if (data.type === 'done') {
      setAiState('idle');
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last) {
          return [
            ...prev.slice(0, -1),
            {
              ...last,
              id: data.message_id || last.id,
              confidence_score: data.confidence_score,
              citations: data.citations,
              follow_ups: data.follow_ups,
              latency_ms: data.latency_ms,
              tokens_generated: data.tokens_generated,
              plan: data.plan || last.plan,
              trace_id: data.trace_id,
              traceparent: data.traceparent,
              trace_spans: data.trace_spans,
            },
          ];
        }
        return prev;
      });
    } else if (data.type === 'error') {
      setAiState('idle');
      setMessages((prev) => [
        ...prev,
        {
          id: 'err-' + Date.now(),
          role: 'assistant',
          content: `⚠️ ${data.content}`,
        },
      ]);
    }
  };

  // Initialize or switch WebSocket connection when sessionId changes
  useEffect(() => {
    connectWebSocket(sessionId);
    return () => {
      if (socketRef.current) socketRef.current.close();
    };
  }, [sessionId]);

  const connectWebSocket = (currentId: string) => {
    if (socketRef.current) {
      socketRef.current.close();
    }

    const wsUrl = `${WS_BASE}/${currentId}`;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      console.log('NexusAI WebSocket connected to session:', currentId);
      setTransportMode('ws');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleIncomingStreamEvent(data);
      } catch (err) {
        console.error('Error handling WebSocket message:', err);
      }
    };

    ws.onerror = (err) => {
      console.warn('WebSocket stream encounter, fallback to SSE active:', err);
      setTransportMode('sse');
    };

    ws.onclose = () => {
      setAiState('idle');
    };
  };

  const handleSendMessage = async (text: string, options: { useRag: boolean; useTools: boolean }) => {
    const userMsg: ChatMessage = {
      id: 'usr-' + Date.now(),
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setAiState('thinking');

    const payload = {
      message: text,
      token: getAuthToken() || undefined,
      use_rag: options.useRag,
      use_tools: options.useTools,
    };

    // If already in SSE mode, stream directly via SSE
    if (transportMode === 'sse') {
      try {
        await api.streamChatSSE(sessionId, payload, handleIncomingStreamEvent);
      } catch (err) {
        console.error('SSE streaming error:', err);
        setAiState('idle');
      }
      return;
    }

    // WebSocket Attempt with 3000ms watchdog timeout
    const checkWsReady = new Promise<boolean>((resolve) => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        resolve(true);
        return;
      }
      connectWebSocket(sessionId);
      const start = Date.now();
      const interval = setInterval(() => {
        if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
          clearInterval(interval);
          resolve(true);
        } else if (Date.now() - start >= 3000) {
          clearInterval(interval);
          resolve(false);
        }
      }, 100);
    });

    const isWsReady = await checkWsReady;
    if (isWsReady && socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      setTransportMode('ws');
      socketRef.current.send(JSON.stringify(payload));
    } else {
      console.warn('WebSocket connection unavailable (>3s). Seamlessly falling back to SSE streaming...');
      setTransportMode('sse');
      try {
        await api.streamChatSSE(sessionId, payload, handleIncomingStreamEvent);
      } catch (err) {
        console.error('SSE fallback streaming error:', err);
        setAiState('idle');
      }
    }
  };

  const handleSelectSession = async (id: string) => {
    setSessionId(id);
    try {
      const conv = await api.getConversation(id);
      setMessages(conv.messages || []);
    } catch {
      setMessages([]);
    }
  };

  const handleNewSession = () => {
    const newId = 'session-' + Math.random().toString(36).substring(2, 9);
    setSessionId(newId);
    setMessages([]);
  };

  return (
    <div className="relative min-h-screen flex overflow-hidden bg-[#07090e]">
      {/* Interactive Glowing Cursor with Particle Trail */}
      <GlowingCursor />

      {/* Cyberpunk Visual Depth: Animated Gradient Mesh, Cyber Grid & Scanline Overlay */}
      <div className="animated-gradient-mesh" />
      <div className="cyber-grid" />
      <div className="scanline-effect" />

      {/* 3D Particle Neural Network WebGL Shader Background */}
      <NeuralBackground aiState={aiState} />

      {/* Navigation Sidebar */}
      <ChatSidebar
        currentSessionId={sessionId}
        onSelectSession={handleSelectSession}
        onNewSession={handleNewSession}
        onOpenDashboard={() => setDashboardOpen(true)}
        onOpenSettings={() => setThemeCustomizerOpen(true)}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Chat Stage */}
      <main className="flex-1 flex flex-col h-screen relative z-10 overflow-hidden">
        {/* Top Glass Navbar */}
        <header className="h-16 px-4 sm:px-6 glass-header flex items-center justify-between z-20">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-xl bg-slate-800/80 border border-white/5 text-slate-300 hover:text-white"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_10px_#00f2fe]" />
              <h1 className="font-bold text-sm tracking-wide text-white hidden sm:inline">
                NexusAI Architecture Console
              </h1>
              {/* Transport Indicator Badge */}
              <button
                onClick={() => setTransportMode((prev) => (prev === 'ws' ? 'sse' : 'ws'))}
                className={`ml-2 px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold flex items-center gap-1.5 transition-all border ${
                  transportMode === 'ws'
                    ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30 hover:bg-cyan-500/20 shadow-[0_0_8px_rgba(0,242,254,0.15)]'
                    : 'bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20 shadow-[0_0_8px_rgba(245,158,11,0.15)]'
                }`}
                title={`Active transport: ${transportMode === 'ws' ? 'WebSocket (Primary bidirectional)' : 'Server-Sent Events (Resilient HTTP fallback)'}. Click to toggle.`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${transportMode === 'ws' ? 'bg-cyan-400 shadow-[0_0_6px_#00f2fe]' : 'bg-amber-400 shadow-[0_0_6px_#f59e0b]'}`} />
                <span>{transportMode === 'ws' ? '⚡ WS' : '🌊 SSE Fallback'}</span>
              </button>
            </div>
          </div>

          {/* 3D Reactive Orb Avatar in Header */}
          <div className="flex items-center justify-center -my-3">
            <ReactiveOrb state={aiState} />
          </div>

          {/* Quick Actions Header Controls */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setCommandPaletteOpen(true)}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/60 border border-white/10 hover:border-cyan-500/40 text-xs font-mono text-slate-400 hover:text-cyan-300 transition-all shadow-sm"
              title="Command Palette (Ctrl+K)"
            >
              <Command className="w-3.5 h-3.5 text-cyan-400" />
              <span>Ctrl+K</span>
            </button>

            <button
              onClick={() => setDashboardOpen(true)}
              className="p-2 rounded-xl bg-slate-900/60 border border-white/10 hover:border-emerald-500/40 text-slate-300 hover:text-emerald-300 transition-all"
              title="Open Admin Analytics Dashboard"
            >
              <Activity className="w-4 h-4 text-emerald-400" />
            </button>

            <button
              onClick={() => setThemeCustomizerOpen(true)}
              className="p-2 rounded-xl bg-slate-900/60 border border-white/10 hover:border-purple-500/40 text-slate-300 hover:text-purple-300 transition-all"
              title="Change Theme & Visual Style"
            >
              <Palette className="w-4 h-4 text-purple-400" />
            </button>
          </div>
        </header>

        {/* Message Conversation Stream */}
        <MessageList
          messages={messages}
          aiState={aiState}
          onFollowUpClick={(prompt) => handleSendMessage(prompt, { useRag: true, useTools: true })}
        />

        {/* Prompt Input Bar */}
        <MessageInput
          onSendMessage={handleSendMessage}
          disabled={aiState === 'thinking'}
        />
      </main>

      {/* Overlays & Modals */}
      <AnalyticsDashboard
        isOpen={dashboardOpen}
        onClose={() => setDashboardOpen(false)}
      />

      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        onNewSession={handleNewSession}
        onOpenDashboard={() => setDashboardOpen(true)}
        currentSessionId={sessionId}
      />

      <ThemeCustomizer
        isOpen={themeCustomizerOpen}
        onClose={() => setThemeCustomizerOpen(false)}
      />
    </div>
  );
};
